"""Ticket service — CRUD, SLA, audit log."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.config import get_settings
from src.models.audit_log import AuditAction, AuditLog
from src.models.ticket import Ticket, TicketPriority, TicketStatus, TicketUrgency
from src.models.user import User

settings = get_settings()

# SLA hours by priority
SLA_HOURS: dict[TicketPriority, int] = {
    TicketPriority.LOW: 24,
    TicketPriority.MEDIUM: 8,
    TicketPriority.HIGH: 4,
    TicketPriority.CRITICAL: 1,
}


def _gen_ticket_number() -> str:
    """Generate INC-YYYYMMDD-XXXX style ticket number."""
    now = datetime.now(timezone.utc)
    import random
    return f"INC-{now.strftime('%Y%m%d')}-{random.randint(1000, 9999)}"


async def create_ticket(
    db: AsyncSession,
    title: str,
    description: str,
    submitter_id: int,
    is_production_impact: bool = False,
) -> Ticket:
    ticket = Ticket(
        ticket_number=_gen_ticket_number(),
        title=title,
        description=description,
        submitter_id=submitter_id,
        is_production_impact=is_production_impact,
        status=TicketStatus.OPEN,
    )
    db.add(ticket)
    await db.flush()
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
        .options(selectinload(Ticket.submitter))
        .where(Ticket.id == ticket_id)
    )
    return result.scalar_one_or_none()


async def get_tickets(
    db: AsyncSession,
    status: TicketStatus | None = None,
    submitter_id: int | None = None,
    submitter_company_unit: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Ticket], int]:
    query = select(Ticket)
    if status:
        query = query.where(Ticket.status == status)
    if submitter_id:
        query = query.where(Ticket.submitter_id == submitter_id)
    if submitter_company_unit:
        query = query.join(User, Ticket.submitter_id == User.id).where(
            User.company_unit == submitter_company_unit
        )

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar() or 0

    query = query.order_by(Ticket.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return result.scalars().all(), total


async def get_pending_hitl(db: AsyncSession) -> list[Ticket]:
    result = await db.execute(
        select(Ticket)
        .where(Ticket.status == TicketStatus.PENDING_HITL)
        .order_by(Ticket.created_at.asc())
    )
    return result.scalars().all()


async def update_ticket_classification(
    db: AsyncSession,
    ticket_id: int,
    category: str,
    priority: str,
    urgency: str,
    confidence_score: float,
    suggested_solution: str | None,
    rag_sources: list[str] | None,
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
    ticket.suggested_solution = suggested_solution
    ticket.rag_sources = json.dumps(rag_sources or [])
    ticket.agent_reasoning = agent_reasoning
    ticket.routing_target = routing_target
    ticket.hitl_required = hitl_required

    # Set SLA deadline
    sla_hours = SLA_HOURS.get(TicketPriority(priority), 8)
    ticket.sla_deadline = datetime.now(timezone.utc) + timedelta(hours=sla_hours)

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
        metadata={"category": category, "priority": priority, "confidence": confidence_score},
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
    ticket.hitl_decided_at = datetime.now(timezone.utc)

    action = AuditAction.HITL_APPROVED if approved else AuditAction.HITL_REJECTED
    if approved:
        ticket.status = TicketStatus.IN_PROGRESS
        ticket.first_response_at = datetime.now(timezone.utc)
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
    ticket = await get_ticket(db, ticket_id)
    if not ticket:
        return None

    ticket.status = TicketStatus.CLOSED
    ticket.resolved_at = datetime.now(timezone.utc)
    await db.flush()

    action = (
        AuditAction.TICKET_AUTO_CLOSED if actor_type == "agent"
        else AuditAction.TICKET_MANUALLY_CLOSED
    )
    await write_audit_log(
        db=db,
        ticket_id=ticket_id,
        actor_id=actor_id,
        actor_type=actor_type,
        action=action,
        description=f"Ticket đóng bởi {actor_type}. {note}",
    )
    return ticket


async def escalate_ticket(
    db: AsyncSession,
    ticket_id: int,
    reason: str,
) -> Ticket | None:
    ticket = await get_ticket(db, ticket_id)
    if not ticket:
        return None

    ticket.status = TicketStatus.ESCALATED
    ticket.sla_escalated = True
    await db.flush()

    await write_audit_log(
        db=db,
        ticket_id=ticket_id,
        actor_type="system",
        action=AuditAction.TICKET_ESCALATED,
        description=f"Ticket leo thang SLA: {reason}",
    )
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
        metadata_json=json.dumps(metadata) if metadata else None,
        confidence_score=confidence_score,
        model_used=model_used,
    )
    db.add(log)
    await db.flush()
    return log
