"""Tickets API — CRUD + agent workflow trigger + HITL decisions."""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth import get_current_active_user
from src.database import get_db
from src.models.schemas import (
    AgentProcessResponse,
    HITLDecisionRequest,
    TicketCreate,
    TicketListResponse,
    TicketResponse,
    TicketStatusUpdate,
)
from src.models.ticket import TicketStatus
from src.models.user import CompanyUnit, User, UserRole
from src.services import auth_service, ticket_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tickets", tags=["Tickets"])


# ─── Submit Ticket ────────────────────────────────────────────────────────────

@router.post("", response_model=AgentProcessResponse, status_code=201)
async def create_ticket(
    payload: TicketCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Nhân viên gửi ticket mới → Agent tự động xử lý trong background."""
    ticket = await ticket_service.create_ticket(
        db=db,
        title=payload.title,
        description=payload.description,
        submitter_id=current_user.id,
        is_production_impact=payload.is_production_impact,
    )

    # Trigger agent workflow in background
    background_tasks.add_task(
        _run_agent_workflow,
        ticket_id=ticket.id,
        ticket_number=ticket.ticket_number,
        title=ticket.title,
        description=ticket.description,
        submitter_id=current_user.id,
        is_production_impact=ticket.is_production_impact,
        submitter_is_vip=current_user.is_vip,
        company_unit=current_user.company_unit.value,
        department=current_user.department,
    )

    return AgentProcessResponse(
        ticket_id=ticket.id,
        ticket_number=ticket.ticket_number,
        status=ticket.status,
        category=None,
        priority=None,
        confidence_score=None,
        suggested_solution=None,
        hitl_required=False,
        action_taken="processing",
        message="Ticket đã được tạo. Agent đang phân tích...",
    )


async def _run_agent_workflow(
    ticket_id: int,
    ticket_number: str,
    title: str,
    description: str,
    submitter_id: int,
    is_production_impact: bool,
    submitter_is_vip: bool,
    company_unit: str,
    department: str | None,
):
    """Background task: chạy LangGraph workflow và cập nhật DB."""
    from src.agents.graph import process_ticket
    from src.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            # Update status to classifying
            ticket = await ticket_service.get_ticket(db, ticket_id)
            if ticket:
                ticket.status = TicketStatus.CLASSIFYING
                await db.flush()
                await db.commit()

            # Run agent
            final_state = await process_ticket(
                ticket_id=ticket_id,
                ticket_number=ticket_number,
                title=title,
                description=description,
                submitter_id=submitter_id,
                is_production_impact=is_production_impact,
                submitter_is_vip=submitter_is_vip,
                company_unit=company_unit,
                department=department,
            )

            # Persist results back to DB
            await ticket_service.update_ticket_classification(
                db=db,
                ticket_id=ticket_id,
                category=final_state.get("category", "other"),
                priority=final_state.get("priority", "medium"),
                urgency=final_state.get("urgency", "medium"),
                confidence_score=final_state.get("confidence_score", 0.5),
                suggested_solution=final_state.get("suggested_solution"),
                rag_sources=final_state.get("rag_sources", []),
                agent_reasoning=final_state.get("agent_reasoning"),
                routing_target=final_state.get("routing_target"),
                hitl_required=final_state.get("hitl_required", False),
                model_used=final_state.get("model_used", "mistral"),
            )

            # Auto-close if eligible
            if final_state.get("auto_close_eligible") and not final_state.get("hitl_required"):
                await ticket_service.close_ticket(
                    db=db,
                    ticket_id=ticket_id,
                    actor_id=None,
                    actor_type="agent",
                    note=f"Auto-closed. Solution provided via RAG. Confidence: {final_state.get('confidence_score', 0):.0%}",
                )

            await db.commit()
            logger.info(f"Agent workflow completed for ticket #{ticket_number}")

        except Exception as e:
            await db.rollback()
            logger.error(f"Agent workflow error for ticket #{ticket_number}: {e}")


# ─── List Tickets ──────────────────────────────────────────────────────────────

@router.get("", response_model=TicketListResponse)
async def list_tickets(
    status: TicketStatus | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Danh sách tickets. Employee chỉ thấy ticket của mình."""
    submitter_id = None
    submitter_company_unit = None
    if current_user.role == UserRole.EMPLOYEE:
        submitter_id = current_user.id
    elif (
        current_user.role in (UserRole.TECHNICIAN, UserRole.MANAGER)
        and current_user.company_unit != CompanyUnit.CORPORATE
    ):
        submitter_company_unit = current_user.company_unit

    tickets, total = await ticket_service.get_tickets(
        db=db,
        status=status,
        submitter_id=submitter_id,
        submitter_company_unit=submitter_company_unit,
        page=page,
        page_size=page_size,
    )

    return TicketListResponse(
        items=[TicketResponse.model_validate(t) for t in tickets],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/pending-hitl", response_model=list[TicketResponse])
async def get_pending_hitl(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Danh sách ticket chờ HITL approval — chỉ Manager/Admin."""
    if not auth_service.can_approve_hitl(current_user):
        raise HTTPException(status_code=403, detail="Chỉ Manager hoặc Admin mới xem được")

    tickets = await ticket_service.get_pending_hitl(db)
    return [TicketResponse.model_validate(t) for t in tickets]


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket không tồn tại")
    if not auth_service.can_view_ticket(current_user, ticket):
        raise HTTPException(status_code=403, detail="Không có quyền xem ticket này")
    return TicketResponse.model_validate(ticket)


# ─── HITL Decision ─────────────────────────────────────────────────────────────

@router.post("/{ticket_id}/approve", response_model=TicketResponse)
async def approve_ticket(
    ticket_id: int,
    payload: HITLDecisionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Manager phê duyệt hoặc từ chối ticket HITL."""
    if not auth_service.can_approve_hitl(current_user):
        raise HTTPException(status_code=403, detail="Chỉ Manager hoặc Admin mới phê duyệt được")

    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket không tồn tại")
    if ticket.status != TicketStatus.PENDING_HITL:
        raise HTTPException(status_code=400, detail=f"Ticket không ở trạng thái PENDING_HITL (hiện: {ticket.status})")

    updated = await ticket_service.apply_hitl_decision(
        db=db,
        ticket_id=ticket_id,
        approved=payload.approved,
        manager_id=current_user.id,
        note=payload.note,
    )
    return TicketResponse.model_validate(updated)


# ─── Manual Status Update ─────────────────────────────────────────────────────

@router.patch("/{ticket_id}/status", response_model=TicketResponse)
async def update_status(
    ticket_id: int,
    payload: TicketStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Technician/Manager cập nhật trạng thái ticket thủ công."""
    if current_user.role == UserRole.EMPLOYEE:
        raise HTTPException(status_code=403, detail="Nhân viên không thể cập nhật trạng thái")

    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket không tồn tại")

    if payload.status == TicketStatus.CLOSED:
        await ticket_service.close_ticket(
            db=db,
            ticket_id=ticket_id,
            actor_id=current_user.id,
            actor_type="user",
            note=payload.note or "",
        )
    else:
        from src.models.audit_log import AuditAction
        ticket.status = payload.status
        await db.flush()
        await ticket_service.write_audit_log(
            db=db,
            ticket_id=ticket_id,
            actor_id=current_user.id,
            actor_type="user",
            action=AuditAction.STATUS_CHANGED,
            description=f"Trạng thái thay đổi → {payload.status}. Note: {payload.note or 'N/A'}",
        )

    await db.refresh(ticket)
    return TicketResponse.model_validate(ticket)


@router.post("/{ticket_id}/escalate", response_model=TicketResponse)
async def escalate_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Technician leo thang ticket thủ công."""
    if current_user.role == UserRole.EMPLOYEE:
        raise HTTPException(status_code=403, detail="Không có quyền leo thang")

    ticket = await ticket_service.escalate_ticket(
        db=db,
        ticket_id=ticket_id,
        reason=f"Leo thang thủ công bởi {current_user.full_name}",
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket không tồn tại")
    return TicketResponse.model_validate(ticket)


@router.post("/{ticket_id}/confirm-resolution", response_model=TicketResponse)
async def confirm_resolution(
    ticket_id: int,
    resolved: bool = Query(..., description="True nếu đã giải quyết, False nếu chưa"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Người dùng xác nhận kết quả giải pháp AI đề xuất (dùng cho ngưỡng 70%-85%)."""
    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket không tồn tại")
    if ticket.submitter_id != current_user.id and current_user.role == UserRole.EMPLOYEE:
        raise HTTPException(status_code=403, detail="Chỉ người tạo ticket mới có quyền xác nhận")

    if resolved:
        await ticket_service.close_ticket(
            db=db,
            ticket_id=ticket_id,
            actor_id=current_user.id,
            actor_type="user",
            note="Người dùng xác nhận giải pháp AI thành công.",
        )
    else:
        from src.models.audit_log import AuditAction
        ticket.status = TicketStatus.ESCALATED
        await db.flush()
        await ticket_service.write_audit_log(
            db=db,
            ticket_id=ticket_id,
            actor_id=current_user.id,
            actor_type="user",
            action=AuditAction.STATUS_CHANGED,
            description="Người dùng báo giải pháp không thành công, ticket đã gửi tới phòng ban phụ trách.",
        )

    await db.refresh(ticket)
    return TicketResponse.model_validate(ticket)

