"""Tickets API — CRUD + agent workflow trigger + HITL decisions."""
from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth import get_current_active_user
from src.database import get_db
from src.models.schemas import (
    AgentProcessResponse,
    HITLDecisionRequest,
    TicketCreate,
    TicketConversationResponse,
    TicketListResponse,
    TicketMessageCreate,
    TicketMessageResponse,
    TicketResponse,
    TicketStatusUpdate,
)
from src.models.ticket import TicketStatus
from src.models.user import CompanyUnit, User, UserRole
from src.services import auth_service, ticket_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tickets", tags=["Tickets"])


from fastapi import Header

_idempotency_store: dict[str, AgentProcessResponse] = {}


# ─── Submit Ticket ────────────────────────────────────────────────────────────

@router.post("", response_model=AgentProcessResponse, status_code=201)
async def create_ticket(
    payload: TicketCreate,
    background_tasks: BackgroundTasks,
    x_idempotency_key: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Nhân viên gửi ticket mới (hỗ trợ X-Idempotency-Key chống trùng lặp) → Agent xử lý background."""
    if x_idempotency_key and x_idempotency_key in _idempotency_store:
        logger.info(f"Idempotency Key hit: {x_idempotency_key}")
        return _idempotency_store[x_idempotency_key]

    ticket = await ticket_service.create_ticket(
        db=db,
        title=payload.title,
        description=payload.description,
        submitter_id=current_user.id,
        is_production_impact=payload.is_production_impact,
    )
    await db.commit()

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

    response_data = AgentProcessResponse(
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

    if x_idempotency_key:
        _idempotency_store[x_idempotency_key] = response_data

    return response_data


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

            # Check if Guardrail Step 1 Short-Circuited / Blocked
            if final_state.get("is_blocked"):
                ticket = await ticket_service.get_ticket(db, ticket_id)
                if ticket:
                    ticket.status = TicketStatus.REJECTED
                    ticket.closed_by = "security_guardrail"
                    ticket.suggested_solution = final_state.get("safe_response")
                    await db.flush()

                    from src.services.ticket_conversation_service import add_message
                    ticket.status = TicketStatus.SECURITY_REVIEW
                    from src.models.ticket_message import TicketMessageSender
                    await add_message(
                        db,
                        ticket_id=ticket.id,
                        sender_type=TicketMessageSender.SYSTEM,
                        sender_id=None,
                        content=f"🛡️ Ticket được đưa vào trạng thái SECURITY_REVIEW (Kiểm tra An ninh Forensic Audit).\nLý do: {final_state.get('block_reason')}",
                    )

                    from src.models.audit_log import AuditAction
                    await ticket_service.write_audit_log(
                        db=db,
                        ticket_id=ticket_id,
                        actor_type="system",
                        action=AuditAction.STATUS_CHANGED,
                        description=f"Security Guardrail Event: {final_state.get('block_reason')}",
                        metadata={"is_blocked": True, "reason": final_state.get("block_reason"), "status": "security_review"},
                    )
                await db.commit()
                logger.warning(f"Guardrail Step 1 Security Review triggered for ticket #{ticket_number}")
                return

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
            ticket = await ticket_service.get_ticket(db, ticket_id)
            if ticket:
                from src.services.ticket_conversation_service import seed_agent_opening
                await seed_agent_opening(db, ticket)

            # Apply State Machine V2 Transitions based on Policy Engine
            ticket = await ticket_service.get_ticket(db, ticket_id)
            if ticket:
                if final_state.get("hitl_required"):
                    ticket.status = TicketStatus.PENDING_HITL
                    # Create Action-Level HITL Approval Record
                    from src.models.hitl_approval import HITLApproval
                    hitl_record = HITLApproval(
                        ticket_id=ticket_id,
                        action_type="EXECUTE_HIGH_RISK",
                        action_payload=final_state.get("suggested_solution"),
                        risk_score=final_state.get("risk_score", 0.70),
                        reason=final_state.get("hitl_reason", "Policy Engine Decision"),
                    )
                    db.add(hitl_record)
                elif final_state.get("action_taken") == "ask_clarification":
                    ticket.status = TicketStatus.NEEDS_CLARIFICATION
                elif final_state.get("action_taken") == "human_handoff":
                    ticket.status = TicketStatus.WAITING_FOR_AGENT
                elif final_state.get("auto_close_eligible") or final_state.get("action_taken") == "auto_answer":
                    ticket.status = TicketStatus.PENDING_CLOSURE

            await db.commit()
            logger.info(f"Agent workflow completed for ticket #{ticket_number}")


        except Exception as e:
            await db.rollback()
            logger.error(f"Agent workflow error for ticket #{ticket_number}: {e}")


# ─── List Tickets ──────────────────────────────────────────────────────────────

@router.get("", response_model=TicketListResponse)
async def list_tickets(
    status: TicketStatus | None = Query(None),
    search: str | None = Query(None, min_length=1, max_length=200),
    priority: str | None = Query(None),
    sort_by: str = Query("created_at", pattern="^(created_at|updated_at|priority|sla_deadline|confidence_score)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
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
        search=search,
        priority=priority,
        sort_by=sort_by,
        sort_order=sort_order,
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


@router.get("/{ticket_id}/messages", response_model=TicketConversationResponse)
async def get_ticket_messages(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket không tồn tại")
    if not auth_service.can_view_ticket(current_user, ticket):
        raise HTTPException(status_code=403, detail="Không có quyền xem ticket này")

    from src.services.ticket_conversation_service import list_messages, seed_agent_opening

    await seed_agent_opening(db, ticket)
    messages = await list_messages(db, ticket_id)
    return TicketConversationResponse(
        items=[TicketMessageResponse.model_validate(item) for item in messages]
    )


@router.post("/{ticket_id}/messages", response_model=TicketConversationResponse)
async def post_ticket_message(
    ticket_id: int,
    payload: TicketMessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket không tồn tại")
    if not auth_service.can_view_ticket(current_user, ticket):
        raise HTTPException(status_code=403, detail="Không có quyền xem ticket này")

    if ticket.status in (
        TicketStatus.CLOSED,
        TicketStatus.RESOLVED,
        TicketStatus.REJECTED,
    ):
        raise HTTPException(
            status_code=400,
            detail="Ticket đã được xử lý hoặc đã đóng. Không thể gửi thêm tin nhắn.",
        )


    from src.services.ticket_conversation_service import handle_ticket_message

    messages = await handle_ticket_message(
        db,
        ticket=ticket,
        user=current_user,
        content=payload.message,
    )
    await db.commit()
    return TicketConversationResponse(
        items=[TicketMessageResponse.model_validate(item) for item in messages]
    )


@router.post("/{ticket_id}/request-technician", response_model=TicketConversationResponse)
async def request_technician(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket không tồn tại")
    if not auth_service.can_view_ticket(current_user, ticket):
        raise HTTPException(status_code=403, detail="Không có quyền xem ticket này")

    from src.services.ticket_conversation_service import escalate_to_technician, list_messages

    await escalate_to_technician(
        db,
        ticket=ticket,
        actor_id=current_user.id,
        reason="Người dùng yêu cầu kỹ thuật viên hỗ trợ trong ticket.",
    )
    messages = await list_messages(db, ticket_id)
    return TicketConversationResponse(
        items=[TicketMessageResponse.model_validate(item) for item in messages]
    )


@router.post("/{ticket_id}/takeover", response_model=TicketResponse)
async def takeover_ticket_api(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Technician / Manager chủ động tiếp nhận xử lý ticket (Takeover)."""
    if current_user.role == UserRole.EMPLOYEE:
        raise HTTPException(status_code=403, detail="Nhân viên không thể tiếp nhận ticket")

    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket không tồn tại")

    if (
        current_user.role in (UserRole.TECHNICIAN, UserRole.MANAGER)
        and current_user.company_unit != CompanyUnit.CORPORATE
        and ticket.submitter
        and ticket.submitter.company_unit != current_user.company_unit
    ):
        raise HTTPException(status_code=403, detail="Không thể tiếp nhận ticket của đơn vị khác")

    updated = await ticket_service.takeover_ticket(
        db=db,
        ticket_id=ticket_id,
        technician_id=current_user.id,
    )
    return TicketResponse.model_validate(updated)



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

    from src.models.ticket import can_transition_ticket
    if not can_transition_ticket(ticket.status, payload.status):
        raise HTTPException(
            status_code=400,
            detail=f"Chuyển trạng thái từ '{ticket.status}' sang '{payload.status}' không hợp lệ theo quy tắc State Machine."
        )

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
    """Người dùng xác nhận giải pháp trong ticket."""
    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket không tồn tại")
    if ticket.submitter_id != current_user.id and current_user.role == UserRole.EMPLOYEE:
        raise HTTPException(status_code=403, detail="Chỉ người tạo ticket mới có quyền xác nhận")

    from src.services.ticket_conversation_service import add_message, escalate_to_technician
    from src.models.ticket_message import TicketMessageSender

    if resolved:
        await ticket_service.close_ticket(
            db=db,
            ticket_id=ticket_id,
            actor_id=current_user.id,
            actor_type="user",
            note="Người dùng xác nhận vấn đề đã được giải quyết.",
        )
        ticket.closed_by = "user"
        await add_message(
            db,
            ticket_id=ticket.id,
            sender_type=TicketMessageSender.SYSTEM,
            sender_id=current_user.id,
            content="✓ Người dùng xác nhận vấn đề đã được giải quyết. Ticket đã được đóng.",
        )
    else:
        await escalate_to_technician(
            db,
            ticket=ticket,
            actor_id=current_user.id,
            reason="Người dùng phản hồi chưa giải quyết được sự cố.",
        )

    await db.refresh(ticket)
    return TicketResponse.model_validate(ticket)


@router.post("/{ticket_id}/close", response_model=TicketResponse)
async def close_ticket_api(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Đóng ticket bởi User hoặc Agent."""
    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket không tồn tại")
    if ticket.submitter_id != current_user.id and current_user.role == UserRole.EMPLOYEE:
        raise HTTPException(status_code=403, detail="Chỉ người tạo ticket mới có quyền đóng")

    from src.services.ticket_conversation_service import add_message
    from src.models.ticket_message import TicketMessageSender

    await ticket_service.close_ticket(
        db=db,
        ticket_id=ticket_id,
        actor_id=current_user.id,
        actor_type="user",
        note=f"Đóng ticket bởi {current_user.full_name}",
    )
    ticket.closed_by = "user" if current_user.role == UserRole.EMPLOYEE else "human_agent"

    await add_message(
        db,
        ticket_id=ticket.id,
        sender_type=TicketMessageSender.SYSTEM,
        sender_id=current_user.id,
        content=f"✓ Ticket đã được đóng bởi {current_user.full_name}.",
    )

    await db.refresh(ticket)
    return TicketResponse.model_validate(ticket)


@router.post("/{ticket_id}/reopen", response_model=TicketResponse)
async def reopen_ticket_api(
    ticket_id: int,
    payload: TicketReopenRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Mở lại ticket đã đóng (bắt buộc nhập lý do)."""
    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket không tồn tại")
    if ticket.submitter_id != current_user.id and current_user.role == UserRole.EMPLOYEE:
        raise HTTPException(status_code=403, detail="Chỉ người tạo ticket mới có quyền mở lại")

    if not payload.reason or not payload.reason.strip():
        raise HTTPException(status_code=400, detail="Vui lòng nhập lý do mở lại ticket")

    from src.models.audit_log import AuditAction
    from src.models.ticket import TicketSupportMode
    from src.services.ticket_conversation_service import add_message
    from src.models.ticket_message import TicketMessageSender
    from datetime import UTC, datetime

    ticket.status = TicketStatus.REOPENED
    if ticket.assignee_id:
        ticket.status = TicketStatus.HUMAN_ACTIVE
        ticket.support_mode = TicketSupportMode.HUMAN
    else:
        ticket.status = TicketStatus.WAITING_FOR_AGENT
        ticket.support_mode = TicketSupportMode.HUMAN

    ticket.reopened_at = datetime.now(UTC)
    await db.flush()

    await add_message(
        db,
        ticket_id=ticket.id,
        sender_type=TicketMessageSender.SYSTEM,
        sender_id=current_user.id,
        content=f'↻ Người dùng đã mở lại ticket.\n\nLý do: "{payload.reason.strip()}"',
    )

    await ticket_service.write_audit_log(
        db=db,
        ticket_id=ticket_id,
        actor_id=current_user.id,
        actor_type="user",
        action=AuditAction.TICKET_REOPENED if hasattr(AuditAction, 'TICKET_REOPENED') else AuditAction.STATUS_CHANGED,
        description=f"Mở lại ticket. Lý do: {payload.reason.strip()}",
    )

    await db.refresh(ticket)
    return TicketResponse.model_validate(ticket)


@router.post("/{ticket_id}/rating", response_model=TicketResponse)
async def submit_ticket_rating(
    ticket_id: int,
    payload: TicketRatingRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Đánh giá chất lượng hỗ trợ ticket (1-5 sao)."""
    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket không tồn tại")
    if ticket.submitter_id != current_user.id and current_user.role == UserRole.EMPLOYEE:
        raise HTTPException(status_code=403, detail="Chỉ người tạo ticket mới có quyền đánh giá")

    ticket.rating = payload.rating
    ticket.rating_feedback = payload.feedback.strip() if payload.feedback else None
    await db.flush()

    from src.models.audit_log import AuditAction
    await ticket_service.write_audit_log(
        db=db,
        ticket_id=ticket_id,
        actor_id=current_user.id,
        actor_type="user",
        action=AuditAction.STATUS_CHANGED,
        description=f"Đánh giá trải nghiệm: {payload.rating}/5 sao. Nhận xét: {payload.feedback or 'Nó'}",
    )

    await db.commit()
    await db.refresh(ticket)
    return TicketResponse.model_validate(ticket)

