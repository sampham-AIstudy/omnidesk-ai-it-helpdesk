"""Admin API — User management, KB management."""
from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth import get_current_active_user
from src.database import get_db
from src.models.audit_log import AuditAction, AuditLog
from src.models.knowledge_base import KnowledgeBaseEntry
from src.models.preference_candidate import PreferenceCandidate
from src.models.schemas import (
    AdminUserUpdate,
    FulfillmentGroupListResponse,
    KBEntryCreate,
    KBEntryResponse,
    KBEntryUpdate,
    PreferenceCandidateReviewRequest,
    TechnicianFulfillmentGroupsResponse,
    TechnicianFulfillmentGroupsUpdate,
    UserCreate,
    UserResponse,
)
from src.models.technician_fulfillment_group import TechnicianFulfillmentGroup
from src.models.ticket import Ticket
from src.models.user import User, UserRole
from src.services import auth_service
from src.services.rag_service import delete_document, get_collection_count, index_document
from src.services.service_request_service import canonical_fulfillment_groups
from src.services.ticket_service import write_audit_log

router = APIRouter(prefix="/admin", tags=["Admin"])


def require_admin(current_user: User = Depends(get_current_active_user)) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Chỉ Admin mới thực hiện được")
    return current_user


def require_manager_or_admin(current_user: User = Depends(get_current_active_user)) -> User:
    if not auth_service.has_min_role(current_user, UserRole.MANAGER):
        raise HTTPException(status_code=403, detail="Cần quyền Manager trở lên")
    return current_user


def _kb_visibility_clause(user: User):
    """Match vector-retrieval ACL rules before returning a raw KB article."""
    # System admins manage lifecycle and incident response across tenants, but
    # this exception is deliberately limited to the explicit admin role.
    if user.role == UserRole.ADMIN:
        return KnowledgeBaseEntry.id.is_not(None)
    company_unit = user.company_unit.value
    company_allowed = or_(
        KnowledgeBaseEntry.applicable_to_all.is_(True),
        KnowledgeBaseEntry.company_unit.is_(None),
        KnowledgeBaseEntry.company_unit.in_(("all", company_unit)),
    )
    department = user.department or ""
    department_allowed = or_(
        KnowledgeBaseEntry.department.is_(None),
        KnowledgeBaseEntry.department == "",
        KnowledgeBaseEntry.department == department,
    )
    return and_(company_allowed, department_allowed)


def _preference_candidate_payload(candidate: PreferenceCandidate) -> dict:
    """Only return the pre-sanitized dataset representation to reviewers."""
    evidence = json.loads(candidate.label_evidence_json)
    return {
        "candidate_id": candidate.candidate_id,
        "tenant_id": candidate.tenant_id,
        "group_key": candidate.group_key,
        "prompt": candidate.prompt,
        "chosen": candidate.chosen,
        "rejected": candidate.rejected,
        "source_event_ids": json.loads(candidate.source_event_ids_json),
        "quality_score": candidate.quality_score,
        "quality_tier": candidate.quality_tier,
        "review_status": candidate.review_status,
        "reviewed_by_id": candidate.reviewed_by_id,
        "reviewed_at": candidate.reviewed_at,
        "review_note": candidate.review_note,
        "excluded_from_training": candidate.excluded_from_training,
        "training_exclusion_reason": candidate.training_exclusion_reason,
        "training_excluded_by": candidate.training_excluded_by,
        "training_excluded_at": candidate.training_excluded_at,
        "created_at": candidate.created_at,
        "evidence": evidence,
    }


@router.get("/preference-candidates")
async def list_preference_candidates(
    tenant: str | None = Query(default=None),
    status: str | None = Query(default=None, pattern="^(PENDING_REVIEW|APPROVED|REJECTED)$"),
    quality_tier: str | None = Query(default=None, pattern="^(HIGH|MEDIUM|LOW)$"),
    rating: int | None = Query(default=None, ge=1, le=5),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    source_type: str | None = Query(default=None, max_length=80),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    requested_tenant = tenant or str(getattr(current_user.company_unit, "value", current_user.company_unit))
    if tenant is None and auth_service.scoped_company_unit(current_user) is None:
        requested_tenant = None
    if requested_tenant is not None and not auth_service.can_access_company_unit(current_user, requested_tenant):
        raise HTTPException(status_code=403, detail="Tenant review scope is forbidden")
    stmt = select(PreferenceCandidate).order_by(PreferenceCandidate.created_at.desc(), PreferenceCandidate.candidate_id.desc())
    if requested_tenant is not None:
        stmt = stmt.where(PreferenceCandidate.tenant_id == requested_tenant)
    if status:
        stmt = stmt.where(PreferenceCandidate.review_status == status)
    if quality_tier:
        stmt = stmt.where(PreferenceCandidate.quality_tier == quality_tier)
    if date_from:
        stmt = stmt.where(PreferenceCandidate.created_at >= date_from)
    if date_to:
        stmt = stmt.where(PreferenceCandidate.created_at <= date_to)
    candidates = list((await db.execute(stmt)).scalars())
    payload = [_preference_candidate_payload(item) for item in candidates]
    if rating is not None:
        payload = [item for item in payload if rating in item["evidence"].get("ratings", [])]
    if source_type:
        payload = [item for item in payload if source_type in item["evidence"].get("source_types", [])]
    return {"items": payload, "total": len(payload)}


@router.post("/preference-candidates/{candidate_id}/review")
async def review_preference_candidate_api(
    candidate_id: str,
    payload: PreferenceCandidateReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    candidate = await db.get(PreferenceCandidate, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Preference candidate not found")
    if not auth_service.can_access_company_unit(current_user, candidate.tenant_id):
        raise HTTPException(status_code=403, detail="Tenant review scope is forbidden")
    from src.services.feedback_dataset_service import review_preference_candidate

    try:
        candidate = await review_preference_candidate(
            db, candidate_id=candidate_id, reviewer=current_user, status=payload.status, note=payload.note,
        )
    except (LookupError, PermissionError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.add(AuditLog(
        actor_id=current_user.id,
        actor_type="user",
        action=AuditAction.STATUS_CHANGED,
        description=f"Preference candidate {candidate_id} reviewed as {payload.status}",
        metadata_json=json.dumps({"candidate_id": candidate_id, "tenant_id": candidate.tenant_id, "quality_tier": candidate.quality_tier}),
    ))
    await db.commit()
    await db.refresh(candidate)
    return _preference_candidate_payload(candidate)


# ─── User Management ──────────────────────────────────────────────────────────

@router.get("/users", response_model=list[UserResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    query = select(User).order_by(User.created_at.desc())
    company_scope = auth_service.scoped_company_unit(current_user)
    if company_scope:
        query = query.where(User.company_unit == company_scope)
    result = await db.execute(query)
    users = result.scalars().all()
    return [UserResponse.model_validate(u) for u in users]


@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    existing = await auth_service.get_user_by_username(db, payload.username)
    if existing:
        raise HTTPException(status_code=409, detail="Username đã tồn tại")
    email_in_use = await auth_service.get_user_by_email(db, payload.email.lower())
    if email_in_use:
        raise HTTPException(status_code=409, detail="Email is already in use")
    user_data = payload.model_dump()
    user_data["email"] = payload.email.lower()
    user = await auth_service.create_user(db, **user_data)
    await write_audit_log(
        db=db, actor_id=_admin.id, actor_type="user", action=AuditAction.USER_CREATED,
        description=f"User #{user.id} created",
        metadata={"target_user_id": user.id, "role": user.role.value, "company_unit": user.company_unit.value},
    )
    await db.refresh(user)
    return UserResponse.model_validate(user)


async def _assert_admin_lifecycle_safe(
    db: AsyncSession, *, actor: User, target: User, changes: dict[str, object]
) -> None:
    next_active = bool(changes.get("is_active", target.is_active))
    next_role = changes.get("role", target.role)
    if target.id == actor.id and (not next_active or next_role != UserRole.ADMIN):
        raise HTTPException(status_code=400, detail="An administrator cannot deactivate or demote their own account.")

    removes_active_admin = (
        target.role == UserRole.ADMIN
        and target.is_active
        and (not next_active or next_role != UserRole.ADMIN)
    )
    if removes_active_admin:
        active_admins = await db.scalar(
            select(func.count(User.id)).where(User.role == UserRole.ADMIN, User.is_active.is_(True))
        )
        if int(active_admins or 0) <= 1:
            raise HTTPException(status_code=409, detail="The final active administrator cannot be deactivated or demoted.")


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    payload: AdminUserUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Typed admin update plus soft deactivate/reactivate; never mass assigns."""
    target = await db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="At least one editable field is required.")
    if any(changes.get(field) is None for field in ("full_name", "email", "role", "company_unit") if field in changes):
        raise HTTPException(status_code=422, detail="Name, email, role and company unit cannot be null.")
    await _assert_admin_lifecycle_safe(db, actor=admin, target=target, changes=changes)

    if "email" in changes:
        normalized_email = str(changes["email"]).lower()
        existing = await auth_service.get_user_by_email(db, normalized_email)
        if existing and existing.id != target.id:
            raise HTTPException(status_code=409, detail="Email is already in use")
        changes["email"] = normalized_email
    if "full_name" in changes:
        changes["full_name"] = str(changes["full_name"]).strip()
    if "phone" in changes:
        changes["phone"] = str(changes["phone"]).strip() or None
    if "department" in changes:
        changes["department"] = str(changes["department"]).strip() or None

    previous_active = target.is_active
    was_technician = target.role == UserRole.TECHNICIAN
    for field, value in changes.items():
        setattr(target, field, value)
    await db.flush()
    removed_groups: list[str] = []
    if was_technician and target.role != UserRole.TECHNICIAN:
        result = await db.execute(
            select(TechnicianFulfillmentGroup.fulfillment_group)
            .where(TechnicianFulfillmentGroup.technician_id == target.id)
            .order_by(TechnicianFulfillmentGroup.fulfillment_group)
        )
        removed_groups = list(result.scalars())
        if removed_groups:
            await db.execute(
                delete(TechnicianFulfillmentGroup).where(TechnicianFulfillmentGroup.technician_id == target.id)
            )
            await write_audit_log(
                db=db, actor_id=admin.id, actor_type="user",
                action=AuditAction.TECHNICIAN_FULFILLMENT_GROUPS_UPDATED,
                description=f"Technician #{target.id} fulfillment groups cleared after role change",
                metadata={
                    "target_user_id": target.id,
                    "previous_groups": removed_groups,
                    "new_groups": [],
                    "reason": "role_changed_from_technician",
                },
            )
    if "is_active" in changes and target.is_active != previous_active:
        action = AuditAction.USER_REACTIVATED if target.is_active else AuditAction.USER_DEACTIVATED
        description = f"User #{target.id} {'reactivated' if target.is_active else 'deactivated'}"
    else:
        action = AuditAction.USER_UPDATED
        description = f"User #{target.id} updated"
    await write_audit_log(
        db=db, actor_id=admin.id, actor_type="user", action=action, description=description,
        metadata={
            "target_user_id": target.id,
            "fields": sorted(changes.keys()),
            "role": target.role.value,
            "company_unit": target.company_unit.value,
            "is_active": target.is_active,
            "removed_fulfillment_groups": removed_groups,
        },
    )
    await db.refresh(target)
    return UserResponse.model_validate(target)


# ─── Knowledge Base Management ────────────────────────────────────────────────

async def _technician_group_response(
    db: AsyncSession, technician_id: int
) -> TechnicianFulfillmentGroupsResponse:
    result = await db.execute(
        select(TechnicianFulfillmentGroup.fulfillment_group)
        .where(TechnicianFulfillmentGroup.technician_id == technician_id)
        .order_by(TechnicianFulfillmentGroup.fulfillment_group)
    )
    return TechnicianFulfillmentGroupsResponse(
        technician_id=technician_id,
        fulfillment_groups=list(result.scalars()),
    )


async def _require_technician_target(db: AsyncSession, technician_id: int) -> User:
    target = await db.get(User, technician_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.role != UserRole.TECHNICIAN:
        raise HTTPException(status_code=422, detail="Fulfillment groups can only be assigned to a technician.")
    return target


@router.get("/fulfillment-groups", response_model=FulfillmentGroupListResponse)
async def list_fulfillment_groups(_admin: User = Depends(require_admin)):
    """Expose fixed, catalog-derived values without building group CRUD."""
    return FulfillmentGroupListResponse(items=canonical_fulfillment_groups())


@router.get("/technicians/{technician_id}/fulfillment-groups", response_model=TechnicianFulfillmentGroupsResponse)
async def get_technician_fulfillment_groups(
    technician_id: int,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    await _require_technician_target(db, technician_id)
    return await _technician_group_response(db, technician_id)


@router.put("/technicians/{technician_id}/fulfillment-groups", response_model=TechnicianFulfillmentGroupsResponse)
async def replace_technician_fulfillment_groups(
    technician_id: int,
    payload: TechnicianFulfillmentGroupsUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Atomically replace explicit membership; an empty set grants no queue access."""
    target = await _require_technician_target(db, technician_id)
    requested = [group.strip() for group in payload.fulfillment_groups]
    if len(set(requested)) != len(requested):
        raise HTTPException(status_code=422, detail="Fulfillment groups must not contain duplicates.")
    allowed = set(canonical_fulfillment_groups())
    invalid = sorted(set(requested) - allowed)
    if invalid:
        raise HTTPException(status_code=422, detail=f"Unknown fulfillment group: {', '.join(invalid)}")

    previous = (await _technician_group_response(db, technician_id)).fulfillment_groups
    await db.execute(delete(TechnicianFulfillmentGroup).where(TechnicianFulfillmentGroup.technician_id == technician_id))
    db.add_all([
        TechnicianFulfillmentGroup(technician_id=technician_id, fulfillment_group=group)
        for group in sorted(requested)
    ])
    await db.flush()
    response = await _technician_group_response(db, technician_id)
    await write_audit_log(
        db=db, actor_id=admin.id, actor_type="user",
        action=AuditAction.TECHNICIAN_FULFILLMENT_GROUPS_UPDATED,
        description=f"Technician #{target.id} fulfillment groups updated",
        metadata={
            "target_user_id": target.id,
            "target_company_unit": target.company_unit.value,
            "previous_groups": previous,
            "new_groups": response.fulfillment_groups,
        },
    )
    return response


@router.get("/kb", response_model=list[KBEntryResponse])
async def list_kb(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    result = await db.execute(
        select(KnowledgeBaseEntry)
        .where(KnowledgeBaseEntry.is_active)
        .where(_kb_visibility_clause(_user))
        .order_by(KnowledgeBaseEntry.id)
    )
    entries = result.scalars().all()
    return [KBEntryResponse.model_validate(e) for e in entries]


@router.post("/kb/{entry_id}/vote", response_model=KBEntryResponse)
async def vote_kb_entry(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    """Bấm Hữu Ích cho bài viết Knowledge Base."""
    result = await db.execute(
        select(KnowledgeBaseEntry)
        .where(KnowledgeBaseEntry.id == entry_id)
        .where(KnowledgeBaseEntry.is_active)
        .where(_kb_visibility_clause(_user))
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="KB entry không tồn tại")

    entry.helpful_votes = (entry.helpful_votes or 0) + 1
    entry.usage_count = (entry.usage_count or 0) + 1
    await db.commit()
    await db.refresh(entry)
    return KBEntryResponse.model_validate(entry)


@router.post("/kb/{entry_id}/unvote", response_model=KBEntryResponse)
async def unvote_kb_entry(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    """Gỡ bình chọn Hữu Ích cho bài viết Knowledge Base."""
    result = await db.execute(
        select(KnowledgeBaseEntry)
        .where(KnowledgeBaseEntry.id == entry_id)
        .where(KnowledgeBaseEntry.is_active)
        .where(_kb_visibility_clause(_user))
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="KB entry không tồn tại")

    entry.helpful_votes = max(0, (entry.helpful_votes or 0) - 1)
    await db.commit()
    await db.refresh(entry)
    return KBEntryResponse.model_validate(entry)


@router.post("/kb", response_model=KBEntryResponse, status_code=201)
async def create_kb_entry(
    payload: KBEntryCreate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    entry = KnowledgeBaseEntry(**payload.model_dump())
    db.add(entry)
    await db.flush()

    # Index vào ChromaDB
    chroma_id = f"kb-admin-{entry.id}"
    content_for_index = f"{entry.title}. {entry.content}"
    index_document(
        doc_id=chroma_id,
        content=content_for_index,
        metadata={
            "title": entry.title,
            "category": entry.category,
            "tags": entry.tags or "",
            "solution": entry.solution or "",
            "runbook": entry.runbook or "",
            "company_unit": entry.company_unit or "all",
            "department": entry.department or "",
            "applicable_to_all": entry.applicable_to_all,
        },
    )
    entry.chroma_id = chroma_id
    await db.flush()
    await write_audit_log(
        db=db,
        actor_id=_admin.id,
        actor_type="user",
        action=AuditAction.KB_CREATED,
        description=f"KB entry #{entry.id} created: {entry.title}",
        metadata={"kb_id": entry.id, "category": entry.category},
    )
    await db.refresh(entry)
    return KBEntryResponse.model_validate(entry)


@router.patch("/kb/{entry_id}", response_model=KBEntryResponse)
async def update_kb_entry(
    entry_id: int,
    payload: KBEntryUpdate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    entry = await db.get(KnowledgeBaseEntry, entry_id)
    if not entry or not entry.is_active:
        raise HTTPException(status_code=404, detail="KB entry khong ton tai")

    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(entry, key, value)

    if not entry.chroma_id:
        entry.chroma_id = f"kb-admin-{entry.id}"

    content_for_index = f"{entry.title}. {entry.content}"
    index_document(
        doc_id=entry.chroma_id,
        content=content_for_index,
        metadata={
            "title": entry.title,
            "category": entry.category,
            "tags": entry.tags or "",
            "solution": entry.solution or "",
            "runbook": entry.runbook or "",
            "company_unit": entry.company_unit or "all",
            "department": entry.department or "",
            "applicable_to_all": entry.applicable_to_all,
        },
    )

    await db.flush()
    await write_audit_log(
        db=db,
        actor_id=_admin.id,
        actor_type="user",
        action=AuditAction.KB_UPDATED,
        description=f"KB entry #{entry.id} updated: {entry.title}",
        metadata={"kb_id": entry.id, "fields": sorted(updates.keys())},
    )
    await db.refresh(entry)
    return KBEntryResponse.model_validate(entry)


@router.delete("/kb/{entry_id}", status_code=204)
async def delete_kb_entry(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    entry = await db.get(KnowledgeBaseEntry, entry_id)
    if not entry or not entry.is_active:
        raise HTTPException(status_code=404, detail="KB entry khong ton tai")

    entry.is_active = False
    if entry.chroma_id:
        delete_document(entry.chroma_id)

    await db.flush()
    await write_audit_log(
        db=db,
        actor_id=_admin.id,
        actor_type="user",
        action=AuditAction.KB_DELETED,
        description=f"KB entry #{entry.id} deleted: {entry.title}",
        metadata={"kb_id": entry.id},
    )


@router.get("/kb/stats")
async def kb_stats(_user: User = Depends(require_manager_or_admin)):
    return {
        "chroma_documents": get_collection_count(),
        "status": "healthy",
    }


@router.get("/ai-metrics")
async def get_ai_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    """AI Observability & Performance Analytics Endpoint."""
    from sqlalchemy import func

    from src.models.ai_run import AIRun

    company_scope = auth_service.scoped_company_unit(current_user)

    def scoped_runs(query):
        if company_scope is None:
            return query
        return query.join(Ticket, AIRun.ticket_id == Ticket.id).join(
            User, Ticket.submitter_id == User.id
        ).where(User.company_unit == company_scope)

    total_runs_res = await db.execute(scoped_runs(select(func.count(AIRun.id))))
    total_runs = total_runs_res.scalar() or 0

    if total_runs == 0:
        return {
            "total_ai_runs": 0,
            "avg_latency_ms": 0,
            "avg_groundedness": 0.0,
            "avg_confidence": 0.0,
            "hitl_trigger_rate": 0.0,
            "total_estimated_cost_usd": 0.0,
            "recent_runs": [],
        }

    stats_res = await db.execute(
        scoped_runs(select(
            func.avg(AIRun.latency_ms),
            func.avg(AIRun.confidence_score),
            func.avg(AIRun.classification_confidence),
            func.sum(AIRun.estimated_cost),
        ))
    )
    avg_latency, avg_confidence, avg_conf, total_cost = stats_res.fetchone() or (0, 0, 0, 0)

    hitl_count_res = await db.execute(
        scoped_runs(select(func.count(AIRun.id)).where(AIRun.decision == "HITL"))
    )
    hitl_count = hitl_count_res.scalar() or 0

    recent_runs_res = await db.execute(
        scoped_runs(select(AIRun)).order_by(AIRun.created_at.desc()).limit(10)
    )
    recent_runs = recent_runs_res.scalars().all()

    return {
        "total_ai_runs": total_runs,
        "avg_latency_ms": round(float(avg_latency or 0), 2),
        "avg_confidence": round(float(avg_confidence or 0), 3),
        "avg_classification_confidence": round(float(avg_conf or 0), 3),
        "hitl_trigger_rate": round(float(hitl_count / total_runs), 3) if total_runs > 0 else 0.0,
        "total_estimated_cost_usd": round(float(total_cost or 0), 4),
        "recent_runs": [
            {
                "id": r.id,
                "ticket_id": r.ticket_id,
                "trace_id": r.trace_id,
                "workflow": r.workflow,
                "provider": r.provider,
                "model": r.model,
                "latency_ms": r.latency_ms,
                "confidence_score": r.confidence_score,
                "hitl_triggered": r.decision == "HITL",
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in recent_runs
        ],
    }


# ─── Token & Cost Tracking ───────────────────────────────────────────────────

@router.get("/token-usage", response_model=None)
async def get_token_usage_metrics(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Return aggregated Mistral AI token usage and cost metrics for the Admin Dashboard.

    All amounts are pre-computed and stored at write-time; this endpoint only
    reads and aggregates immutable log rows — never recalculates costs.
    """
    from src.models.schemas import (
        TokenUsageMetricsResponse,
        TokenUsageModelBreakdown,
        TokenUsageUserBreakdown,
    )
    from src.models.token_usage import TokenUsageLog

    # 1. Overall totals
    totals_row = await db.execute(
        select(
            func.count(TokenUsageLog.id).label("total_requests"),
            func.coalesce(func.sum(TokenUsageLog.prompt_tokens), 0).label("total_prompt_tokens"),
            func.coalesce(func.sum(TokenUsageLog.completion_tokens), 0).label("total_completion_tokens"),
            func.coalesce(func.sum(TokenUsageLog.estimated_cost), 0.0).label("total_cost"),
        )
    )
    totals = totals_row.one()

    # 2. Per-user breakdown (LEFT JOIN users for username/email)
    user_rows = await db.execute(
        select(
            TokenUsageLog.user_id,
            User.username,
            User.email,
            func.count(TokenUsageLog.id).label("total_requests"),
            func.coalesce(func.sum(TokenUsageLog.prompt_tokens), 0).label("total_prompt_tokens"),
            func.coalesce(func.sum(TokenUsageLog.completion_tokens), 0).label("total_completion_tokens"),
            func.coalesce(func.sum(TokenUsageLog.estimated_cost), 0.0).label("total_cost"),
        )
        .outerjoin(User, User.id == TokenUsageLog.user_id)
        .group_by(TokenUsageLog.user_id, User.username, User.email)
        .order_by(func.sum(TokenUsageLog.estimated_cost).desc())
    )
    user_breakdown = [
        TokenUsageUserBreakdown(
            user_id=row.user_id,
            username=row.username,
            email=row.email,
            total_requests=row.total_requests,
            total_prompt_tokens=row.total_prompt_tokens,
            total_completion_tokens=row.total_completion_tokens,
            total_cost_usd=round(float(row.total_cost), 6),
        )
        for row in user_rows.all()
    ]

    # 3. Per-model breakdown
    model_rows = await db.execute(
        select(
            TokenUsageLog.model_name,
            func.count(TokenUsageLog.id).label("total_requests"),
            func.coalesce(func.sum(TokenUsageLog.prompt_tokens), 0).label("total_prompt_tokens"),
            func.coalesce(func.sum(TokenUsageLog.completion_tokens), 0).label("total_completion_tokens"),
            func.coalesce(func.sum(TokenUsageLog.estimated_cost), 0.0).label("total_cost"),
        )
        .group_by(TokenUsageLog.model_name)
        .order_by(func.sum(TokenUsageLog.estimated_cost).desc())
    )
    model_breakdown = [
        TokenUsageModelBreakdown(
            model_name=row.model_name,
            total_requests=row.total_requests,
            total_prompt_tokens=row.total_prompt_tokens,
            total_completion_tokens=row.total_completion_tokens,
            total_cost_usd=round(float(row.total_cost), 6),
        )
        for row in model_rows.all()
    ]

    return TokenUsageMetricsResponse(
        total_requests=totals.total_requests,
        total_prompt_tokens=totals.total_prompt_tokens,
        total_completion_tokens=totals.total_completion_tokens,
        total_cost_usd=round(float(totals.total_cost), 4),
        user_breakdown=user_breakdown,
        model_breakdown=model_breakdown,
    )

