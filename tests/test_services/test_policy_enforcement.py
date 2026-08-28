"""Unit and integration tests for PolicyEnforcementService and runtime pipeline."""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.agents.nodes.hitl_node import hitl_check_node
from src.agents.state import TicketAgentState
from src.database import _create_application_schema_without_feedback, migrate_policy_engine_schema
from src.models.policy import (
    Policy,
    PolicyAuditEvent,
    PolicyException,
    PolicyExceptionStatus,
    PolicyScope,
    PolicyStatus,
    PolicyVersion,
    PolicyVersionStatus,
    ResolvedDecision,
)
from src.models.user import CompanyUnit, User, UserRole
from src.services import policy_enforcement_service
from src.services.policy_dsl import policy_content_hash
from src.services.policy_enforcement_service import (
    clear_policy_cache,
    enforce_policy,
)
from src.services.service_request_service import create_service_request


@pytest.fixture
async def async_db(tmp_path):
    """Isolated SQLite database with core application and policy engine tables."""
    db_file = tmp_path / "test_enforcement.db"
    test_engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}")
    async with test_engine.begin() as conn:
        await conn.run_sync(_create_application_schema_without_feedback)
    await migrate_policy_engine_schema(test_engine)

    session_maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    clear_policy_cache()
    async with session_maker() as session:
        yield session
    clear_policy_cache()
    await test_engine.dispose()


def _make_rule_dict(
    rule_id: str,
    effect: str,
    action: str,
    *,
    field_name: str | None = None,
    op: str = "eq",
    val: str | None = None,
    reason_code: str = "POLICY_RULE",
    allow_exception: bool = False,
) -> dict:
    conditions = []
    if field_name and val is not None:
        conditions.append({"field": field_name, "operator": op, "value": val})
    return {
        "schema_version": 1,
        "default_effect": "advisory",
        "rules": [
            {
                "rule_id": rule_id,
                "effect": effect,
                "action": [action],
                "resource": {"type": "managed_endpoint"},
                "subjects": {"roles": []},
                "conditions": {"all": conditions},
                "reason_code": reason_code,
                "user_message_template": "Denied by company policy.",
                "allow_exception": allow_exception,
            }
        ],
    }


@pytest.mark.asyncio
async def test_enforce_policy_no_decisive_policy(async_db: AsyncSession):
    """When no tenant or global policy exists, enforce_policy returns NO_DECISIVE_POLICY (allowed)."""
    res = await enforce_policy(
        async_db,
        tenant_id="hospitality",
        action_type="ticket:evaluate",
        actor_id=1,
    )
    assert res.decision == ResolvedDecision.NO_DECISIVE_POLICY
    assert res.allowed is True
    assert res.requires_approval is False
    assert res.escalate is False


@pytest.mark.asyncio
async def test_enforce_policy_missing_tenant_fail_closed(async_db: AsyncSession):
    """Missing tenant_id must fail closed with ESCALATE/non-allowed outcome."""
    res = await enforce_policy(
        async_db,
        tenant_id="",
        action_type="ticket:evaluate",
    )
    assert res.decision == ResolvedDecision.ESCALATE
    assert res.allowed is False
    assert res.escalate is True
    assert "MISSING_TENANT_ID" in res.reason_codes


@pytest.mark.asyncio
async def test_enforce_policy_tenant_deny_rule_and_audit(async_db: AsyncSession):
    """A tenant-specific DENY policy is resolved and audited."""
    now = datetime.now(UTC)
    rule_dict = _make_rule_dict(
        "DENY_HOSP_PASSWORD_RESET",
        "deny",
        "password_reset",
        field_name="action.type",
        op="eq",
        val="password_reset",
        reason_code="TENANT_POLICY_DENY_PWD",
    )

    policy_obj = Policy(
        tenant_id="hospitality",
        policy_key="SEC-HOSP-001",
        name="Hospitality Password Policy",
        category="security",
        status=PolicyStatus.ACTIVE.value,
    )
    async_db.add(policy_obj)
    await async_db.flush()

    content = "Password reset policy text"
    version = PolicyVersion(
        policy_id=policy_obj.id,
        version_number=1,
        title="v1",
        content=content,
        effect_summary="Deny password reset for hospitality",
        rule_definition_json=json.dumps(rule_dict),
        content_hash=policy_content_hash(title="v1", content=content, rule_definition=rule_dict),
        priority=100,
        status=PolicyVersionStatus.ACTIVE.value,
        effective_from=now - timedelta(days=1),
    )
    async_db.add(version)
    await async_db.flush()
    policy_obj.current_version_id = version.id
    async_db.add(PolicyScope(policy_version_id=version.id, tenant_id="hospitality"))
    await async_db.flush()

    clear_policy_cache("hospitality")
    res = await enforce_policy(
        async_db,
        tenant_id="hospitality",
        resource={"type": "managed_endpoint"},
        action_type="password_reset",
        actor_id=42,
        ticket_id=999,
    )
    assert res.decision == ResolvedDecision.DENY
    assert res.allowed is False
    assert "TENANT_POLICY_DENY_PWD" in res.reason_codes

    # Verify audit log entry was created
    audit = (
        await async_db.execute(
            PolicyAuditEvent.__table__.select().where(
                PolicyAuditEvent.ticket_id == 999
            )
        )
    ).first()
    assert audit is not None
    assert audit.decision == "deny"
    assert audit.tenant_id == "hospitality"


@pytest.mark.asyncio
async def test_enforce_policy_tenant_isolation(async_db: AsyncSession):
    """Tenant A's policy must not affect Tenant B."""
    now = datetime.now(UTC)
    rule_dict = _make_rule_dict(
        "DENY_CORP_VPN",
        "deny",
        "vpn_request",
        field_name="action.type",
        op="eq",
        val="vpn_request",
        reason_code="CORP_NO_VPN",
    )

    policy_obj = Policy(
        tenant_id="corporate",
        policy_key="SEC-CORP-VPN",
        name="Corporate VPN Policy",
        category="access_control",
        status=PolicyStatus.ACTIVE.value,
    )
    async_db.add(policy_obj)
    await async_db.flush()

    content = "VPN policy text"
    version = PolicyVersion(
        policy_id=policy_obj.id,
        version_number=1,
        title="v1",
        content=content,
        effect_summary="Deny VPN for corporate",
        rule_definition_json=json.dumps(rule_dict),
        content_hash=policy_content_hash(title="v1", content=content, rule_definition=rule_dict),
        priority=100,
        status=PolicyVersionStatus.ACTIVE.value,
        effective_from=now - timedelta(days=1),
    )
    async_db.add(version)
    await async_db.flush()
    async_db.add(PolicyScope(policy_version_id=version.id, tenant_id="corporate"))

    clear_policy_cache()

    corp_res = await enforce_policy(
        async_db,
        tenant_id="corporate",
        resource={"type": "managed_endpoint"},
        action_type="vpn_request",
    )
    assert corp_res.decision == ResolvedDecision.DENY

    hosp_res = await enforce_policy(
        async_db,
        tenant_id="hospitality",
        resource={"type": "managed_endpoint"},
        action_type="vpn_request",
    )
    assert hosp_res.decision == ResolvedDecision.NO_DECISIVE_POLICY
    assert hosp_res.allowed is True


@pytest.mark.asyncio
async def test_enforce_policy_approved_exception_override(async_db: AsyncSession):
    """An approved valid exception overrides a DENY policy."""
    now = datetime.now(UTC)
    rule_dict = _make_rule_dict(
        "DENY_SOFTWARE_INSTALL",
        "deny",
        "software_install",
        field_name="action.type",
        op="eq",
        val="software_install",
        reason_code="NO_SOFTWARE_INSTALL",
        allow_exception=True,
    )

    policy_obj = Policy(
        tenant_id="education",
        policy_key="SEC-EDU-SOFT",
        name="Education Software Policy",
        category="software",
        status=PolicyStatus.ACTIVE.value,
    )
    async_db.add(policy_obj)
    await async_db.flush()

    content = "Software install policy text"
    version = PolicyVersion(
        policy_id=policy_obj.id,
        version_number=1,
        title="v1",
        content=content,
        effect_summary="Deny software install for education",
        rule_definition_json=json.dumps(rule_dict),
        content_hash=policy_content_hash(title="v1", content=content, rule_definition=rule_dict),
        priority=100,
        status=PolicyVersionStatus.ACTIVE.value,
        effective_from=now - timedelta(days=1),
    )
    async_db.add(version)
    await async_db.flush()
    async_db.add(PolicyScope(policy_version_id=version.id, tenant_id="education"))

    exception = PolicyException(
        policy_id=policy_obj.id,
        tenant_id="education",
        subject_type="department",
        subject_id="IT Lab",
        reason="Academic research exception",
        status=PolicyExceptionStatus.APPROVED.value,
        valid_from=now - timedelta(days=1),
        valid_until=now + timedelta(days=30),
    )
    async_db.add(exception)
    await async_db.flush()

    clear_policy_cache("education")

    # Regular department -> DENY
    res_regular = await enforce_policy(
        async_db,
        tenant_id="education",
        department="Finance",
        action_type="software_install",
        resource={"type": "managed_endpoint"},
    )
    assert res_regular.decision == ResolvedDecision.DENY

    # Exception department -> ALLOW
    res_except = await enforce_policy(
        async_db,
        tenant_id="education",
        department="IT Lab",
        action_type="software_install",
        resource={"type": "managed_endpoint"},
    )
    assert res_except.decision == ResolvedDecision.ALLOW
    assert len(res_except.matching_exceptions) > 0


@pytest.mark.asyncio
@pytest.mark.skip(reason="Phase 1C.1 deliberately has no service-request runtime integration")
async def test_service_request_policy_denial(async_db: AsyncSession):
    """create_service_request enforces tenant policy and raises ValueError if DENY."""
    now = datetime.now(UTC)
    user = User(
        email="emp@corporate.com",
        username="emp_corp",
        full_name="Employee Corporate",
        hashed_password="pw",
        role=UserRole.EMPLOYEE,
        company_unit=CompanyUnit.CORPORATE,
    )
    async_db.add(user)
    await async_db.flush()

    rule_dict = _make_rule_dict(
        "DENY_CORP_SOFTWARE",
        "deny",
        "service_request:create",
        field_name="resource.service_name",
        op="eq",
        val="Cài đặt phần mềm",
        reason_code="SOFTWARE_BLOCKED",
    )

    policy_obj = Policy(
        tenant_id="corporate",
        policy_key="SR-CORP-SOFT",
        name="No Software Installation",
        category="software",
        status=PolicyStatus.ACTIVE.value,
    )
    async_db.add(policy_obj)
    await async_db.flush()

    content = "Software catalog restriction"
    version = PolicyVersion(
        policy_id=policy_obj.id,
        version_number=1,
        title="v1",
        content=content,
        effect_summary="Deny software install for corporate",
        rule_definition_json=json.dumps(rule_dict),
        content_hash=policy_content_hash(title="v1", content=content, rule_definition=rule_dict),
        priority=100,
        status=PolicyVersionStatus.ACTIVE.value,
        effective_from=now - timedelta(days=1),
    )
    async_db.add(version)
    await async_db.flush()

    clear_policy_cache("corporate")

    with pytest.raises(ValueError, match="bị từ chối bởi chính sách doanh nghiệp"):
        await create_service_request(
            async_db,
            service_name="Cài đặt phần mềm",
            category="Software",
            form_data={"software_name": "Docker"},
            submitter_id=user.id,
        )


@pytest.mark.asyncio
@pytest.mark.skip(reason="Phase 1C.1 deliberately has no HITL runtime integration")
async def test_hitl_check_node_policy_integration():
    """hitl_check_node respects dynamic policy decisions (DENY, REQUIRE_APPROVAL, ESCALATE)."""
    state: TicketAgentState = {
        "ticket_id": 101,
        "ticket_number": "INC-20260827-0101",
        "title": "Hỏng màn hình máy siêu âm",
        "description": "Cần thay thế màn hình",
        "category": "hardware",
        "priority": "high",
        "urgency": "high",
        "confidence_score": 0.95,
        "rag_context": "Hướng dẫn bảo trì",
        "company_unit": "healthcare",
        "submitter_id": 12,
        "hitl_required": False,
        "is_blocked": False,
        "needs_clarification": False,
        "error": None,
    }

    result_state = await hitl_check_node(state)
    assert "hitl_required" in result_state
    assert "action_taken" in result_state


async def _seed_cache_deny(session: AsyncSession, tenant: str = "cache-tenant") -> None:
    now = datetime.now(UTC)
    rule_dict = _make_rule_dict("CACHE_DENY", "deny", "cache_action", reason_code="CACHE_DENY")
    policy = Policy(tenant_id=tenant, policy_key="CACHE-1", name="Cache", category="security", status="active")
    session.add(policy)
    await session.flush()
    version = PolicyVersion(
        policy_id=policy.id, version_number=1, title="v1", content="content", effect_summary="deny",
        rule_definition_json=json.dumps(rule_dict), content_hash=policy_content_hash(title="v1", content="content", rule_definition=rule_dict),
        priority=1, status="active", effective_from=now - timedelta(minutes=1),
    )
    session.add(version)
    await session.flush()
    policy.current_version_id = version.id
    session.add(PolicyScope(policy_version_id=version.id, tenant_id=tenant))
    await session.flush()


@pytest.mark.asyncio
async def test_policy_cache_disabled_miss_hit_and_backend_failure(async_db: AsyncSession, monkeypatch):
    """Policy cache is optional and can never bypass DB policy enforcement."""
    await _seed_cache_deny(async_db)
    clear_policy_cache()
    original_execute = async_db.execute
    calls = 0

    async def counted_execute(*args, **kwargs):
        nonlocal calls
        calls += 1
        return await original_execute(*args, **kwargs)

    monkeypatch.setattr(async_db, "execute", counted_execute)
    monkeypatch.setattr(policy_enforcement_service, "_POLICY_CACHE_TTL_SECONDS", 0)
    disabled = await enforce_policy(async_db, tenant_id="cache-tenant", action_type="cache_action", resource={"type": "managed_endpoint"})
    assert disabled.decision is ResolvedDecision.DENY and calls > 0

    monkeypatch.setattr(policy_enforcement_service, "_POLICY_CACHE_TTL_SECONDS", 60)
    clear_policy_cache()
    before_miss = calls
    miss = await enforce_policy(async_db, tenant_id="cache-tenant", action_type="cache_action", resource={"type": "managed_endpoint"})
    after_miss = calls
    hit = await enforce_policy(async_db, tenant_id="cache-tenant", action_type="cache_action", resource={"type": "managed_endpoint"})
    assert miss.decision is hit.decision is ResolvedDecision.DENY
    assert after_miss > before_miss and calls == after_miss

    class BrokenCache:
        def get(self, _key):
            raise RuntimeError("cache unavailable")

        def __setitem__(self, _key, _value):
            raise RuntimeError("cache unavailable")

        def clear(self):
            pass

    monkeypatch.setattr(policy_enforcement_service, "_policy_cache", BrokenCache())
    failed_cache = await enforce_policy(async_db, tenant_id="cache-tenant", action_type="cache_action", resource={"type": "managed_endpoint"})
    assert failed_cache.decision is ResolvedDecision.DENY
    assert failed_cache.allowed is False


@pytest.mark.asyncio
async def test_security_relevant_db_failure_fails_closed(async_db: AsyncSession, monkeypatch):
    async def unavailable(*_args, **_kwargs):
        raise RuntimeError("database unavailable")

    clear_policy_cache()
    monkeypatch.setattr(async_db, "execute", unavailable)
    result = await enforce_policy(async_db, tenant_id="automotive", action_type="security_action")
    assert result.decision is ResolvedDecision.ESCALATE
    assert result.allowed is False
    assert "RESOLVER_ERROR" in result.reason_codes
