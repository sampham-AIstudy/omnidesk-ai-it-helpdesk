"""Ticket service — CRUD, SLA, audit log."""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.config import get_settings
from src.models.audit_log import AuditAction, AuditLog
from src.models.ticket import Ticket, TicketPriority, TicketStatus
from src.models.user import User
from src.timezone import vietnam_now

logger = logging.getLogger(__name__)
settings = get_settings()


# SLA hours by priority
SLA_HOURS: dict[TicketPriority, int] = {
    TicketPriority.LOW: 24,
    TicketPriority.MEDIUM: 8,
    TicketPriority.HIGH: 4,
    TicketPriority.CRITICAL: 1,
}
_TICKET_NUMBER_MAX_ATTEMPTS = 8


def _gen_ticket_number() -> str:
    """Generate INC-YYYYMMDD-XXXX style ticket number."""
    now = vietnam_now()
    import random
    return f"INC-{now.strftime('%Y%m%d')}-{random.randint(1000, 9999)}"


async def create_ticket(
    db: AsyncSession,
    title: str,
    description: str,
    submitter_id: int,
    is_production_impact: bool = False,
    duplicate_of_ticket_id: int | None = None,
    duplicate_score: float | None = None,
    duplicate_detection_method: str | None = None,
    duplicate_confirmed_by: str | None = None,
) -> Ticket:
    # The database unique constraint is the concurrency authority.  A nested
    # transaction lets a rare collision roll back only its insert, then retry
    # without poisoning the caller's outer unit of work.
    ticket: Ticket | None = None
    for attempt in range(_TICKET_NUMBER_MAX_ATTEMPTS):
        candidate = Ticket(
            ticket_number=_gen_ticket_number(),
            title=title,
            description=description,
            submitter_id=submitter_id,
            is_production_impact=is_production_impact,
            status=TicketStatus.OPEN,
            duplicate_of_ticket_id=duplicate_of_ticket_id,
            duplicate_score=duplicate_score,
            duplicate_detection_method=duplicate_detection_method,
            duplicate_confirmed_by=duplicate_confirmed_by,
        )
        try:
            async with db.begin_nested():
                db.add(candidate)
                await db.flush()
            ticket = candidate
            break
        except IntegrityError as exc:
            if attempt + 1 == _TICKET_NUMBER_MAX_ATTEMPTS:
                raise RuntimeError("Could not allocate a unique ticket number after bounded retries.") from exc

    if ticket is None:  # Defensive guard; the loop either returns or raises.
        raise RuntimeError("Could not allocate a unique ticket number.")
    await db.refresh(ticket)

    await write_audit_log(
        db=db,
        ticket_id=ticket.id,
        actor_id=submitter_id,
        actor_type="user",
        action=AuditAction.TICKET_CREATED,
        description=f"Ticket '{title}' được tạo bởi user #{submitter_id}",
    )
    return ticket


async def get_ticket(db: AsyncSession, ticket_id: int) -> Ticket | None:
    result = await db.execute(
        select(Ticket)
        .options(selectinload(Ticket.submitter), selectinload(Ticket.assignee))
        .where(Ticket.id == ticket_id)
    )
    return result.scalar_one_or_none()



async def get_tickets(
    db: AsyncSession,
    status: TicketStatus | None = None,
    submitter_id: int | None = None,
    submitter_company_unit: str | None = None,
    search: str | None = None,
    priority: TicketPriority | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Ticket], int]:
    query = select(Ticket).options(
        selectinload(Ticket.submitter),
        selectinload(Ticket.assignee),
    )
    if status:
        query = query.where(Ticket.status == status)
    if submitter_id:
        query = query.where(Ticket.submitter_id == submitter_id)
    if priority:
        query = query.where(Ticket.priority == priority)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(or_(
            Ticket.ticket_number.ilike(pattern),
            Ticket.title.ilike(pattern),
            Ticket.description.ilike(pattern),
        ))
    if submitter_company_unit:
        query = query.join(User, Ticket.submitter_id == User.id).where(
            User.company_unit == submitter_company_unit
        )

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar() or 0

    sort_columns = {
        "created_at": Ticket.created_at,
        "updated_at": Ticket.updated_at,
        "priority": Ticket.priority,
        "sla_deadline": Ticket.sla_deadline,
        "confidence_score": Ticket.confidence_score,
    }
    sort_column = sort_columns.get(sort_by, Ticket.created_at)
    query = query.order_by(
        Ticket.is_pinned.desc(),
        sort_column.asc() if sort_order == "asc" else sort_column.desc(),
        Ticket.id.desc(),
    )
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return list(result.scalars().all()), total


async def set_ticket_pinned(
    db: AsyncSession,
    ticket_id: int,
    pinned: bool,
    actor: User,
    reason: str | None = None,
) -> Ticket | None:
    ticket = await get_ticket(db, ticket_id)
    if not ticket:
        return None

    if ticket.status in {TicketStatus.CLOSED, TicketStatus.RESOLVED, TicketStatus.REJECTED}:
        raise ValueError(f"Không thể thay đổi ghim sự cố đã kết thúc ({ticket.status})")

    from datetime import datetime, timezone
    ticket.is_pinned = pinned
    if pinned:
        ticket.pinned_by_id = actor.id
        ticket.pinned_at = datetime.now(timezone.utc)
        ticket.pin_reason = reason.strip() if reason else None
        action = AuditAction.TICKET_PINNED
        desc = f"Sự cố đã được ghim ưu tiên đầu hàng đợi bởi {actor.full_name}" + (f": {reason.strip()}" if reason and reason.strip() else "")
    else:
        ticket.pinned_by_id = None
        ticket.pinned_at = None
        ticket.pin_reason = None
        action = AuditAction.TICKET_UNPINNED
        desc = f"Sự cố đã được bỏ ghim ưu tiên bởi {actor.full_name}"

    await write_audit_log(
        db=db,
        ticket_id=ticket_id,
        actor_id=actor.id,
        actor_type="user",
        action=action,
        description=desc,
        metadata={
            "pinned": pinned,
            "reason": reason,
            "actor_id": actor.id,
            "actor_role": actor.role.value if hasattr(actor.role, "value") else str(actor.role),
        },
    )

    await db.flush()
    await db.refresh(ticket)
    return ticket


async def get_pending_hitl(
    db: AsyncSession, submitter_company_unit: str | None = None
) -> list[Ticket]:
    query = select(Ticket).where(Ticket.status == TicketStatus.PENDING_HITL)
    if submitter_company_unit:
        query = query.join(User, Ticket.submitter_id == User.id).where(
            User.company_unit == submitter_company_unit
        )
    result = await db.execute(query.order_by(Ticket.created_at.asc()))
    return list(result.scalars().all())


async def update_ticket_classification(
    db: AsyncSession,
    ticket_id: int,
    category: str,
    priority: str,
    urgency: str,
    confidence_score: float,
    retrieval_confidence: float | None,
    groundedness_score: float | None,
    suggested_solution: str | None,
    rag_sources: list[str | dict[str, Any]] | None,
    agent_reasoning: str | None,
    routing_target: str | None,
    hitl_required: bool,
    model_used: str,
) -> Ticket | None:
    ticket = await get_ticket(db, ticket_id)
    if not ticket:
        return None

    from src.models.ticket import TicketCategory, TicketPriority, TicketUrgency

    ticket.category = TicketCategory(category)
    ticket.priority = TicketPriority(priority)
    ticket.urgency = TicketUrgency(urgency)
    ticket.confidence_score = confidence_score
    ticket.retrieval_confidence = retrieval_confidence
    ticket.groundedness_score = groundedness_score
    ticket.suggested_solution = suggested_solution
    ticket.rag_sources = json.dumps(rag_sources or [])
    ticket.agent_reasoning = agent_reasoning
    ticket.routing_target = routing_target
    ticket.hitl_required = hitl_required

    # Set SLA deadline
    sla_hours = SLA_HOURS.get(TicketPriority(priority), 8)
    ticket.sla_deadline = datetime.now(UTC) + timedelta(hours=sla_hours)

    if hitl_required:
        ticket.status = TicketStatus.PENDING_HITL
    else:
        ticket.status = TicketStatus.IN_PROGRESS

    await db.flush()

    await write_audit_log(
        db=db,
        ticket_id=ticket_id,
        actor_type="agent",
        action=AuditAction.TICKET_CLASSIFIED,
        description=(
            f"AI phân loại: category={category}, priority={priority}, "
            f"confidence={confidence_score:.2f}, hitl={hitl_required}"
        ),
        metadata={
            "category": category,
            "priority": priority,
            "classification_confidence": confidence_score,
            "retrieval_confidence": retrieval_confidence,
            "groundedness_score": groundedness_score,
        },
        confidence_score=confidence_score,
        model_used=model_used,
    )
    return ticket


async def apply_hitl_decision(
    db: AsyncSession,
    ticket_id: int,
    approved: bool,
    manager_id: int,
    note: str | None,
) -> Ticket | None:
    ticket = await get_ticket(db, ticket_id)
    if not ticket:
        return None

    ticket.hitl_approved_by_id = manager_id
    ticket.hitl_note = note
    ticket.hitl_decided_at = datetime.now(UTC)

    action = AuditAction.HITL_APPROVED if approved else AuditAction.HITL_REJECTED
    if approved:
        ticket.status = TicketStatus.IN_PROGRESS
        ticket.first_response_at = datetime.now(UTC)
    else:
        ticket.status = TicketStatus.OPEN
        ticket.hitl_required = False

    await db.flush()

    await write_audit_log(
        db=db,
        ticket_id=ticket_id,
        actor_id=manager_id,
        actor_type="user",
        action=action,
        description=f"Manager {'phê duyệt' if approved else 'từ chối'} HITL. Note: {note or 'N/A'}",
    )
    return ticket


async def close_ticket(
    db: AsyncSession,
    ticket_id: int,
    actor_id: int | None,
    actor_type: str,
    note: str = "",
) -> Ticket | None:
    if actor_type == "agent":
        raise ValueError("AI agent không có quyền đóng ticket")
    ticket = await get_ticket(db, ticket_id)
    if not ticket:
        return None

    ticket.status = TicketStatus.CLOSED
    ticket.resolved_at = datetime.now(UTC)
    await db.flush()

    # Ticket text may include PII, credentials, customer data and tenant-only
    # incidents. Knowledge publication must be a reviewed KB workflow, never
    # an automatic side effect of closing a ticket.
    logger.info("KB publication requires an approved, redacted KB review for ticket #%s", ticket.ticket_number)

    try:
        from src.services.zero_mem_service import index_ticket_trace
        await index_ticket_trace(db, ticket)
    except Exception as exc:
        logger.warning("Could not refresh episodic ticket trace %s: %s", ticket.id, exc)

    await write_audit_log(
        db=db,
        ticket_id=ticket_id,
        actor_id=actor_id,
        actor_type=actor_type,
        action=AuditAction.TICKET_MANUALLY_CLOSED,
        description=f"Ticket đóng bởi {actor_type}. {note}",
    )
    await db.refresh(ticket)
    return ticket



async def escalate_ticket(
    db: AsyncSession,
    ticket_id: int,
    reason: str,
    actor: User | None = None,
    escalate_to: str = "manager",
    bump_priority: bool = False,
    handover_notes: str | None = None,
) -> Ticket | None:
    ticket = await get_ticket(db, ticket_id)
    if not ticket:
        return None

    if ticket.status in {TicketStatus.CLOSED, TicketStatus.RESOLVED, TicketStatus.REJECTED}:
        raise ValueError(f"Không thể leo thang sự cố đã kết thúc ({ticket.status})")

    old_status = ticket.status.value if hasattr(ticket.status, "value") else str(ticket.status)
    old_priority = ticket.priority.value if hasattr(ticket.priority, "value") and ticket.priority else str(ticket.priority)

    from src.models.ticket import TicketPriority, TicketStatus
    ticket.status = TicketStatus.ESCALATED
    ticket.sla_escalated = True

    if bump_priority:
        ticket.priority = TicketPriority.CRITICAL

    from src.models.ticket_message import TicketMessageSender
    from src.services.ticket_conversation_service import add_message

    actor_name = actor.full_name if actor else "Hệ thống"
    actor_role = actor.role.value if actor and hasattr(actor.role, "value") else "system"
    msg_parts = [
        f"🚨 **[SỰ CỐ LEO THANG / ESCALATED]**",
        f"• **Người thực hiện:** {actor_name} ({actor_role})",
        f"• **Chuyển cấp:** {escalate_to.upper()}",
        f"• **Lý do:** {reason}",
    ]
    if handover_notes and handover_notes.strip():
        msg_parts.append(f"• **Ghi chú bàn giao:** {handover_notes.strip()}")
    if bump_priority:
        msg_parts.append("• **Độ ưu tiên:** Đã nâng lên **KHẨN CẤP (CRITICAL P1)**")

    await add_message(
        db,
        ticket_id=ticket_id,
        sender_type=TicketMessageSender.SYSTEM,
        content="\n".join(msg_parts),
    )

    await write_audit_log(
        db=db,
        ticket_id=ticket_id,
        actor_id=actor.id if actor else None,
        actor_type="user" if actor else "system",
        action=AuditAction.TICKET_ESCALATED,
        description=f"Sự cố leo thang lên {escalate_to}: {reason}",
        metadata={
            "escalate_to": escalate_to,
            "reason": reason,
            "bump_priority": bump_priority,
            "handover_notes": handover_notes,
            "old_status": old_status,
            "new_status": TicketStatus.ESCALATED.value,
            "old_priority": old_priority,
            "new_priority": ticket.priority.value if hasattr(ticket.priority, "value") and ticket.priority else str(ticket.priority),
        },
    )

    await db.flush()
    await db.refresh(ticket)
    return ticket


async def takeover_ticket(
    db: AsyncSession,
    ticket_id: int,
    technician_id: int,
) -> Ticket | None:
    """Explicit Agent Takeover: Technician claims ticket and transitions state to IN_PROGRESS + HUMAN."""
    ticket = await get_ticket(db, ticket_id)
    if not ticket:
        return None

    old_status = ticket.status.value if hasattr(ticket.status, 'value') else str(ticket.status)
    from src.models.ticket import TicketSupportMode
    ticket.assignee_id = technician_id
    ticket.status = TicketStatus.IN_PROGRESS
    ticket.support_mode = TicketSupportMode.HUMAN
    await db.flush()

    tech_user = await db.get(User, technician_id)
    tech_name = tech_user.full_name if tech_user else f"Chuyên viên #{technician_id}"

    from src.models.ticket_message import TicketMessageSender
    from src.services.ticket_conversation_service import add_message
    await add_message(
        db,
        ticket_id=ticket.id,
        sender_type=TicketMessageSender.SYSTEM,
        sender_id=technician_id,
        content=f"👨‍💻 Chuyên viên {tech_name} đã tiếp nhận xử lý ticket.",
    )

    await write_audit_log(
        db=db,
        ticket_id=ticket_id,
        actor_id=technician_id,
        actor_type="technician",
        action=AuditAction.TICKET_ASSIGNED,
        description=f"Chuyên viên {tech_name} tiếp nhận ticket #{ticket.ticket_number}",
        metadata={"old_status": old_status, "new_status": TicketStatus.IN_PROGRESS.value, "support_mode": "human"},
    )

    await db.refresh(ticket)
    return ticket



async def write_audit_log(
    db: AsyncSession,
    action: AuditAction,
    description: str,
    ticket_id: int | None = None,
    actor_id: int | None = None,
    actor_type: str = "system",
    metadata: dict | None = None,
    confidence_score: float | None = None,
    model_used: str | None = None,
) -> AuditLog:
    log = AuditLog(
        ticket_id=ticket_id,
        actor_id=actor_id,
        actor_type=actor_type,
        action=action,
        description=description,
        metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
        confidence_score=confidence_score,
        model_used=model_used,
    )
    db.add(log)
    await db.flush()
    return log
