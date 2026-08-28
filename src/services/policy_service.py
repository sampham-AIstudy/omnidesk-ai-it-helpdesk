"""Transactional management foundation for the Company Policy Engine."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.policy import (
    Policy,
    PolicyAuditEvent,
    PolicyEffect,
    PolicyException,
    PolicyExceptionStatus,
    PolicyScope,
    PolicyStatus,
    PolicyVersion,
    PolicyVersionStatus,
)
from src.services.policy_dsl import PolicyRuleDefinition, normalize_policy_text, policy_content_hash


class PolicyServiceError(Exception):
    """Base error exposed by policy management operations."""


class PolicyNotFoundError(PolicyServiceError):
    pass


class PolicyConflictError(PolicyServiceError):
    pass


class PolicyValidationError(PolicyServiceError):
    pass


class InvalidPolicyTransitionError(PolicyConflictError):
    pass


class PolicyTenantViolationError(PolicyServiceError):
    pass


def _tenant(policy: Policy) -> str:
    return policy.tenant_id or "global"


def _safe_snapshot(values: dict[str, Any]) -> str:
    return json.dumps(values, ensure_ascii=False, sort_keys=True, default=str)


async def _write_audit(
    db: AsyncSession, *, actor_id: int, policy: Policy, event_type: str,
    version: PolicyVersion | None = None, exception: PolicyException | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None, trace_id: str | None = None,
) -> None:
    db.add(PolicyAuditEvent(
        tenant_id=_tenant(policy), actor_id=actor_id, principal_id=actor_id,
        policy_id=policy.id, policy_version_id=version.id if version else None,
        policy_exception_id=exception.id if exception else None,
        event_type=event_type, before_snapshot=_safe_snapshot(before or {}),
        after_snapshot=_safe_snapshot(after or {}), metadata_json="{}", trace_id=trace_id,
    ))
    await db.flush()


def _assert_access(policy: Policy, tenant_id: str | None, *, global_admin: bool) -> None:
    if policy.tenant_id is None:
        if not global_admin:
            raise PolicyTenantViolationError("Global policy requires global administrator authority")
    elif tenant_id != policy.tenant_id:
        raise PolicyTenantViolationError("Policy tenant is outside caller scope")


async def _get_policy(db: AsyncSession, policy_id: str) -> Policy:
    policy = await db.get(Policy, policy_id)
    if policy is None:
        raise PolicyNotFoundError("Policy not found")
    return policy


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


async def _validate_version_for_governance(
    db: AsyncSession, *, policy: Policy, version: PolicyVersion,
) -> list[PolicyScope]:
    """Revalidate immutable inputs before a version changes governance state."""
    try:
        definition = json.loads(version.rule_definition_json)
        PolicyRuleDefinition.model_validate(definition)
    except Exception as exc:
        raise PolicyValidationError("Invalid policy rule definition") from exc
    if policy_content_hash(title=version.title, content=version.content, rule_definition=definition) != version.content_hash:
        raise PolicyValidationError("Policy version content hash mismatch")
    if version.effective_until is not None and version.effective_until <= version.effective_from:
        raise PolicyValidationError("Invalid effective window")
    scopes = list((await db.execute(select(PolicyScope).where(PolicyScope.policy_version_id == version.id))).scalars())
    if not scopes or any(policy.tenant_id is not None and scope.tenant_id not in (None, policy.tenant_id) for scope in scopes):
        raise PolicyValidationError("Invalid policy scopes")
    return scopes


def _invalidate_policy_cache(policy: Policy) -> None:
    """Discard cached enforcement records only after a lifecycle mutation/audit succeeds."""
    from src.services.policy_enforcement_service import clear_policy_cache

    clear_policy_cache(policy.tenant_id)


async def create_policy(
    db: AsyncSession, *, actor_id: int, tenant_id: str | None, global_policy: bool,
    policy_key: str, name: str, category: str, description: str | None = None,
    trace_id: str | None = None,
) -> Policy:
    if global_policy != (tenant_id is None):
        raise PolicyValidationError("Global ownership must be explicitly declared")
    key = policy_key.strip().upper() if isinstance(policy_key, str) else ""
    clean_category = category.strip() if isinstance(category, str) else ""
    if not key or len(key) > 80 or not clean_category or len(clean_category) > 64:
        raise PolicyValidationError("Invalid policy metadata")
    try:
        clean_name = normalize_policy_text(name, maximum=255)
        clean_description = normalize_policy_text(description, maximum=50_000) if description else None
    except ValueError as exc:
        raise PolicyValidationError("Invalid policy metadata") from exc
    policy = Policy(
        tenant_id=tenant_id, policy_key=key,
        name=clean_name, category=clean_category, description=clean_description,
        status=PolicyStatus.DRAFT.value, created_by=actor_id,
    )
    db.add(policy)
    try:
        await db.flush()
    except IntegrityError as exc:
        raise PolicyConflictError("Policy key already exists for this tenant") from exc
    await _write_audit(db, actor_id=actor_id, policy=policy, event_type="POLICY_CREATED", after={"policy_key": key, "tenant": _tenant(policy)}, trace_id=trace_id)
    return policy


async def update_policy_metadata(
    db: AsyncSession, *, actor_id: int, tenant_id: str | None, global_admin: bool,
    policy_id: str, changes: dict[str, Any], trace_id: str | None = None,
) -> Policy:
    policy = await _get_policy(db, policy_id)
    _assert_access(policy, tenant_id, global_admin=global_admin)
    allowed = {"name", "description", "category"}
    if not changes or set(changes) - allowed:
        raise PolicyValidationError("Only name, description and category are mutable")
    before = {field: getattr(policy, field) for field in changes}
    normalized = dict(changes)
    try:
        if "name" in normalized:
            normalized["name"] = normalize_policy_text(normalized["name"], maximum=255)
        if "description" in normalized and normalized["description"] is not None:
            normalized["description"] = normalize_policy_text(normalized["description"], maximum=50_000)
    except ValueError as exc:
        raise PolicyValidationError("Invalid policy metadata") from exc
    if "category" in normalized:
        normalized["category"] = str(normalized["category"]).strip()
        if not normalized["category"] or len(normalized["category"]) > 64:
            raise PolicyValidationError("Invalid category")
    if before == normalized:
        return policy
    for field, value in normalized.items():
        setattr(policy, field, value)
    await db.flush()
    await _write_audit(db, actor_id=actor_id, policy=policy, event_type="POLICY_METADATA_UPDATED", before=before, after=normalized, trace_id=trace_id)
    return policy


async def create_version(
    db: AsyncSession, *, actor_id: int, tenant_id: str | None, global_admin: bool,
    policy_id: str, title: str, content: str, rule_definition: dict[str, Any], priority: int,
    effective_from: datetime, effective_until: datetime | None, scopes: list[dict[str, Any]],
    supersedes_version_id: str | None = None, trace_id: str | None = None,
) -> PolicyVersion:
    policy = await _get_policy(db, policy_id)
    _assert_access(policy, tenant_id, global_admin=global_admin)
    if effective_until is not None and effective_until <= effective_from:
        raise PolicyValidationError("Invalid effective window")
    if not scopes:
        raise PolicyValidationError("At least one scope is required")
    try:
        PolicyRuleDefinition.model_validate(rule_definition)
    except Exception as exc:
        raise PolicyValidationError("Invalid policy rule definition") from exc
    if supersedes_version_id:
        prior = await db.get(PolicyVersion, supersedes_version_id)
        if prior is None or prior.policy_id != policy.id:
            raise PolicyValidationError("Invalid superseded version")
    try:
        clean_title = normalize_policy_text(title, maximum=255)
        clean_content = normalize_policy_text(content, maximum=50_000)
    except ValueError as exc:
        raise PolicyValidationError("Invalid policy version content") from exc
    number = int(await db.scalar(select(func.max(PolicyVersion.version_number)).where(PolicyVersion.policy_id == policy.id)) or 0) + 1
    version = PolicyVersion(policy_id=policy.id, version_number=number, title=clean_title, content=clean_content, rule_definition_json=json.dumps(rule_definition, ensure_ascii=False, sort_keys=True), effect_summary=str(rule_definition.get("default_effect", "advisory")), priority=priority, effective_from=effective_from, effective_until=effective_until, status=PolicyVersionStatus.DRAFT.value, created_by=actor_id, supersedes_version_id=supersedes_version_id, content_hash=policy_content_hash(title=clean_title, content=clean_content, rule_definition=rule_definition))
    db.add(version)
    try:
        await db.flush()
        for scope_values in scopes:
            scope_tenant = scope_values.get("tenant_id")
            if policy.tenant_id is not None and scope_tenant not in (None, policy.tenant_id):
                raise PolicyTenantViolationError("Scope tenant must match policy tenant")
            db.add(PolicyScope(policy_version_id=version.id, **scope_values))
        await db.flush()
    except IntegrityError as exc:
        raise PolicyConflictError("Duplicate policy version") from exc
    await _write_audit(db, actor_id=actor_id, policy=policy, version=version, event_type="POLICY_VERSION_CREATED", after={"version_number": number, "priority": priority}, trace_id=trace_id)
    return version


async def approve_version(
    db: AsyncSession, *, actor_id: int, tenant_id: str | None, global_admin: bool,
    policy_id: str, version_number: int, trace_id: str | None = None,
) -> PolicyVersion:
    policy = await _get_policy(db, policy_id)
    _assert_access(policy, tenant_id, global_admin=global_admin)
    version = await db.scalar(select(PolicyVersion).where(PolicyVersion.policy_id == policy.id, PolicyVersion.version_number == version_number))
    if version is None:
        raise PolicyNotFoundError("Policy version not found")
    if version.status != PolicyVersionStatus.DRAFT.value:
        raise InvalidPolicyTransitionError("Only DRAFT versions can be approved")
    await _validate_version_for_governance(db, policy=policy, version=version)
    version.status = PolicyVersionStatus.APPROVED.value
    version.approved_by = actor_id
    version.approved_at = datetime.now()
    await db.flush()
    await _write_audit(db, actor_id=actor_id, policy=policy, version=version, event_type="POLICY_VERSION_APPROVED", after={"version_number": version_number}, trace_id=trace_id)
    return version


async def activate_version(
    db: AsyncSession, *, actor_id: int, tenant_id: str | None, global_admin: bool,
    policy_id: str, version_number: int, trace_id: str | None = None,
) -> PolicyVersion:
    """Immediately activate an APPROVED version; scheduled activation is not supported in v1."""
    policy = await _get_policy(db, policy_id)
    _assert_access(policy, tenant_id, global_admin=global_admin)
    version = await db.scalar(select(PolicyVersion).where(
        PolicyVersion.policy_id == policy.id, PolicyVersion.version_number == version_number,
    ))
    if version is None:
        raise PolicyNotFoundError("Policy version not found")
    if version.status != PolicyVersionStatus.APPROVED.value:
        raise InvalidPolicyTransitionError("Only APPROVED versions can be activated")
    await _validate_version_for_governance(db, policy=policy, version=version)
    now = datetime.now(UTC)
    if _as_utc(version.effective_from) > now:
        raise PolicyValidationError("Future-effective versions require scheduled activation")
    if version.effective_until is not None and _as_utc(version.effective_until) <= now:
        raise PolicyValidationError("Expired versions cannot be activated")
    active = await db.scalar(select(PolicyVersion).where(
        PolicyVersion.policy_id == policy.id, PolicyVersion.status == PolicyVersionStatus.ACTIVE.value,
    ))
    if active is not None:
        active.status = PolicyVersionStatus.SUPERSEDED.value
        await db.flush()
        await _write_audit(
            db, actor_id=actor_id, policy=policy, version=active, event_type="POLICY_SUPERSEDED",
            before={"status": PolicyVersionStatus.ACTIVE.value},
            after={"status": PolicyVersionStatus.SUPERSEDED.value, "superseded_by": version_number}, trace_id=trace_id,
        )
    version.status = PolicyVersionStatus.ACTIVE.value
    version.activated_by = actor_id
    version.activated_at = now
    policy.current_version_id = version.id
    policy.status = PolicyStatus.ACTIVE.value
    await db.flush()
    await _write_audit(
        db, actor_id=actor_id, policy=policy, version=version, event_type="POLICY_ACTIVATED",
        after={"version_number": version_number, "status": PolicyVersionStatus.ACTIVE.value}, trace_id=trace_id,
    )
    _invalidate_policy_cache(policy)
    return version


async def deactivate_policy(
    db: AsyncSession, *, actor_id: int, tenant_id: str | None, global_admin: bool,
    policy_id: str, trace_id: str | None = None,
) -> Policy:
    """Gate enforcement at the policy header while retaining immutable active-version history."""
    policy = await _get_policy(db, policy_id)
    _assert_access(policy, tenant_id, global_admin=global_admin)
    if policy.status != PolicyStatus.ACTIVE.value:
        raise InvalidPolicyTransitionError("Only ACTIVE policies can be deactivated")
    policy.status = PolicyStatus.INACTIVE.value
    policy.deactivated_by = actor_id
    policy.deactivated_at = datetime.now(UTC)
    await db.flush()
    await _write_audit(
        db, actor_id=actor_id, policy=policy, event_type="POLICY_DEACTIVATED",
        before={"status": PolicyStatus.ACTIVE.value, "current_version_id": policy.current_version_id},
        after={"status": PolicyStatus.INACTIVE.value, "current_version_id": policy.current_version_id}, trace_id=trace_id,
    )
    _invalidate_policy_cache(policy)
    return policy


async def _get_exception(db: AsyncSession, exception_id: str) -> PolicyException:
    exception = await db.get(PolicyException, exception_id)
    if exception is None:
        raise PolicyNotFoundError("Policy exception not found")
    return exception


async def _exception_policy(
    db: AsyncSession, *, exception: PolicyException, tenant_id: str | None, global_admin: bool,
) -> Policy:
    policy = await _get_policy(db, exception.policy_id)
    _assert_access(policy, tenant_id, global_admin=global_admin)
    if exception.tenant_id != (policy.tenant_id or tenant_id):
        raise PolicyTenantViolationError("Exception tenant is outside policy scope")
    return policy


async def create_exception(
    db: AsyncSession, *, actor_id: int, tenant_id: str | None, global_admin: bool,
    policy_id: str, subject_type: str, subject_id: str, reason: str, valid_from: datetime,
    valid_until: datetime, override_effect: str = PolicyEffect.ALLOW.value,
    action_type: str | None = None, resource_type: str | None = None,
    resource_selector: dict[str, Any] | None = None, policy_version_id: str | None = None,
    trace_id: str | None = None,
) -> PolicyException:
    policy = await _get_policy(db, policy_id)
    _assert_access(policy, tenant_id, global_admin=global_admin)
    if not tenant_id:
        raise PolicyValidationError("Exceptions require an explicit tenant")
    if policy.tenant_id is not None and tenant_id != policy.tenant_id:
        raise PolicyTenantViolationError("Exception tenant must match policy tenant")
    if subject_type not in {"user", "department", "role"} or not isinstance(subject_id, str) or not subject_id.strip():
        raise PolicyValidationError("Invalid exception subject")
    if valid_until <= valid_from:
        raise PolicyValidationError("Invalid exception window")
    if override_effect != PolicyEffect.ALLOW.value:
        raise PolicyValidationError("Only allow exceptions are supported")
    try:
        clean_reason = normalize_policy_text(reason, maximum=50_000)
        selector_json = json.dumps(resource_selector, ensure_ascii=False, sort_keys=True) if resource_selector else None
    except (TypeError, ValueError) as exc:
        raise PolicyValidationError("Invalid exception details") from exc
    if policy_version_id:
        version = await db.get(PolicyVersion, policy_version_id)
        if version is None or version.policy_id != policy.id:
            raise PolicyValidationError("Invalid exception policy version")
    exception = PolicyException(
        policy_id=policy.id, policy_version_id=policy_version_id, tenant_id=tenant_id,
        subject_type=subject_type, subject_id=subject_id.strip(), action_type=action_type,
        resource_type=resource_type, resource_selector_json=selector_json, override_effect=override_effect,
        reason=clean_reason, status=PolicyExceptionStatus.PENDING.value, valid_from=valid_from,
        valid_until=valid_until, created_by=actor_id,
    )
    db.add(exception)
    await db.flush()
    await _write_audit(
        db, actor_id=actor_id, policy=policy, exception=exception, event_type="POLICY_EXCEPTION_CREATED",
        after={"subject_type": subject_type, "subject_id": subject_id.strip(), "status": "pending"}, trace_id=trace_id,
    )
    return exception


async def _validate_exception_permission(db: AsyncSession, *, policy: Policy, exception: PolicyException) -> None:
    version_id = exception.policy_version_id or policy.current_version_id
    if not version_id:
        raise PolicyValidationError("Exception requires an active policy version")
    version = await db.get(PolicyVersion, version_id)
    if version is None or version.policy_id != policy.id:
        raise PolicyValidationError("Invalid exception policy version")
    try:
        definition = PolicyRuleDefinition.model_validate(json.loads(version.rule_definition_json))
    except Exception as exc:
        raise PolicyValidationError("Invalid policy rule definition") from exc
    permitted = any(
        rule.allow_exception
        and (exception.action_type is None or exception.action_type in rule.action)
        and (exception.resource_type is None or rule.resource.type in (None, exception.resource_type))
        for rule in definition.rules
    )
    if not permitted:
        raise PolicyValidationError("Policy rules do not permit this exception")


async def approve_exception(
    db: AsyncSession, *, actor_id: int, tenant_id: str | None, global_admin: bool,
    exception_id: str, trace_id: str | None = None,
) -> PolicyException:
    exception = await _get_exception(db, exception_id)
    policy = await _exception_policy(db, exception=exception, tenant_id=tenant_id, global_admin=global_admin)
    if exception.status != PolicyExceptionStatus.PENDING.value:
        raise InvalidPolicyTransitionError("Only PENDING exceptions can be approved")
    now = datetime.now(UTC)
    if _as_utc(exception.valid_until) <= now or exception.valid_until <= exception.valid_from:
        raise PolicyValidationError("Exception is expired or has an invalid window")
    await _validate_exception_permission(db, policy=policy, exception=exception)
    exception.status = PolicyExceptionStatus.APPROVED.value
    exception.approved_by = actor_id
    exception.approved_at = now
    await db.flush()
    await _write_audit(db, actor_id=actor_id, policy=policy, exception=exception, event_type="POLICY_EXCEPTION_APPROVED", after={"status": "approved"}, trace_id=trace_id)
    _invalidate_policy_cache(policy)
    return exception


async def reject_exception(
    db: AsyncSession, *, actor_id: int, tenant_id: str | None, global_admin: bool,
    exception_id: str, trace_id: str | None = None,
) -> PolicyException:
    exception = await _get_exception(db, exception_id)
    policy = await _exception_policy(db, exception=exception, tenant_id=tenant_id, global_admin=global_admin)
    if exception.status != PolicyExceptionStatus.PENDING.value:
        raise InvalidPolicyTransitionError("Only PENDING exceptions can be rejected")
    exception.status = PolicyExceptionStatus.REJECTED.value
    await db.flush()
    await _write_audit(db, actor_id=actor_id, policy=policy, exception=exception, event_type="POLICY_EXCEPTION_REJECTED", after={"status": "rejected"}, trace_id=trace_id)
    return exception


async def revoke_exception(
    db: AsyncSession, *, actor_id: int, tenant_id: str | None, global_admin: bool,
    exception_id: str, trace_id: str | None = None,
) -> PolicyException:
    exception = await _get_exception(db, exception_id)
    policy = await _exception_policy(db, exception=exception, tenant_id=tenant_id, global_admin=global_admin)
    if exception.status != PolicyExceptionStatus.APPROVED.value:
        raise InvalidPolicyTransitionError("Only APPROVED exceptions can be revoked")
    exception.status = PolicyExceptionStatus.REVOKED.value
    exception.revoked_by = actor_id
    exception.revoked_at = datetime.now(UTC)
    await db.flush()
    await _write_audit(db, actor_id=actor_id, policy=policy, exception=exception, event_type="POLICY_EXCEPTION_REVOKED", after={"status": "revoked"}, trace_id=trace_id)
    _invalidate_policy_cache(policy)
    return exception
