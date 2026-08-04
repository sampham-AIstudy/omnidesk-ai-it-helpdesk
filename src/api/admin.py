"""Admin API — User management, KB management."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth import get_current_active_user
from src.database import get_db
from src.models.knowledge_base import KnowledgeBaseEntry
from src.models.audit_log import AuditAction
from src.models.schemas import KBEntryCreate, KBEntryResponse, KBEntryUpdate, UserCreate, UserResponse
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


# ─── User Management ──────────────────────────────────────────────────────────

@router.get("/users", response_model=list[UserResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_manager_or_admin),
):
    result = await db.execute(select(User).order_by(User.created_at.desc()))
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
    user = await auth_service.create_user(db, **payload.model_dump())
    return UserResponse.model_validate(user)


# ─── Knowledge Base Management ────────────────────────────────────────────────

@router.get("/kb", response_model=list[KBEntryResponse])
async def list_kb(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_manager_or_admin),
):
    result = await db.execute(
        select(KnowledgeBaseEntry)
        .where(KnowledgeBaseEntry.is_active == True)
        .order_by(KnowledgeBaseEntry.id)
    )
    entries = result.scalars().all()
    return [KBEntryResponse.model_validate(e) for e in entries]


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
