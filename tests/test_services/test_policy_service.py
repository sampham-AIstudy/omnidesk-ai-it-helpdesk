"""Focused transactional contracts for the Phase 1C.2A.1 policy service."""
from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.database import _create_application_schema_without_feedback, migrate_policy_engine_schema
from src.models.policy import Policy, PolicyAuditEvent, PolicyException, PolicyScope, PolicyVersion, PolicyVersionStatus
from src.models.user import CompanyUnit, User, UserRole
from src.services import policy_service
from src.services.policy_dsl import policy_content_hash
from src.services.policy_enforcement_service import _load_tenant_policy_records, clear_policy_cache
from src.services.policy_resolver import ResolverContext, resolve_policy_decision
from src.services.policy_service import (
    InvalidPolicyTransitionError,
    PolicyConflictError,
    PolicyNotFoundError,
    PolicyTenantViolationError,
    PolicyValidationError,
    activate_version,
    approve_exception,
    approve_version,
    create_exception,
    create_policy,
    create_version,
    deactivate_policy,
    reject_exception,
    revoke_exception,
    update_policy_metadata,
)

NOW = datetime(2026, 8, 28, tzinfo=UTC)


@pytest.fixture
async def async_db(tmp_path):
    """A disposable schema; this test module never opens data/helpdesk.db."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'policy-service.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(_create_application_schema_without_feedback)
    await migrate_policy_engine_schema(engine)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        user = User(username="policy-admin", email="policy@example.test", full_name="Policy Admin", hashed_password="x", role=UserRole.ADMIN, company_unit=CompanyUnit.CORPORATE)
        session.add(user)
        await session.commit()
        yield session
    await engine.dispose()


def rule_definition(*, allow_exception: bool = False) -> dict:
    return {"schema_version": 1, "default_effect": "advisory", "rules": [{"rule_id": "endpoint-deny", "effect": "deny", "action": ["disable_endpoint_protection"], "resource": {"type": "managed_endpoint"}, "subjects": {"roles": ["employee"]}, "conditions": {"all": []}, "reason_code": "ENDPOINT_DENY", "user_message_template": "Restricted.", "allow_exception": allow_exception}]}


def scope(tenant_id: str = "automotive") -> dict:
    return {"tenant_id": tenant_id, "resource_type": "managed_endpoint"}


async def policy(async_db: AsyncSession, key: str = "POL-001", tenant_id: str | None = "automotive") -> Policy:
    record = await create_policy(async_db, actor_id=1, tenant_id=tenant_id, global_policy=tenant_id is None, policy_key=key, name="Endpoint policy", category="endpoint_security", description="Initial")
    await async_db.commit()
    return record


async def version(async_db: AsyncSession, record: Policy, *, content: str = "Protect managed endpoints.") -> PolicyVersion:
    created = await create_version(async_db, actor_id=1, tenant_id=record.tenant_id, global_admin=record.tenant_id is None, policy_id=record.id, title="Version", content=content, rule_definition=rule_definition(), priority=100, effective_from=NOW, effective_until=None, scopes=[scope(record.tenant_id or "automotive")])
    await async_db.commit()
    return created


async def approved_version(async_db: AsyncSession, record: Policy, *, allow_exception: bool = False) -> PolicyVersion:
    created = await create_version(async_db, actor_id=1, tenant_id=record.tenant_id, global_admin=record.tenant_id is None, policy_id=record.id, title="Version", content="Protect endpoints.", rule_definition=rule_definition(allow_exception=allow_exception), priority=100, effective_from=NOW, effective_until=None, scopes=[scope(record.tenant_id or "automotive")])
    await approve_version(async_db, actor_id=1, tenant_id=record.tenant_id, global_admin=record.tenant_id is None, policy_id=record.id, version_number=created.version_number)
    await async_db.commit()
    return created


async def count(async_db: AsyncSession, model) -> int:
    return int(await async_db.scalar(select(func.count()).select_from(model)) or 0)


@pytest.mark.asyncio
async def test_create_policy_tenant_global_duplicates_and_audit(async_db: AsyncSession):
    tenant = await policy(async_db)
    assert tenant.current_version_id is None
    assert await count(async_db, PolicyVersion) == 0
    created = list((await async_db.execute(select(PolicyAuditEvent).where(PolicyAuditEvent.policy_id == tenant.id))).scalars())
    assert [(event.event_type, event.actor_id, event.tenant_id) for event in created] == [("POLICY_CREATED", 1, "automotive")]
    global_record = await policy(async_db, "GLOBAL-001", None)
    assert global_record.tenant_id is None
    with pytest.raises(PolicyValidationError):
        await create_policy(async_db, actor_id=1, tenant_id=None, global_policy=False, policy_key="BAD", name="Bad", category="security")
    with pytest.raises(PolicyConflictError):
        await create_policy(async_db, actor_id=1, tenant_id="automotive", global_policy=False, policy_key="POL-001", name="Duplicate", category="security")
    await async_db.rollback()
    other = await policy(async_db, "POL-001", "healthcare")
    assert other.tenant_id == "healthcare"
    with pytest.raises(PolicyConflictError):
        await create_policy(async_db, actor_id=1, tenant_id=None, global_policy=True, policy_key="GLOBAL-001", name="Duplicate global", category="security")
    await async_db.rollback()


@pytest.mark.asyncio
async def test_update_metadata_contract_noop_tenant_safety_and_error_mapping(async_db: AsyncSession):
    record = await policy(async_db)
    await update_policy_metadata(async_db, actor_id=1, tenant_id="automotive", global_admin=False, policy_id=record.id, changes={"name": "Updated", "description": "New description", "category": "security"})
    await async_db.commit()
    audit = (await async_db.execute(select(PolicyAuditEvent).where(PolicyAuditEvent.event_type == "POLICY_METADATA_UPDATED"))).scalar_one()
    assert json.loads(audit.before_snapshot) == {"category": "endpoint_security", "description": "Initial", "name": "Endpoint policy"}
    assert json.loads(audit.after_snapshot) == {"category": "security", "description": "New description", "name": "Updated"}
    assert "content" not in audit.before_snapshot + audit.after_snapshot
    audits_before = await count(async_db, PolicyAuditEvent)
    await update_policy_metadata(async_db, actor_id=1, tenant_id="automotive", global_admin=False, policy_id=record.id, changes={"name": "Updated"})
    await async_db.commit()
    assert await count(async_db, PolicyAuditEvent) == audits_before  # NO_OP is silent.
    for forbidden in ("policy_key", "tenant_id", "current_version_id", "created_by", "created_at", "status"):
        with pytest.raises(PolicyValidationError):
            await update_policy_metadata(async_db, actor_id=1, tenant_id="automotive", global_admin=False, policy_id=record.id, changes={forbidden: "x"})
    healthcare = await policy(async_db, "HEALTH-001", "healthcare")
    with pytest.raises(PolicyTenantViolationError):
        await update_policy_metadata(async_db, actor_id=1, tenant_id="automotive", global_admin=False, policy_id=healthcare.id, changes={"name": "Blocked"})
    with pytest.raises(PolicyNotFoundError):
        await update_policy_metadata(async_db, actor_id=1, tenant_id="automotive", global_admin=False, policy_id="missing", changes={"name": "Missing"})
    global_record = await policy(async_db, "GLOBAL-002", None)
    with pytest.raises(PolicyTenantViolationError):
        await update_policy_metadata(async_db, actor_id=1, tenant_id="automotive", global_admin=False, policy_id=global_record.id, changes={"name": "Blocked"})
    await update_policy_metadata(async_db, actor_id=1, tenant_id="automotive", global_admin=True, policy_id=global_record.id, changes={"name": "Allowed"})
    await async_db.commit()


@pytest.mark.asyncio
async def test_create_versions_validation_and_draft_non_activation(async_db: AsyncSession):
    record = await policy(async_db)
    versions = [await version(async_db, record, content=f"Content {number}") for number in range(1, 4)]
    assert [item.version_number for item in versions] == [1, 2, 3]
    assert all(item.status == PolicyVersionStatus.DRAFT.value for item in versions)
    assert record.current_version_id is None
    assert all(item.content_hash == policy_content_hash(title=item.title, content=item.content, rule_definition=rule_definition()) for item in versions)
    scopes = list((await async_db.execute(select(PolicyScope).where(PolicyScope.policy_version_id == versions[0].id))).scalars())
    assert [item.policy_version_id for item in scopes] == [versions[0].id]
    events = list((await async_db.execute(select(PolicyAuditEvent).where(PolicyAuditEvent.event_type == "POLICY_VERSION_CREATED"))).scalars())
    assert len(events) == 3
    with pytest.raises(PolicyValidationError):
        await create_version(async_db, actor_id=1, tenant_id="automotive", global_admin=False, policy_id=record.id, title="Bad", content="Content", rule_definition={"bad": True}, priority=1, effective_from=NOW, effective_until=None, scopes=[scope()])
    with pytest.raises(PolicyValidationError):
        await create_version(async_db, actor_id=1, tenant_id="automotive", global_admin=False, policy_id=record.id, title="Bad", content="Content", rule_definition=rule_definition(), priority=1, effective_from=NOW, effective_until=NOW, scopes=[scope()])
    with pytest.raises(PolicyTenantViolationError):
        await create_version(async_db, actor_id=1, tenant_id="automotive", global_admin=False, policy_id=record.id, title="Bad", content="Content", rule_definition=rule_definition(), priority=1, effective_from=NOW, effective_until=None, scopes=[scope("healthcare")])
    with pytest.raises(PolicyValidationError):
        await create_version(async_db, actor_id=1, tenant_id="automotive", global_admin=False, policy_id=record.id, title="Bad", content="Content", rule_definition=rule_definition(), priority=1, effective_from=NOW, effective_until=None, scopes=[scope()], supersedes_version_id="missing")
    await async_db.rollback()
    assert await count(async_db, PolicyVersion) == 3
    assert await count(async_db, PolicyScope) == 3
    assert await count(async_db, PolicyAuditEvent) == 4


@pytest.mark.asyncio
async def test_version_unique_constraint_maps_conflict(async_db: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    record = await policy(async_db)
    await version(async_db, record)
    async_db.add(PolicyVersion(id="manual", policy_id=record.id, version_number=2, title="Manual", content="Manual", rule_definition_json=json.dumps(rule_definition()), effect_summary="advisory", priority=1, effective_from=NOW, status="draft", content_hash="x"))
    await async_db.commit()
    # Simulate a concurrent creator taking the number selected by this service call.
    async_db.add(PolicyVersion(id="racer", policy_id=record.id, version_number=3, title="Racer", content="Racer", rule_definition_json=json.dumps(rule_definition()), effect_summary="advisory", priority=1, effective_from=NOW, status="draft", content_hash="x"))
    await async_db.commit()

    async def stale_max(*_args, **_kwargs):
        return 2

    monkeypatch.setattr(async_db, "scalar", stale_max)
    with pytest.raises(PolicyConflictError):
        await create_version(async_db, actor_id=1, tenant_id="automotive", global_admin=False, policy_id=record.id, title="Service", content="Service", rule_definition=rule_definition(), priority=1, effective_from=NOW, effective_until=None, scopes=[scope()])
    await async_db.rollback()


@pytest.mark.asyncio
async def test_approve_validation_transitions_and_sql_immutability(async_db: AsyncSession):
    record = await policy(async_db)
    record_id = record.id
    created = await version(async_db, record)
    created_id = created.id
    approved = await approve_version(async_db, actor_id=1, tenant_id="automotive", global_admin=False, policy_id=record.id, version_number=1)
    await async_db.commit()
    assert approved.status == "approved" and approved.approved_by == 1 and approved.approved_at is not None
    assert record.current_version_id is None
    assert await count(async_db, PolicyAuditEvent) == 3
    with pytest.raises(InvalidPolicyTransitionError):
        await approve_version(async_db, actor_id=1, tenant_id="automotive", global_admin=False, policy_id=record.id, version_number=1)
    await async_db.rollback()
    for state in ("active", "superseded", "expired", "rejected"):
        await async_db.execute(text("UPDATE policy_versions SET status = :state WHERE id = :id"), {"state": state, "id": created_id})
        await async_db.commit()
        with pytest.raises(InvalidPolicyTransitionError):
            await approve_version(async_db, actor_id=1, tenant_id="automotive", global_admin=False, policy_id=record_id, version_number=1)
        await async_db.rollback()
    await async_db.execute(text("UPDATE policy_versions SET status = 'approved' WHERE id = :id"), {"id": created_id})
    await async_db.commit()
    with pytest.raises(IntegrityError):
        async with async_db.begin_nested():
            await async_db.execute(text("UPDATE policy_versions SET content = 'changed' WHERE id = :id"), {"id": created_id})


@pytest.mark.asyncio
@pytest.mark.parametrize("corruption", ["dsl", "hash", "scopes"])
async def test_approval_revalidates_draft_governance_inputs(async_db: AsyncSession, corruption: str):
    record = await policy(async_db)
    draft = await version(async_db, record)
    draft_id = draft.id
    audit_count = await count(async_db, PolicyAuditEvent)
    if corruption == "dsl":
        await async_db.execute(text("UPDATE policy_versions SET rule_definition_json = '{}' WHERE id = :id"), {"id": draft_id})
    elif corruption == "hash":
        await async_db.execute(text("UPDATE policy_versions SET content_hash = 'bad' WHERE id = :id"), {"id": draft_id})
    else:
        await async_db.execute(text("DELETE FROM policy_scopes WHERE policy_version_id = :id"), {"id": draft_id})
    await async_db.commit()
    await async_db.refresh(draft)
    with pytest.raises(PolicyValidationError):
        await approve_version(async_db, actor_id=1, tenant_id="automotive", global_admin=False, policy_id=record.id, version_number=1)
    await async_db.rollback()
    assert (await async_db.get(PolicyVersion, draft_id)).status == "draft"
    assert await count(async_db, PolicyAuditEvent) == audit_count


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["create", "metadata", "version", "approve"])
async def test_required_audit_failure_rolls_back_every_operation(async_db: AsyncSession, monkeypatch: pytest.MonkeyPatch, operation: str):
    record = await policy(async_db)
    draft = await version(async_db, record) if operation == "approve" else None
    record_id = record.id
    draft_id = draft.id if draft is not None else None
    baseline = (await count(async_db, Policy), await count(async_db, PolicyVersion), await count(async_db, PolicyScope), await count(async_db, PolicyAuditEvent))
    await async_db.commit()

    async def audit_failure(*_args, **_kwargs):
        raise RuntimeError("audit storage unavailable")

    monkeypatch.setattr(policy_service, "_write_audit", audit_failure)
    with pytest.raises(RuntimeError):
        async with async_db.begin():
            if operation == "create":
                await create_policy(async_db, actor_id=1, tenant_id="automotive", global_policy=False, policy_key="ROLLBACK", name="Rollback", category="security")
            elif operation == "metadata":
                await update_policy_metadata(async_db, actor_id=1, tenant_id="automotive", global_admin=False, policy_id=record.id, changes={"name": "Should roll back"})
            elif operation == "version":
                await create_version(async_db, actor_id=1, tenant_id="automotive", global_admin=False, policy_id=record.id, title="Rollback", content="Rollback content", rule_definition=rule_definition(), priority=1, effective_from=NOW, effective_until=None, scopes=[scope()])
            else:
                assert draft is not None
                await approve_version(async_db, actor_id=1, tenant_id="automotive", global_admin=False, policy_id=record.id, version_number=draft.version_number)
    assert (await count(async_db, Policy), await count(async_db, PolicyVersion), await count(async_db, PolicyScope), await count(async_db, PolicyAuditEvent)) == baseline
    if operation == "metadata":
        assert (await async_db.get(Policy, record_id)).name == "Endpoint policy"
    if operation == "approve":
        assert draft_id is not None
        assert (await async_db.get(PolicyVersion, draft_id)).status == "draft"


@pytest.mark.asyncio
async def test_activation_supersession_windows_and_deactivation(async_db: AsyncSession):
    record = await policy(async_db)
    record_id = record.id
    first = await approved_version(async_db, record)
    await activate_version(async_db, actor_id=1, tenant_id="automotive", global_admin=False, policy_id=record_id, version_number=1)
    await async_db.commit()
    second = await approved_version(async_db, record)
    second_id = second.id
    activated = await activate_version(async_db, actor_id=1, tenant_id="automotive", global_admin=False, policy_id=record_id, version_number=2)
    await async_db.commit()
    assert activated.status == "active" and activated.activated_by == 1
    assert (await async_db.get(PolicyVersion, first.id)).status == "superseded"
    assert (await async_db.get(Policy, record_id)).current_version_id == second_id
    assert await count(async_db, PolicyVersion) == 2
    active_count = await async_db.scalar(select(func.count()).select_from(PolicyVersion).where(PolicyVersion.status == "active"))
    assert active_count == 1
    events = list((await async_db.execute(select(PolicyAuditEvent.event_type))).scalars())
    assert events.count("POLICY_SUPERSEDED") == 1 and events.count("POLICY_ACTIVATED") == 2
    for status in ("active", "superseded", "draft", "expired", "rejected"):
        await async_db.execute(text("UPDATE policy_versions SET status = :status WHERE id = :id"), {"status": status, "id": second_id})
        await async_db.commit()
        with pytest.raises(InvalidPolicyTransitionError):
            await activate_version(async_db, actor_id=1, tenant_id="automotive", global_admin=False, policy_id=record_id, version_number=2)
        await async_db.rollback()
    await async_db.execute(text("UPDATE policy_versions SET status = 'approved', effective_from = :future WHERE id = :id"), {"future": NOW.replace(year=2030), "id": second_id})
    await async_db.commit()
    with pytest.raises(PolicyValidationError, match="Future-effective"):
        await activate_version(async_db, actor_id=1, tenant_id="automotive", global_admin=False, policy_id=record_id, version_number=2)
    await async_db.rollback()
    await async_db.execute(text("UPDATE policies SET status = 'active' WHERE id = :id"), {"id": record_id})
    await async_db.commit()
    deactivated = await deactivate_policy(async_db, actor_id=1, tenant_id="automotive", global_admin=False, policy_id=record_id)
    await async_db.commit()
    assert deactivated.status == "inactive" and deactivated.deactivated_by == 1 and deactivated.current_version_id == second_id
    with pytest.raises(InvalidPolicyTransitionError):
        await deactivate_policy(async_db, actor_id=1, tenant_id="automotive", global_admin=False, policy_id=record_id)


@pytest.mark.asyncio
async def test_exception_lifecycle_permissions_tenant_and_transitions(async_db: AsyncSession):
    record = await policy(async_db)
    active = await approved_version(async_db, record, allow_exception=True)
    await activate_version(async_db, actor_id=1, tenant_id="automotive", global_admin=False, policy_id=record.id, version_number=active.version_number)
    await async_db.commit()
    created = await create_exception(async_db, actor_id=1, tenant_id="automotive", global_admin=False, policy_id=record.id, policy_version_id=active.id, subject_type="user", subject_id="1", reason="Temporary maintenance", action_type="disable_endpoint_protection", resource_type="managed_endpoint", valid_from=NOW, valid_until=NOW.replace(year=2027))
    await async_db.commit()
    assert created.status == "pending" and created.created_by == 1
    approved = await approve_exception(async_db, actor_id=1, tenant_id="automotive", global_admin=False, exception_id=created.id)
    await async_db.commit()
    assert approved.status == "approved" and approved.approved_by == 1
    with pytest.raises(InvalidPolicyTransitionError):
        await approve_exception(async_db, actor_id=1, tenant_id="automotive", global_admin=False, exception_id=created.id)
    await async_db.rollback()
    revoked = await revoke_exception(async_db, actor_id=1, tenant_id="automotive", global_admin=False, exception_id=created.id)
    await async_db.commit()
    assert revoked.status == "revoked" and revoked.revoked_by == 1
    with pytest.raises(InvalidPolicyTransitionError):
        await revoke_exception(async_db, actor_id=1, tenant_id="automotive", global_admin=False, exception_id=created.id)
    await async_db.rollback()
    rejected = await create_exception(async_db, actor_id=1, tenant_id="automotive", global_admin=False, policy_id=record.id, subject_type="role", subject_id="employee", reason="Not needed", valid_from=NOW, valid_until=NOW.replace(year=2027))
    await reject_exception(async_db, actor_id=1, tenant_id="automotive", global_admin=False, exception_id=rejected.id)
    await async_db.commit()
    assert rejected.status == "rejected"
    for operation in (approve_exception, revoke_exception, reject_exception):
        with pytest.raises(InvalidPolicyTransitionError):
            await operation(async_db, actor_id=1, tenant_id="automotive", global_admin=False, exception_id=rejected.id)
        await async_db.rollback()
    other = await policy(async_db, "HEALTH-LIFECYCLE", "healthcare")
    with pytest.raises(PolicyTenantViolationError):
        await activate_version(async_db, actor_id=1, tenant_id="automotive", global_admin=False, policy_id=other.id, version_number=1)
    with pytest.raises(PolicyTenantViolationError):
        await create_exception(async_db, actor_id=1, tenant_id="automotive", global_admin=False, policy_id=other.id, subject_type="user", subject_id="1", reason="Blocked", valid_from=NOW, valid_until=NOW.replace(year=2027))
    with pytest.raises(PolicyValidationError):
        await create_exception(async_db, actor_id=1, tenant_id="automotive", global_admin=False, policy_id=record.id, subject_type="chat", subject_id="x", reason="No", valid_from=NOW, valid_until=NOW.replace(year=2027))


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["activation", "deactivation", "exception_create", "exception_approve", "exception_reject", "exception_revoke"])
async def test_lifecycle_audit_failure_rolls_back(async_db: AsyncSession, monkeypatch: pytest.MonkeyPatch, operation: str):
    record = await policy(async_db)
    active = await approved_version(async_db, record, allow_exception=True)
    if operation in {"deactivation", "exception_create", "exception_approve", "exception_reject", "exception_revoke"}:
        await activate_version(async_db, actor_id=1, tenant_id="automotive", global_admin=False, policy_id=record.id, version_number=active.version_number)
        await async_db.commit()
    pending = None
    if operation in {"exception_approve", "exception_reject", "exception_revoke"}:
        pending = await create_exception(async_db, actor_id=1, tenant_id="automotive", global_admin=False, policy_id=record.id, policy_version_id=active.id, subject_type="user", subject_id="1", reason="Temporary", action_type="disable_endpoint_protection", valid_from=NOW, valid_until=NOW.replace(year=2027))
        await async_db.commit()
    if operation == "exception_revoke":
        assert pending is not None
        await approve_exception(async_db, actor_id=1, tenant_id="automotive", global_admin=False, exception_id=pending.id)
        await async_db.commit()
    policy_id, version_id = record.id, active.id
    exception_id = pending.id if pending else None
    baseline = (await count(async_db, PolicyException), await count(async_db, PolicyAuditEvent))
    await async_db.commit()

    async def audit_failure(*_args, **_kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(policy_service, "_write_audit", audit_failure)
    with pytest.raises(RuntimeError):
        async with async_db.begin():
            if operation == "activation":
                await activate_version(async_db, actor_id=1, tenant_id="automotive", global_admin=False, policy_id=policy_id, version_number=1)
            elif operation == "deactivation":
                await deactivate_policy(async_db, actor_id=1, tenant_id="automotive", global_admin=False, policy_id=policy_id)
            elif operation == "exception_create":
                await create_exception(async_db, actor_id=1, tenant_id="automotive", global_admin=False, policy_id=policy_id, subject_type="user", subject_id="1", reason="Temporary", valid_from=NOW, valid_until=NOW.replace(year=2027))
            elif operation == "exception_approve":
                assert exception_id is not None
                await approve_exception(async_db, actor_id=1, tenant_id="automotive", global_admin=False, exception_id=exception_id)
            elif operation == "exception_reject":
                assert exception_id is not None
                await reject_exception(async_db, actor_id=1, tenant_id="automotive", global_admin=False, exception_id=exception_id)
            else:
                assert exception_id is not None
                await revoke_exception(async_db, actor_id=1, tenant_id="automotive", global_admin=False, exception_id=exception_id)
    assert (await count(async_db, PolicyException), await count(async_db, PolicyAuditEvent)) == baseline
    if operation == "activation":
        assert (await async_db.get(PolicyVersion, version_id)).status == "approved"
    if operation == "deactivation":
        assert (await async_db.get(Policy, policy_id)).status == "active"
    if operation in {"exception_approve", "exception_reject"}:
        assert exception_id is not None and (await async_db.get(PolicyException, exception_id)).status == "pending"
    if operation == "exception_revoke":
        assert exception_id is not None and (await async_db.get(PolicyException, exception_id)).status == "approved"


async def enforcement_revision(async_db: AsyncSession) -> str:
    clear_policy_cache("automotive")
    records = await _load_tenant_policy_records(async_db, "automotive")
    return resolve_policy_decision(
        ResolverContext(tenant_id="automotive", role="employee", user_id=1, action_type="disable_endpoint_protection", resource={"type": "managed_endpoint"}),
        *records,
    ).resolver_revision


@pytest.mark.asyncio
async def test_active_enforcement_revision_matrix(async_db: AsyncSession):
    record = await policy(async_db)
    empty = await enforcement_revision(async_db)
    draft = await create_version(async_db, actor_id=1, tenant_id="automotive", global_admin=False, policy_id=record.id, title="Revision", content="Revision content", rule_definition=rule_definition(allow_exception=True), priority=100, effective_from=NOW, effective_until=None, scopes=[scope()])
    await async_db.commit()
    assert await enforcement_revision(async_db) == empty
    await approve_version(async_db, actor_id=1, tenant_id="automotive", global_admin=False, policy_id=record.id, version_number=draft.version_number)
    await async_db.commit()
    assert await enforcement_revision(async_db) == empty
    await activate_version(async_db, actor_id=1, tenant_id="automotive", global_admin=False, policy_id=record.id, version_number=draft.version_number)
    await async_db.commit()
    active_revision = await enforcement_revision(async_db)
    assert active_revision != empty
    pending = await create_exception(async_db, actor_id=1, tenant_id="automotive", global_admin=False, policy_id=record.id, policy_version_id=draft.id, subject_type="user", subject_id="1", reason="Pending", action_type="disable_endpoint_protection", valid_from=NOW, valid_until=NOW.replace(year=2027))
    await async_db.commit()
    assert await enforcement_revision(async_db) == active_revision
    await approve_exception(async_db, actor_id=1, tenant_id="automotive", global_admin=False, exception_id=pending.id)
    await async_db.commit()
    approved_revision = await enforcement_revision(async_db)
    assert approved_revision != active_revision
    await revoke_exception(async_db, actor_id=1, tenant_id="automotive", global_admin=False, exception_id=pending.id)
    await async_db.commit()
    assert await enforcement_revision(async_db) != approved_revision
    await deactivate_policy(async_db, actor_id=1, tenant_id="automotive", global_admin=False, policy_id=record.id)
    await async_db.commit()
    assert await enforcement_revision(async_db) != active_revision


@pytest.mark.asyncio
async def test_supersession_audit_failure_preserves_old_active(async_db: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    record = await policy(async_db)
    first = await approved_version(async_db, record)
    await activate_version(async_db, actor_id=1, tenant_id="automotive", global_admin=False, policy_id=record.id, version_number=1)
    await async_db.commit()
    second = await approved_version(async_db, record)
    record_id, first_id, second_id = record.id, first.id, second.id
    baseline_audits = await count(async_db, PolicyAuditEvent)
    await async_db.commit()

    async def audit_failure(*_args, **_kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(policy_service, "_write_audit", audit_failure)
    with pytest.raises(RuntimeError):
        async with async_db.begin():
            await activate_version(async_db, actor_id=1, tenant_id="automotive", global_admin=False, policy_id=record_id, version_number=2)
    assert (await async_db.get(PolicyVersion, first_id)).status == "active"
    assert (await async_db.get(PolicyVersion, second_id)).status == "approved"
    assert (await async_db.get(Policy, record_id)).current_version_id == first_id
    assert await count(async_db, PolicyAuditEvent) == baseline_audits
