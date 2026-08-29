"""Tickets API — CRUD + agent workflow trigger + HITL decisions."""
from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse

from src.api.auth import get_current_active_user
from src.database import get_db
from src.guardrails.ai_abuse_guard import validate_chat_message_size
from src.models.audit_log import AuditAction
from src.models.schemas import (
    AgentProcessResponse,
    DuplicateActionRequest,
    DuplicateCheckRequest,
    DuplicateCheckResponse,
    DuplicateTicketCandidate,
    HITLDecisionRequest,
    TicketConversationResponse,
    TicketCreate,
    TicketEscalateRequest,
    TicketListResponse,
    TicketMessageCreate,
    TicketMessageResponse,
    TicketPinRequest,
    TicketRatingRequest,
    TicketReopenRequest,
    TicketResponse,
    TicketStatusUpdate,
)
from src.models.ticket import Ticket, TicketPriority, TicketStatus
from src.models.user import CompanyUnit, User, UserRole
from src.observability.tracing import record_business_event
from src.services import auth_service, ticket_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tickets", tags=["Tickets"])


_IDEMPOTENCY_CACHE_LIMIT = 1_000
_idempotency_store: dict[tuple[int, str], AgentProcessResponse] = {}


def _duplicate_response(check) -> DuplicateCheckResponse:
    primary = check.primary
    requires_confirmation = bool(primary and primary.classification in {"EXACT_DUPLICATE", "SEMANTIC_DUPLICATE"} and (primary.is_active or primary.is_resolved))
    if primary and primary.is_resolved:
        message = "Có vẻ vấn đề này đã được xử lý trong một yêu cầu trước. Bạn có thể xem giải pháp hoặc vẫn tạo ticket mới."
    elif primary and primary.is_active:
        message = "Bạn đã có một yêu cầu tương tự đang được xử lý. Bạn có thể mở ticket hiện tại để bổ sung thông tin."
    elif check.matches:
        message = "Chúng tôi tìm thấy một số yêu cầu có thể liên quan."
    else:
        message = None
    return DuplicateCheckResponse(
        classification=primary.classification if primary else "NOT_DUPLICATE",
        requires_confirmation=requires_confirmation,
        message=message,
        same_user_repeat_count=check.same_user_repeat_count,
        shared_incident_signal=check.shared_incident_signal,
        matches=[DuplicateTicketCandidate(
            ticket_id=match.ticket.id, ticket_number=match.ticket.ticket_number, title=match.ticket.title,
            status=match.ticket.status, resolved_at=getattr(match.ticket, "resolved_at", None) or getattr(match.ticket, "closed_at", None),
            solution=match.solution, classification=match.classification, score=round(match.score, 4),
            detection_method=match.method, is_active=match.is_active, is_resolved=match.is_resolved,
        ) for match in check.matches],
    )


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
    if x_idempotency_key and len(x_idempotency_key) > 128:
        raise HTTPException(status_code=400, detail="Idempotency key is too long")

    idempotency_key = (current_user.id, x_idempotency_key) if x_idempotency_key else None
    if idempotency_key and idempotency_key in _idempotency_store:
        logger.info(f"Idempotency Key hit: {x_idempotency_key}")
        return _idempotency_store[idempotency_key]

    # Guardrail is intentionally before duplicate retrieval and all expensive AI work.
    from src.guardrails.input_guardrails import InputGuardrailPlugin
    guard_result = InputGuardrailPlugin().on_user_message_callback(f"{payload.title}\n{payload.description}")
    if guard_result.get("decision") == "BLOCK":
        raise HTTPException(status_code=400, detail=guard_result.get("safe_response", "Nội dung ticket không đạt yêu cầu an toàn."))

    # A short per-user limit absorbs accidental re-clicks/repeated submissions;
    # it never closes or discards a ticket and the caller can retry after the window.
    from src.assignment.rate_limiter import is_rate_limited
    rate_result = is_rate_limited(f"ticket-create:{current_user.id}")
    if not rate_result["allowed"]:
        raise HTTPException(status_code=429, detail="Bạn đang gửi yêu cầu quá nhanh. Vui lòng thử lại sau ít phút hoặc cập nhật ticket đang mở.")

    from src.services.duplicate_detection_service import (
        audit_duplicate_decision,
        check_duplicate_tickets,
        index_ticket_for_duplicate_detection,
    )
    check = await check_duplicate_tickets(db, payload.title, payload.description, current_user)
    duplicate_response = _duplicate_response(check)
    await audit_duplicate_decision(db, check, current_user)

    # Similar-ticket lookup is advisory only.  A user should always be able to
    # submit the incident; the linked context is surfaced by the AI inside the
    # created ticket, where they can assess it without interrupting the form.
    related_match = check.primary if duplicate_response.requires_confirmation else None

    ticket = await ticket_service.create_ticket(
        db=db,
        title=payload.title,
        description=payload.description,
        submitter_id=current_user.id,
        is_production_impact=payload.is_production_impact,
        duplicate_of_ticket_id=related_match.ticket.id if related_match else None,
        duplicate_score=related_match.score if related_match else None,
        duplicate_detection_method=related_match.method if related_match else None,
        duplicate_confirmed_by=None,
    )
    await db.commit()
    record_business_event("ticket.created")

    # Index before enqueueing the workflow so rapid re-submits are caught without an LLM call.
    try:
        import asyncio
        await asyncio.to_thread(index_ticket_for_duplicate_detection, ticket, current_user)
    except Exception as exc:
        logger.warning("Could not index ticket %s for duplicate detection: %s", ticket.id, exc)
    try:
        from src.services.zero_mem_service import index_ticket_trace
        await index_ticket_trace(db, ticket, current_user)
        await db.commit()
    except Exception as exc:
        logger.warning("Could not index ticket %s for episodic memory: %s", ticket.id, exc)

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

    if idempotency_key:
        if len(_idempotency_store) >= _IDEMPOTENCY_CACHE_LIMIT:
            _idempotency_store.pop(next(iter(_idempotency_store)))
        _idempotency_store[idempotency_key] = response_data

    return response_data


@router.post("/duplicate-check", response_model=DuplicateCheckResponse)
async def duplicate_check(
    payload: DuplicateCheckRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Preview tenant-scoped duplicate suggestions; no ticket is created by this endpoint."""
    from src.services.duplicate_detection_service import audit_duplicate_decision, check_duplicate_tickets
    check = await check_duplicate_tickets(db, payload.title, payload.description, current_user)
    await audit_duplicate_decision(db, check, current_user)
    return _duplicate_response(check)


@router.post("/duplicate-action")
async def duplicate_action(
    payload: DuplicateActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Record that an existing solution helped, or an optional false-positive label for metrics."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from src.models.ticket import Ticket
    from src.services.ticket_service import write_audit_log

    result = await db.execute(select(Ticket).options(selectinload(Ticket.submitter)).where(Ticket.id == payload.matched_ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket or ticket.submitter.company_unit != current_user.company_unit or (ticket.submitter.department or "") != (current_user.department or ""):
        raise HTTPException(status_code=404, detail="Không tìm thấy ticket trong phạm vi truy cập của bạn")
    action = AuditAction.DUPLICATE_PREVENTED if payload.action == "resolved_existing" else AuditAction.DUPLICATE_FALSE_POSITIVE
    await write_audit_log(
        db=db, ticket_id=ticket.id, actor_id=current_user.id, actor_type="user", action=action,
        description="User selected existing duplicate ticket outcome",
        metadata={"matched_ticket_id": ticket.id, "outcome": payload.action},
    )
    return {"ok": True}


@router.get("/duplicate-metrics")
async def get_duplicate_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role not in {UserRole.MANAGER, UserRole.ADMIN}:
        raise HTTPException(status_code=403, detail="Chỉ quản lý hoặc admin có thể xem duplicate metrics")
    from src.services.duplicate_detection_service import duplicate_metrics
    return await duplicate_metrics(db)


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
                record_business_event("guardrail.block")
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
                    record_business_event("ticket.handoff")
                    ticket.status = TicketStatus.PENDING_HITL
                    # Create Action-Level HITL Approval Record
                    from src.models.hitl_approval import HITLApproval
                    hitl_record = HITLApproval(
                        ticket_id=ticket_id,
                        approval_type="manager_approval",
                        reason=f"[HIGH_RISK] {final_state.get('hitl_reason', 'Policy Engine Decision')} | Risk Score: {final_state.get('risk_score', 0.70)}",
                    )
                    db.add(hitl_record)
                elif final_state.get("action_taken") == "ask_clarification":
                    ticket.status = TicketStatus.NEEDS_CLARIFICATION
                elif final_state.get("action_taken") == "human_handoff":
                    record_business_event("ticket.handoff")
                    from src.services.ticket_conversation_service import escalate_to_technician
                    await escalate_to_technician(
                        db,
                        ticket=ticket,
                        actor_id=None,
                        reason="AI không có hướng dẫn Knowledge Base đủ phù hợp để xử lý an toàn.",
                    )
                elif final_state.get("target_status") == "resolved":
                    record_business_event("ticket.auto_resolve")
                    ticket.status = TicketStatus.RESOLVED
                    ticket.closed_by = "ai_auto_close"

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
    priority: TicketPriority | None = Query(None),
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
    """[DEPRECATED] HITL workflow đã bị bỏ (Manager role đã xóa).
    Ticket rủi ro cao giờ được route thẳng đến KTV, không còn nằm ở pending_hitl.
    Endpoint giữ lại để backward compat, luôn trả về danh sách rỗng.
    """
    return []


@router.get("/resolve/{ticket_number}", response_model=TicketResponse)
async def resolve_ticket_reference(
    ticket_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Resolve a display ticket number without bypassing ticket ACLs."""
    normalized = ticket_number.strip().upper()
    if not normalized or len(normalized) > 80:
        raise HTTPException(status_code=404, detail="Ticket not found")
    ticket = (
        await db.execute(select(Ticket).where(Ticket.ticket_number == normalized))
    ).scalar_one_or_none()
    if not ticket or not auth_service.can_view_ticket(current_user, ticket):
        # Do not leak the existence of a ticket outside the caller scope.
        raise HTTPException(status_code=404, detail="Ticket not found")
    return TicketResponse.model_validate(ticket)


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
    is_staff = current_user.role in (UserRole.TECHNICIAN, UserRole.MANAGER, UserRole.ADMIN)
    messages = await list_messages(db, ticket_id, include_internal=is_staff)
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
    validate_chat_message_size(payload.message)
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

    # Internal technical notes: Staff only
    if payload.is_internal:
        if payload.corrects_answer_message_id is not None:
            raise HTTPException(status_code=422, detail="An internal note cannot be a preference correction")
        if current_user.role == UserRole.EMPLOYEE:
            raise HTTPException(status_code=403, detail="Nhân viên không có quyền tạo ghi chú nội bộ")

        from src.models.ticket_message import TicketMessageSender
        from src.services.ticket_conversation_service import add_message, list_messages

        sender_type = (
            TicketMessageSender.MANAGER
            if current_user.role == UserRole.MANAGER
            else TicketMessageSender.TECHNICIAN
        )
        await add_message(
            db,
            ticket_id=ticket.id,
            sender_type=sender_type,
            sender_id=current_user.id,
            content=payload.message,
            is_internal=True,
            index_for_memory=False,
        )
        await db.commit()
        messages = await list_messages(db, ticket_id, include_internal=True)
        return TicketConversationResponse(
            items=[TicketMessageResponse.model_validate(item) for item in messages]
        )

    if current_user.role == UserRole.TECHNICIAN and ticket.assignee_id != current_user.id:
        raise HTTPException(
            status_code=409,
            detail="Bạn cần tiếp nhận ticket trước khi gửi phản hồi cho người dùng.",
        )

    if payload.corrects_answer_message_id is not None:
        if current_user.role == UserRole.EMPLOYEE:
            raise HTTPException(status_code=403, detail="Only staff may submit an explicit correction")
        from src.services.feedback_dataset_service import validate_answer_provenance

        try:
            await validate_answer_provenance(
                db,
                tenant_id=str(getattr(ticket.submitter.company_unit, "value", ticket.submitter.company_unit)),
                ticket_id=ticket.id,
                answer_message_id=str(payload.corrects_answer_message_id),
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Invalid correction answer_message_id for this ticket") from exc

    from src.services.ticket_conversation_service import handle_ticket_message, list_messages

    correction_kwargs = (
        {"corrects_answer_message_id": str(payload.corrects_answer_message_id)}
        if payload.corrects_answer_message_id
        else {}
    )
    messages = await handle_ticket_message(
        db,
        ticket=ticket,
        user=current_user,
        content=payload.message,
        **correction_kwargs,
    )
    await db.commit()
    is_staff = current_user.role in (UserRole.TECHNICIAN, UserRole.MANAGER, UserRole.ADMIN)
    messages = await list_messages(db, ticket_id, include_internal=is_staff)
    return TicketConversationResponse(
        items=[TicketMessageResponse.model_validate(item) for item in messages]
    )


@router.post("/{ticket_id}/messages/stream")
async def stream_ticket_message(
    ticket_id: int,
    payload: TicketMessageCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Stream token output for the ticket conversation, then persist the final message once."""
    validate_chat_message_size(payload.message)
    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket không tồn tại")
    if not auth_service.can_view_ticket(current_user, ticket):
        raise HTTPException(status_code=403, detail="Không có quyền xem ticket này")
    if current_user.role != UserRole.EMPLOYEE and ticket.assignee_id != current_user.id:
        raise HTTPException(
            status_code=409,
            detail="You must take ownership of the ticket before replying.",
        )

    if ticket.status in {TicketStatus.CLOSED, TicketStatus.RESOLVED, TicketStatus.REJECTED}:
        raise HTTPException(status_code=400, detail="Ticket đã được xử lý hoặc đã đóng. Không thể gửi thêm tin nhắn.")

    if payload.is_internal:
        raise HTTPException(status_code=422, detail="Internal notes must use the non-streaming message endpoint")
    if payload.corrects_answer_message_id is not None:
        if current_user.role == UserRole.EMPLOYEE:
            raise HTTPException(status_code=403, detail="Only staff may submit an explicit correction")
        from src.services.feedback_dataset_service import validate_answer_provenance

        try:
            await validate_answer_provenance(
                db,
                tenant_id=str(getattr(ticket.submitter.company_unit, "value", ticket.submitter.company_unit)),
                ticket_id=ticket.id,
                answer_message_id=str(payload.corrects_answer_message_id),
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Invalid correction answer_message_id for this ticket") from exc

    from src.services.ticket_conversation_service import handle_ticket_message

    async def events():
        queue: asyncio.Queue[str] = asyncio.Queue()

        async def on_token(text: str) -> None:
            await queue.put(text)

        correction_kwargs = (
            {"corrects_answer_message_id": str(payload.corrects_answer_message_id)}
            if payload.corrects_answer_message_id
            else {}
        )
        task = asyncio.create_task(handle_ticket_message(
            db,
            ticket=ticket,
            user=current_user,
            content=payload.message,
            on_token=on_token,
            **correction_kwargs,
        ))
        try:
            while not task.done() or not queue.empty():
                if await request.is_disconnected():
                    task.cancel()
                    return
                try:
                    token = await asyncio.wait_for(queue.get(), timeout=0.15)
                    yield f"event: token\ndata: {json.dumps({'text': token}, ensure_ascii=False)}\n\n"
                except TimeoutError:
                    continue
            messages = await task
            await db.commit()
            yield f"event: done\ndata: {json.dumps(TicketConversationResponse(items=[TicketMessageResponse.model_validate(item) for item in messages]).model_dump(mode='json'), ensure_ascii=False)}\n\n"
        except Exception as exc:
            logger.exception("Ticket message streaming failed: %s", exc)
            yield f"event: error\ndata: {json.dumps({'message': 'Không thể tạo phản hồi streaming.'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


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


_join_locks: dict[int, asyncio.Lock] = {}
_join_locks_guard = asyncio.Lock()


@router.post("/{ticket_id}/join", response_model=TicketConversationResponse)
async def join_ticket_conversation(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Manager / Admin tham gia chỉ đạo cuộc trao đổi (Step-In / Supervisor Join)."""
    if current_user.role not in (UserRole.MANAGER, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Chỉ Quản lý hoặc Admin mới có quyền tham gia chỉ đạo sự cố")

    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket không tồn tại")

    if not auth_service.can_view_ticket(current_user, ticket):
        raise HTTPException(status_code=403, detail="Không có quyền truy cập sự cố này")

    if ticket.status in (TicketStatus.CLOSED, TicketStatus.RESOLVED, TicketStatus.REJECTED):
        raise HTTPException(status_code=400, detail="Không thể tham gia sự cố đã kết thúc")

    from src.models.ticket import TicketSupportMode
    from src.models.ticket_message import TicketMessage, TicketMessageSender
    from src.services.ticket_conversation_service import add_message, list_messages

    ticket.support_mode = TicketSupportMode.HUMAN
    await db.flush()

    # Acquire per-ticket lock to guarantee atomicity during concurrent joins
    async with _join_locks_guard:
        if ticket_id not in _join_locks:
            _join_locks[ticket_id] = asyncio.Lock()
        ticket_lock = _join_locks[ticket_id]

    async with ticket_lock:
        # Query for existing join announcement for this manager on this ticket
        existing_join_res = await db.execute(
            select(TicketMessage).where(
                TicketMessage.ticket_id == ticket_id,
                TicketMessage.sender_type == TicketMessageSender.SYSTEM,
                TicketMessage.sender_id == current_user.id,
                (TicketMessage.routing_hint == "manager_joined") | (TicketMessage.content.contains("tham gia"))
            ).limit(1)
        )
        already_announced = existing_join_res.scalars().first() is not None

        if not already_announced:
            await add_message(
                db,
                ticket_id=ticket_id,
                sender_type=TicketMessageSender.SYSTEM,
                sender_id=current_user.id,
                routing_hint="manager_joined",
                content=f"👔 **[QUẢN LÝ THAM GIA]** {current_user.full_name} ({current_user.department or 'Quản lý IT'}) đã tham gia vào cuộc trao đổi để chỉ đạo và hỗ trợ xử lý sự cố.",
            )
            await ticket_service.write_audit_log(
                db=db,
                ticket_id=ticket_id,
                actor_id=current_user.id,
                actor_type="manager",
                action=AuditAction.STATUS_CHANGED,
                description=f"Quản lý {current_user.full_name} tham gia chỉ đạo cuộc trao đổi sự cố.",
                metadata={"action_type": "manager_joined", "manager_id": current_user.id},
            )
            await db.flush()

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


@router.post("/{ticket_id}/escalate", response_model=TicketResponse)
async def escalate_ticket_api(
    ticket_id: int,
    payload: TicketEscalateRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Technician / Manager leo thang sự cố lên cấp cao hơn (kèm tùy chọn nâng ưu tiên khẩn cấp)."""
    if current_user.role == UserRole.EMPLOYEE:
        raise HTTPException(status_code=403, detail="Nhân viên không có quyền leo thang sự cố")

    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket không tồn tại")

    if not auth_service.can_view_ticket(current_user, ticket):
        raise HTTPException(status_code=403, detail="Không có quyền truy cập sự cố này")

    reason = payload.reason if payload and payload.reason else "Chuyên viên kỹ thuật yêu cầu leo thang xử lý lên cấp Quản lý."
    escalate_to = payload.escalate_to if payload and payload.escalate_to else "manager"
    bump_priority = payload.bump_priority if payload else False
    handover_notes = payload.handover_notes if payload else None

    try:
        updated = await ticket_service.escalate_ticket(
            db=db,
            ticket_id=ticket_id,
            reason=reason,
            actor=current_user,
            escalate_to=escalate_to,
            bump_priority=bump_priority,
            handover_notes=handover_notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return TicketResponse.model_validate(updated)


@router.post("/{ticket_id}/pin", response_model=TicketResponse)
async def pin_ticket_api(
    ticket_id: int,
    payload: TicketPinRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Ghim hoặc bỏ ghim sự cố lên đầu hàng đợi ưu tiên (Expedite / Fast-Track)."""
    if current_user.role == UserRole.EMPLOYEE:
        raise HTTPException(status_code=403, detail="Nhân viên không có quyền ghim sự cố")

    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket không tồn tại")

    if not auth_service.can_view_ticket(current_user, ticket):
        raise HTTPException(status_code=403, detail="Không có quyền truy cập sự cố này")

    pinned = payload.pinned if payload is not None else True
    reason = payload.reason if payload else None

    try:
        updated = await ticket_service.set_ticket_pinned(
            db=db,
            ticket_id=ticket_id,
            pinned=pinned,
            actor=current_user,
            reason=reason,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return TicketResponse.model_validate(updated)


# ─── HITL Decision ─────────────────────────────────────────────────────────────

@router.get("/pending-hitl", response_model=list[TicketResponse])
async def get_pending_hitl_tickets():
    """[Deprecated] HITL đã bị loại bỏ, endpoint này luôn trả về danh sách rỗng."""
    logger.warning("Endpoint /pending-hitl is deprecated and will be removed.")
    return []


@router.post("/{ticket_id}/approve", response_model=TicketResponse)
async def approve_ticket(
    ticket_id: int,
    payload: HITLDecisionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """[Backward compat] Xác nhận quyết định HITL cho ticket pending_hitl cũ trong DB.
    Không còn được tạo mới bởi workflow (HITL đã bỏ), chỉ dùng để giải quyết
    các ticket pending_hitl còn tồn đọng trong DB từ trước khi nâng cấp.
    Quyền: Technician hoặc Admin.
    """
    if not auth_service.can_approve_hitl(current_user):
        raise HTTPException(status_code=403, detail="Chỉ Technician hoặc Admin mới xác nhận được")

    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket không tồn tại")
    if not auth_service.can_view_ticket(current_user, ticket):
        raise HTTPException(status_code=403, detail="Không có quyền phê duyệt ticket này")
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

    from src.models.ticket_message import TicketMessageSender
    from src.services.ticket_conversation_service import add_message, escalate_to_technician

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
    """Đóng ticket bởi người tạo hoặc nhân sự hỗ trợ."""
    ticket = await ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket không tồn tại")
    if ticket.submitter_id != current_user.id and current_user.role == UserRole.EMPLOYEE:
        raise HTTPException(status_code=403, detail="Chỉ người tạo ticket mới có quyền đóng")

    from src.models.ticket_message import TicketMessageSender
    from src.services.ticket_conversation_service import add_message

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

    feedback_tenant = str(getattr(ticket.submitter.company_unit, "value", ticket.submitter.company_unit))
    if payload.answer_message_id is not None:
        from src.services.feedback_dataset_service import validate_answer_provenance

        try:
            await validate_answer_provenance(
                db,
                tenant_id=feedback_tenant,
                ticket_id=ticket.id,
                answer_message_id=str(payload.answer_message_id),
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Invalid answer_message_id for this ticket") from exc

    from datetime import UTC, datetime

    from src.models.audit_log import AuditAction
    from src.models.ticket import TicketSupportMode
    from src.models.ticket_message import TicketMessageSender
    from src.services.ticket_conversation_service import add_message

    ticket.status = TicketStatus.REOPENED
    if ticket.assignee_id:
        ticket.status = TicketStatus.HUMAN_ACTIVE
        ticket.support_mode = TicketSupportMode.HUMAN
    else:
        ticket.status = TicketStatus.WAITING_FOR_AGENT
        ticket.support_mode = TicketSupportMode.HUMAN

    ticket.reopened_at = datetime.now(UTC)
    await db.flush()

    from src.services.feedback_dataset_service import record_ticket_outcome_event
    await record_ticket_outcome_event(
        db,
        tenant_id=feedback_tenant,
        ticket_id=ticket.id,
        outcome="reopened",
        actor_role="user",
        answer_message_id=str(payload.answer_message_id) if payload.answer_message_id else None,
        reason=payload.reason,
    )

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

    feedback_tenant = str(getattr(ticket.submitter.company_unit, "value", ticket.submitter.company_unit))
    if payload.answer_message_id is not None:
        from src.services.feedback_dataset_service import validate_answer_provenance

        try:
            await validate_answer_provenance(
                db,
                tenant_id=feedback_tenant,
                ticket_id=ticket.id,
                answer_message_id=str(payload.answer_message_id),
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Invalid answer_message_id for this ticket") from exc

    ticket.rating = payload.rating
    ticket.rating_feedback = payload.feedback.strip() if payload.feedback else None
    await db.flush()

    from src.services.feedback_dataset_service import record_ticket_rating_event
    await record_ticket_rating_event(
        db,
        tenant_id=feedback_tenant,
        ticket_id=ticket.id,
        rating=payload.rating,
        comment=payload.feedback,
        actor_role=current_user.role.value,
        answer_message_id=str(payload.answer_message_id) if payload.answer_message_id else None,
    )

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
