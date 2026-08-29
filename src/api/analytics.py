"""Analytics API — SLA metrics, classification accuracy, dashboard."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth import get_current_active_user
from src.database import get_db
from src.models.audit_log import AuditLog
from src.models.schemas import ClassificationMetrics, DashboardResponse, SLAMetrics, TicketResponse
from src.models.ticket import Ticket, TicketStatus
from src.models.user import User, UserRole
from src.services import auth_service
from src.services.ticket_service import get_pending_hitl, get_tickets

router = APIRouter(prefix="/analytics", tags=["Analytics"])


def _require_analytics_role(current_user: User) -> None:
    if current_user.role not in {UserRole.TECHNICIAN, UserRole.ADMIN}:
        raise HTTPException(status_code=403, detail="Technician or administrator access is required")


def _ticket_scope_clause(current_user: User):
    """Apply the same company boundary to aggregate and drill-down analytics."""
    company_scope = auth_service.scoped_company_unit(current_user)
    if company_scope is None:
        return None
    return Ticket.submitter_id.in_(
        select(User.id).where(User.company_unit == company_scope)
    )


def _apply_ticket_scope(query, current_user: User):
    clause = _ticket_scope_clause(current_user)
    return query.where(clause) if clause is not None else query


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Tenant-scoped operational dashboard for Technician/Admin."""
    _require_analytics_role(current_user)

    # Classification metrics
    total_result = await db.execute(_apply_ticket_scope(select(func.count()).select_from(Ticket), current_user))
    total = total_result.scalar() or 0

    classified_result = await db.execute(_apply_ticket_scope(
        select(func.count()).select_from(Ticket).where(Ticket.category.isnot(None)), current_user
    ))
    auto_classified = classified_result.scalar() or 0

    hitl_result = await db.execute(_apply_ticket_scope(
        select(func.count()).select_from(Ticket).where(Ticket.hitl_required), current_user
    ))
    hitl_count = hitl_result.scalar() or 0

    closed_result = await db.execute(_apply_ticket_scope(
        select(func.count()).select_from(Ticket).where(Ticket.status == TicketStatus.CLOSED), current_user
    ))
    auto_closed = closed_result.scalar() or 0

    # Avg confidence
    conf_result = await db.execute(_apply_ticket_scope(
        select(func.avg(Ticket.confidence_score)).where(Ticket.confidence_score.isnot(None)), current_user
    ))
    avg_conf = conf_result.scalar()

    # Low confidence rate (< 0.6)
    low_conf_result = await db.execute(_apply_ticket_scope(
        select(func.count()).select_from(Ticket)
        .where(Ticket.confidence_score < 0.6)
        .where(Ticket.confidence_score.isnot(None)), current_user
    ))
    low_conf = low_conf_result.scalar() or 0
    low_conf_rate = (low_conf / auto_classified) if auto_classified > 0 else 0

    classification = ClassificationMetrics(
        total_tickets=total,
        auto_classified=auto_classified,
        hitl_triggered=hitl_count,
        auto_closed=auto_closed,
        avg_confidence=round(avg_conf, 3) if avg_conf else None,
        low_confidence_rate=round(low_conf_rate, 3),
    )

    # SLA metrics
    now = datetime.now(UTC)
    sla_total_result = await db.execute(_apply_ticket_scope(
        select(func.count()).select_from(Ticket).where(Ticket.sla_deadline.isnot(None)), current_user
    ))
    sla_total = sla_total_result.scalar() or 0

    breach_result = await db.execute(_apply_ticket_scope(
        select(func.count()).select_from(Ticket)
        .where(Ticket.sla_deadline < now)
        .where(Ticket.status.not_in([TicketStatus.CLOSED, TicketStatus.RESOLVED])), current_user
    ))
    sla_breached = breach_result.scalar() or 0

    escalated_result = await db.execute(_apply_ticket_scope(
        select(func.count()).select_from(Ticket).where(Ticket.sla_escalated), current_user
    ))
    escalated = escalated_result.scalar() or 0

    within_sla = max(0, sla_total - sla_breached)
    compliance = (within_sla / sla_total) if sla_total > 0 else None

    sla = SLAMetrics(
        total_tickets=sla_total,
        within_sla=within_sla,
        sla_breached=sla_breached,
        escalated=escalated,
        sla_compliance_rate=round(compliance, 3) if compliance else None,
    )

    # Recent tickets
    company_scope = auth_service.scoped_company_unit(current_user)
    recent_tickets, _ = await get_tickets(
        db=db, page=1, page_size=10,
        submitter_company_unit=company_scope.value if company_scope else None,
    )
    pending_hitl = await get_pending_hitl(
        db, submitter_company_unit=company_scope.value if company_scope else None
    )

    return DashboardResponse(
        classification=classification,
        sla=sla,
        recent_tickets=[TicketResponse.model_validate(t) for t in recent_tickets],
        pending_hitl=[TicketResponse.model_validate(t) for t in pending_hitl],
    )


@router.get("/audit-logs")
async def get_audit_logs(
    ticket_id: int | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Ticket audit log for authenticated callers within their ticket scope."""
    if current_user.role == UserRole.EMPLOYEE:
        # Employee chỉ xem audit log của ticket mình
        if not ticket_id:
            return {"items": [], "total": 0}

        ticket = await db.get(Ticket, ticket_id)
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        if ticket.submitter_id != current_user.id:
            raise HTTPException(status_code=403, detail="You cannot view this ticket audit log")

    query = select(AuditLog)
    company_scope = auth_service.scoped_company_unit(current_user)
    if company_scope:
        query = query.where(
            AuditLog.ticket_id.in_(
                select(Ticket.id).where(
                    Ticket.submitter_id.in_(select(User.id).where(User.company_unit == company_scope))
                )
            )
        )
    if ticket_id:
        query = query.where(AuditLog.ticket_id == ticket_id)
    query = query.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    logs = result.scalars().all()

    from src.models.schemas import AuditLogResponse
    return {
        "items": [AuditLogResponse.model_validate(log) for log in logs],
        "total": len(logs),
    }


@router.get("/sla-alerts")
async def get_sla_alerts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Tickets sắp vi phạm SLA (còn < 1 giờ)."""
    now = datetime.now(UTC)
    _require_analytics_role(current_user)
    warning_threshold = now + timedelta(hours=1)

    result = await db.execute(_apply_ticket_scope(
        select(Ticket)
        .where(Ticket.sla_deadline.between(now, warning_threshold))
        .where(Ticket.status.not_in([TicketStatus.CLOSED, TicketStatus.RESOLVED]))
        .order_by(Ticket.sla_deadline.asc()), current_user
    ))
    tickets = result.scalars().all()
    return [TicketResponse.model_validate(t) for t in tickets]
