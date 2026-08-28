"""Admin-only management API for governed company policies."""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.admin import require_admin
from src.database import get_db
from src.models.policy import Policy, PolicyAuditEvent, PolicyException, PolicyScope, PolicyVersion
from src.models.schemas import (
    LifecycleActionResponse,
    PolicyAuditListResponse,
    PolicyCreateRequest,
    PolicyDetailResponse,
    PolicyExceptionCreateRequest,
    PolicyExceptionListResponse,
    PolicyExceptionResponse,
    PolicyListResponse,
    PolicySummaryResponse,
    PolicyUpdateRequest,
    PolicyVersionCreateRequest,
    PolicyVersionResponse,
    PolicyVersionSummaryResponse,
)
from src.models.user import User
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

router = APIRouter(prefix="/admin/policies", tags=["Admin Policies"])


def _service_error(exc: Exception) -> HTTPException:
    if isinstance(exc, (PolicyNotFoundError, PolicyTenantViolationError)):
        return HTTPException(status_code=404, detail="Policy resource not found")
    if isinstance(exc, (PolicyConflictError, InvalidPolicyTransitionError)):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, PolicyValidationError):
        return HTTPException(status_code=400, detail=str(exc))
    raise exc


async def _policy_or_404(db: AsyncSession, policy_id: str) -> Policy:
    policy = await db.get(Policy, policy_id)
    if policy is None:
        raise HTTPException(status_code=404, detail="Policy resource not found")
    return policy


async def _version_or_404(db: AsyncSession, policy: Policy, version_number: int) -> PolicyVersion:
    version = await db.scalar(select(PolicyVersion).where(
        PolicyVersion.policy_id == policy.id, PolicyVersion.version_number == version_number,
    ))
    if version is None:
        raise HTTPException(status_code=404, detail="Policy version not found")
    return version


async def _exception_or_404(db: AsyncSession, policy: Policy, exception_id: str) -> PolicyException:
    exception = await db.scalar(select(PolicyException).where(
        PolicyException.id == exception_id, PolicyException.policy_id == policy.id,
    ))
    if exception is None:
        raise HTTPException(status_code=404, detail="Policy exception not found")
    return exception


def _policy_summary(policy: Policy) -> dict[str, Any]:
    return {name: getattr(policy, name) for name in PolicySummaryResponse.model_fields}


def _version_summary(version: PolicyVersion) -> dict[str, Any]:
    return {name: getattr(version, name) for name in PolicyVersionSummaryResponse.model_fields}


def _scope(scope: PolicyScope) -> dict[str, Any]:
    return {
        name: getattr(scope, name)
        for name in ("tenant_id", "company_unit", "department", "role", "user_id", "resource_type", "resource_class", "policy_category")
    }


def _exception_response(exception: PolicyException) -> dict[str, Any]:
    data = {name: getattr(exception, name) for name in PolicyExceptionResponse.model_fields if name != "resource_selector"}
    data["resource_selector"] = json.loads(exception.resource_selector_json) if exception.resource_selector_json else None
    return data


def _audit_response(event: PolicyAuditEvent) -> dict[str, Any]:
    return {
        "id": event.id, "event_type": event.event_type, "actor_id": event.actor_id,
        "policy_version_id": event.policy_version_id, "policy_exception_id": event.policy_exception_id,
        "decision": event.decision, "reason_code": event.reason_code,
        "before_snapshot": json.loads(event.before_snapshot or "{}"),
        "after_snapshot": json.loads(event.after_snapshot or "{}"),
        "trace_id": event.trace_id, "created_at": event.created_at,
    }


@router.post("", response_model=PolicySummaryResponse, status_code=status.HTTP_201_CREATED)
async def create_policy_route(payload: PolicyCreateRequest, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    try:
        policy = await create_policy(db, actor_id=admin.id, **payload.model_dump())
    except Exception as exc:
        raise _service_error(exc) from exc
    return _policy_summary(policy)


@router.get("", response_model=PolicyListResponse)
async def list_policies(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), query: str | None = Query(None, max_length=80),
    tenant: str | None = Query(None, max_length=64), category: str | None = Query(None, max_length=64),
    status_filter: str | None = Query(None, alias="status", max_length=16), effective_state: str | None = Query(None, max_length=16),
    db: AsyncSession = Depends(get_db), _admin: User = Depends(require_admin),
):
    stmt = select(Policy)
    if query:
        pattern = f"%{query.strip()}%"
        stmt = stmt.where(or_(Policy.policy_key.ilike(pattern), Policy.name.ilike(pattern)))
    if tenant is not None:
        stmt = stmt.where(Policy.tenant_id == tenant)
    if category:
        stmt = stmt.where(Policy.category == category)
    if status_filter:
        stmt = stmt.where(Policy.status == status_filter)
    if effective_state == "active":
        stmt = stmt.where(Policy.status == "active")
    elif effective_state is not None:
        raise HTTPException(status_code=400, detail="Unsupported effective_state")
    total = int(await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    items = list((await db.execute(stmt.order_by(Policy.created_at.desc(), Policy.id.desc()).offset((page - 1) * page_size).limit(page_size))).scalars())
    return {"items": [_policy_summary(item) for item in items], "total": total, "page": page, "page_size": page_size}


@router.get("/{policy_id}", response_model=PolicyDetailResponse)
async def policy_detail(policy_id: str, db: AsyncSession = Depends(get_db), _admin: User = Depends(require_admin)):
    policy = await _policy_or_404(db, policy_id)
    version_count = int(await db.scalar(select(func.count()).select_from(PolicyVersion).where(PolicyVersion.policy_id == policy.id)) or 0)
    exception_count = int(await db.scalar(select(func.count()).select_from(PolicyException).where(PolicyException.policy_id == policy.id)) or 0)
    current = await db.get(PolicyVersion, policy.current_version_id) if policy.current_version_id else None
    return {**_policy_summary(policy), "description": policy.description, "version_count": version_count, "exception_count": exception_count, "current_version": _version_summary(current) if current else None}


@router.patch("/{policy_id}", response_model=PolicySummaryResponse)
async def update_policy_route(policy_id: str, payload: PolicyUpdateRequest, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    policy = await _policy_or_404(db, policy_id)
    changes = payload.model_dump(exclude_unset=True)
    try:
        policy = await update_policy_metadata(db, actor_id=admin.id, tenant_id=policy.tenant_id, global_admin=True, policy_id=policy.id, changes=changes)
    except Exception as exc:
        raise _service_error(exc) from exc
    await db.refresh(policy)
    return _policy_summary(policy)


@router.get("/{policy_id}/versions", response_model=list[PolicyVersionSummaryResponse])
async def list_versions(policy_id: str, db: AsyncSession = Depends(get_db), _admin: User = Depends(require_admin)):
    policy = await _policy_or_404(db, policy_id)
    versions = list((await db.execute(select(PolicyVersion).where(PolicyVersion.policy_id == policy.id).order_by(PolicyVersion.version_number.desc()))).scalars())
    return [_version_summary(item) for item in versions]


@router.post("/{policy_id}/versions", response_model=PolicyVersionSummaryResponse, status_code=status.HTTP_201_CREATED)
async def create_version_route(policy_id: str, payload: PolicyVersionCreateRequest, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    policy = await _policy_or_404(db, policy_id)
    try:
        version = await create_version(db, actor_id=admin.id, tenant_id=policy.tenant_id, global_admin=True, policy_id=policy.id, **payload.model_dump())
    except Exception as exc:
        raise _service_error(exc) from exc
    return _version_summary(version)


@router.get("/{policy_id}/versions/{version_number}", response_model=PolicyVersionResponse)
async def version_detail(policy_id: str, version_number: int, db: AsyncSession = Depends(get_db), _admin: User = Depends(require_admin)):
    policy = await _policy_or_404(db, policy_id)
    version = await _version_or_404(db, policy, version_number)
    scopes = list((await db.execute(select(PolicyScope).where(PolicyScope.policy_version_id == version.id))).scalars())
    return {**_version_summary(version), "id": version.id, "content": version.content, "rule_definition": json.loads(version.rule_definition_json), "scopes": [_scope(scope) for scope in scopes], "supersedes_version_id": version.supersedes_version_id}


@router.post("/{policy_id}/versions/{version_number}/approve", response_model=LifecycleActionResponse)
async def approve_version_route(policy_id: str, version_number: int, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    policy = await _policy_or_404(db, policy_id)
    try:
        version = await approve_version(db, actor_id=admin.id, tenant_id=policy.tenant_id, global_admin=True, policy_id=policy.id, version_number=version_number)
    except Exception as exc:
        raise _service_error(exc) from exc
    return {"id": version.id, "status": version.status}


@router.post("/{policy_id}/versions/{version_number}/activate", response_model=LifecycleActionResponse)
async def activate_version_route(policy_id: str, version_number: int, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    policy = await _policy_or_404(db, policy_id)
    try:
        version = await activate_version(db, actor_id=admin.id, tenant_id=policy.tenant_id, global_admin=True, policy_id=policy.id, version_number=version_number)
    except Exception as exc:
        raise _service_error(exc) from exc
    return {"id": version.id, "status": version.status}


@router.post("/{policy_id}/deactivate", response_model=LifecycleActionResponse)
async def deactivate_policy_route(policy_id: str, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    policy = await _policy_or_404(db, policy_id)
    try:
        changed = await deactivate_policy(db, actor_id=admin.id, tenant_id=policy.tenant_id, global_admin=True, policy_id=policy.id)
    except Exception as exc:
        raise _service_error(exc) from exc
    return {"id": changed.id, "status": changed.status}


@router.get("/{policy_id}/exceptions", response_model=PolicyExceptionListResponse)
async def list_exceptions(policy_id: str, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), status_filter: str | None = Query(None, alias="status", max_length=16), db: AsyncSession = Depends(get_db), _admin: User = Depends(require_admin)):
    policy = await _policy_or_404(db, policy_id)
    stmt = select(PolicyException).where(PolicyException.policy_id == policy.id)
    if status_filter:
        stmt = stmt.where(PolicyException.status == status_filter)
    total = int(await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    items = list((await db.execute(stmt.order_by(PolicyException.created_at.desc(), PolicyException.id.desc()).offset((page - 1) * page_size).limit(page_size))).scalars())
    return {"items": [_exception_response(item) for item in items], "total": total, "page": page, "page_size": page_size}


@router.post("/{policy_id}/exceptions", response_model=PolicyExceptionResponse, status_code=status.HTTP_201_CREATED)
async def create_exception_route(policy_id: str, payload: PolicyExceptionCreateRequest, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    policy = await _policy_or_404(db, policy_id)
    values = payload.model_dump()
    values["tenant_id"] = values["tenant_id"] or policy.tenant_id
    try:
        exception = await create_exception(db, actor_id=admin.id, global_admin=True, policy_id=policy.id, **values)
    except Exception as exc:
        raise _service_error(exc) from exc
    return _exception_response(exception)


async def _exception_action(policy_id: str, exception_id: str, operation, db: AsyncSession, admin: User) -> LifecycleActionResponse:
    policy = await _policy_or_404(db, policy_id)
    await _exception_or_404(db, policy, exception_id)
    try:
        exception = await operation(db, actor_id=admin.id, tenant_id=policy.tenant_id, global_admin=True, exception_id=exception_id)
    except Exception as exc:
        raise _service_error(exc) from exc
    return LifecycleActionResponse(id=exception.id, status=exception.status)


@router.post("/{policy_id}/exceptions/{exception_id}/approve", response_model=LifecycleActionResponse)
async def approve_exception_route(policy_id: str, exception_id: str, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    return await _exception_action(policy_id, exception_id, approve_exception, db, admin)


@router.post("/{policy_id}/exceptions/{exception_id}/reject", response_model=LifecycleActionResponse)
async def reject_exception_route(policy_id: str, exception_id: str, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    return await _exception_action(policy_id, exception_id, reject_exception, db, admin)


@router.post("/{policy_id}/exceptions/{exception_id}/revoke", response_model=LifecycleActionResponse)
async def revoke_exception_route(policy_id: str, exception_id: str, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    return await _exception_action(policy_id, exception_id, revoke_exception, db, admin)


@router.get("/{policy_id}/audit", response_model=PolicyAuditListResponse)
async def policy_audit(policy_id: str, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), db: AsyncSession = Depends(get_db), _admin: User = Depends(require_admin)):
    policy = await _policy_or_404(db, policy_id)
    stmt = select(PolicyAuditEvent).where(PolicyAuditEvent.policy_id == policy.id)
    total = int(await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    items = list((await db.execute(stmt.order_by(PolicyAuditEvent.created_at.asc(), PolicyAuditEvent.id.asc()).offset((page - 1) * page_size).limit(page_size))).scalars())
    return {"items": [_audit_response(item) for item in items], "total": total, "page": page, "page_size": page_size}
