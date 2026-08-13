"""Admin API — User management, KB management."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth import get_current_active_user
from src.database import get_db
from src.models.audit_log import AuditAction
from src.models.knowledge_base import KnowledgeBaseEntry
from src.models.schemas import KBEntryCreate, KBEntryResponse, KBEntryUpdate, UserCreate, UserResponse
from src.models.ticket import Ticket
from src.models.user import User, UserRole
from src.services import auth_service
from src.services.rag_service import delete_document, get_collection_count, index_document
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
    return UserResponse.model_validate(user)


# ─── Knowledge Base Management ────────────────────────────────────────────────

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
            func.avg(AIRun.groundedness_score),
            func.avg(AIRun.confidence_score),
            func.sum(AIRun.estimated_cost),
        ))
    )
    avg_latency, avg_ground, avg_conf, total_cost = stats_res.fetchone() or (0, 0, 0, 0)

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
        "avg_groundedness": round(float(avg_ground or 0), 3),
        "avg_confidence": round(float(avg_conf or 0), 3),
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
                "groundedness_score": r.groundedness_score,
                "hitl_triggered": r.decision == "HITL",
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in recent_runs
        ],
    }
