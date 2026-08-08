"""Conversation workflow inside a ticket."""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.audit_log import AuditAction
from src.models.ticket import Ticket, TicketStatus
from src.models.ticket_message import TicketMessage, TicketMessageSender
from src.models.user import User, UserRole
from src.services.llm import get_rag_llm
from src.services.rag_service import search_similar
from src.services.ticket_service import write_audit_log

logger = logging.getLogger(__name__)

TICKET_CHAT_PROMPT = """Bạn là AI Trợ Lý IT Help Desk Doanh Nghiệp (Enterprise IT Service Desk Assistant).
Nhiệm vụ của bạn là hỗ trợ cán bộ nhân viên giải quyết các sự cố CNTT (IT Incidents), dịch vụ mạng/VPN, tài khoản Active Directory, hạ tầng và ứng dụng doanh nghiệp (SAP ERP, Email, Office 365).

QUY TẮC PHẢN HỒI:
1. Sử dụng thuật ngữ chuyên ngành IT Help Desk / ITSM chuẩn xác, lịch sự, chuyên nghiệp.
2. Chỉ dựa vào thông tin trong Ticket và ngữ cảnh Knowledge Base (KB) được cung cấp để hướng dẫn từng bước (1., 2., 3.).
3. Nếu không đủ dữ liệu KB hoặc thao tác có rủi ro bảo mật/bảo trì hạ tầng, thông báo rõ ràng: "Sự cố này cần thao tác trực tiếp của Chuyên viên IT Help Desk. Tôi đã mời Chuyên viên IT tham gia vào Ticket này để hỗ trợ trực tiếp."
4. Tuyệt đối không tự động đóng ticket khi chưa được người dùng xác nhận hoàn tất.
5. Phản hồi bằng tiếng Việt chuẩn mực, plain text ngắn gọn, dễ hiểu."""

MIN_AGENT_RELEVANCE = 0.34


async def list_messages(db: AsyncSession, ticket_id: int) -> list[TicketMessage]:
    result = await db.execute(
        select(TicketMessage)
        .where(TicketMessage.ticket_id == ticket_id)
        .order_by(TicketMessage.created_at.asc(), TicketMessage.id.asc())
    )
    return list(result.scalars().all())


async def add_message(
    db: AsyncSession,
    *,
    ticket_id: int,
    sender_type: TicketMessageSender,
    content: str,
    sender_id: int | None = None,
    sources: list[str] | None = None,
    confidence_score: float | None = None,
    routing_hint: str | None = None,
) -> TicketMessage:
    message = TicketMessage(
        ticket_id=ticket_id,
        sender_id=sender_id,
        sender_type=sender_type,
        content=content.strip(),
        sources_json=json.dumps(sources or [], ensure_ascii=False) if sources else None,
        confidence_score=confidence_score,
        routing_hint=routing_hint,
    )
    db.add(message)
    await db.flush()
    await db.refresh(message)
    return message


async def seed_agent_opening(db: AsyncSession, ticket: Ticket) -> None:
    existing = await list_messages(db, ticket.id)
    if existing or not ticket.suggested_solution:
        return

    sources = []
    if ticket.rag_sources:
        try:
            sources = json.loads(ticket.rag_sources)
        except json.JSONDecodeError:
            sources = []

    await add_message(
        db,
        ticket_id=ticket.id,
        sender_type=TicketMessageSender.AGENT,
        content=(
            "Mình đã phân tích ticket và tìm được hướng xử lý ban đầu:\n"
            f"{ticket.suggested_solution}\n\n"
            "Bạn thử các bước trên rồi phản hồi ngay trong ticket này. "
            "Nếu chưa được, mình sẽ chuyển kỹ thuật viên vào cùng cuộc trao đổi."
        ),
        sources=sources,
        confidence_score=ticket.confidence_score,
        routing_hint=ticket.routing_target,
    )


def _format_context(docs: list[dict]) -> tuple[str, list[str]]:
    context_parts = []
    sources = []
    for index, doc in enumerate(docs[:4], start=1):
        metadata = doc.get("metadata", {})
        title = metadata.get("title", f"KB #{index}")
        context_parts.append(f"[S{index}] {title}\n{doc.get('content', '')}")
        if title not in sources:
            sources.append(title)
    return "\n\n".join(context_parts) or "NO_RELEVANT_CONTEXT", sources


async def escalate_to_technician(
    db: AsyncSession,
    *,
    ticket: Ticket,
    actor_id: int | None,
    reason: str,
) -> TicketMessage:
    from src.models.ticket import TicketSupportMode
    ticket.status = TicketStatus.WAITING_FOR_AGENT
    ticket.support_mode = TicketSupportMode.HUMAN
    ticket.sla_escalated = True
    ticket.first_response_at = ticket.first_response_at or datetime.now(UTC)
    await db.flush()

    await write_audit_log(
        db=db,
        ticket_id=ticket.id,
        actor_id=actor_id,
        actor_type="user" if actor_id else "agent",
        action=AuditAction.TICKET_ESCALATED,
        description=f"AI Handoff -> Chờ chuyên viên hỗ trợ. Lý do: {reason}",
    )

    return await add_message(
        db,
        ticket_id=ticket.id,
        sender_type=TicketMessageSender.SYSTEM,
        sender_id=actor_id,
        content=(
            "🤖 AI đã chuyển yêu cầu đến chuyên viên hỗ trợ.\n"
            f"Ticket đang chờ chuyên viên tiếp nhận. (Lý do: {reason})"
        ),
        routing_hint=ticket.routing_target,
    )


async def handle_ticket_message(
    db: AsyncSession,
    *,
    ticket: Ticket,
    user: User,
    content: str,
) -> list[TicketMessage]:
    from src.models.ticket import TicketSupportMode

    # 0. If ticket is already closed/resolved/rejected, do not accept new messages
    if ticket.status in (
        TicketStatus.CLOSED,
        TicketStatus.RESOLVED,
        TicketStatus.REJECTED,
    ):
        return await list_messages(db, ticket.id)

    sender_type = (
        TicketMessageSender.USER
        if user.role == UserRole.EMPLOYEE
        else TicketMessageSender.TECHNICIAN
    )

    # 1. Recording Message
    await add_message(
        db,
        ticket_id=ticket.id,
        sender_type=sender_type,
        sender_id=user.id,
        content=content,
    )

    # 2. Technician Message / Takeover Handling
    if user.role != UserRole.EMPLOYEE:
        first_tech_join = ticket.assignee_id != user.id or ticket.status in (TicketStatus.WAITING_FOR_AGENT, TicketStatus.ESCALATED)
        ticket.assignee_id = user.id
        ticket.status = TicketStatus.HUMAN_ACTIVE
        ticket.support_mode = TicketSupportMode.HUMAN
        await db.flush()

        if first_tech_join:
            await add_message(
                db,
                ticket_id=ticket.id,
                sender_type=TicketMessageSender.SYSTEM,
                sender_id=user.id,
                content=f"👨‍💻 {user.full_name} ({user.department or 'IT Support'}) đã tham gia cuộc trò chuyện.",
            )
            await write_audit_log(
                db=db,
                ticket_id=ticket.id,
                actor_id=user.id,
                actor_type="technician",
                action=AuditAction.TICKET_ASSIGNED,
                description=f"Chuyên viên {user.full_name} đã tham gia cuộc trò chuyện.",
            )

        return await list_messages(db, ticket.id)

    # 3. If ticket is CLOSED, RESOLVED, REJECTED, WAITING_FOR_AGENT, or HUMAN_ACTIVE -> Do NOT let AI auto-respond directly
    if ticket.status in (
        TicketStatus.CLOSED,
        TicketStatus.RESOLVED,
        TicketStatus.REJECTED,
        TicketStatus.WAITING_FOR_AGENT,
        TicketStatus.HUMAN_ACTIVE,
        TicketStatus.ESCALATED,
    ) or ticket.support_mode == TicketSupportMode.HUMAN:
        return await list_messages(db, ticket.id)

    # 4. Check for User Intent: Explicit Human Request or Dissatisfaction
    content_lower = content.lower().strip()
    human_request_keywords = (
        "gặp chuyên viên", "nói chuyện với người thật", "chuyển chuyên viên",
        "gặp nhân viên", "cần người thật", "cần chuyên viên", "yêu cầu chuyên viên",
        "nói chuyện người thật", "gặp con người", "chuyển người thật", "human agent"
    )
    dissatisfaction_keywords = (
        "không đúng", "không giải quyết được", "vẫn bị lỗi", "vẫn lỗi", "chưa được",
        "không hài lòng", "chưa được nữa", "không được", "lỗi vẫn còn", "vẫn chưa được"
    )


    if any(k in content_lower for k in human_request_keywords):
        await escalate_to_technician(
            db,
            ticket=ticket,
            actor_id=user.id,
            reason="Người dùng chủ động yêu cầu gặp chuyên viên hỗ trợ.",
        )
        return await list_messages(db, ticket.id)

    if any(k in content_lower for k in dissatisfaction_keywords):
        await escalate_to_technician(
            db,
            ticket=ticket,
            actor_id=user.id,
            reason="Giải pháp trước chưa xử lý được vấn đề (Người dùng phản hồi chưa thành công).",
        )
        return await list_messages(db, ticket.id)

    # 5. RAG KB Search
    query = f"{ticket.title}. {ticket.description}. {content}"
    docs = search_similar(
        query=query,
        n_results=4,
        category_filter=ticket.category.value if ticket.category else None,
        user_company_unit=ticket.submitter.company_unit.value if ticket.submitter else None,
        user_department=ticket.submitter.department if ticket.submitter else None,
    )
    best_relevance = max((doc.get("relevance_score", 0.0) for doc in docs), default=0.0)

    unsafe_request = any(
        marker in content.casefold()
        for marker in ("bypass", "ne dlp", "mat khau admin", "password admin", "bo qua quy trinh")
    )
    if not docs or best_relevance < MIN_AGENT_RELEVANCE or unsafe_request:
        await escalate_to_technician(
            db,
            ticket=ticket,
            actor_id=user.id,
            reason="Agent không đủ độ tin cậy để tự xử lý." if not unsafe_request else "Yêu cầu có dấu hiệu rủi ro bảo mật.",
        )
        return await list_messages(db, ticket.id)

    # 6. Generate AI Response
    context_text, sources = _format_context(docs)
    llm = get_rag_llm()
    try:
        response = await llm.ainvoke(
            [
                SystemMessage(content=TICKET_CHAT_PROMPT),
                HumanMessage(
                    content=(
                        f"TICKET: {ticket.title}\n"
                        f"MO TA: {ticket.description}\n"
                        f"TRANG THAI: {ticket.status.value}\n"
                        f"NGUOI DUNG VUA NHAN: {content}\n\n"
                        f"KNOWLEDGE BASE CONTEXT:\n{context_text}"
                    )
                ),
            ]
        )
        answer = response.content.strip()
    except Exception as exc:
        logger.warning("Ticket chat LLM failed for ticket %s: %s", ticket.id, exc)
        answer = (
            "Mình chưa gọi được mô hình trả lời lúc này. "
            "Dựa trên gợi ý đã có trong ticket, bạn thử các bước KB trước; nếu chưa được hãy bấm Cần kỹ thuật viên."
        )

    ticket.first_response_at = ticket.first_response_at or datetime.now(UTC)
    if ticket.status == TicketStatus.OPEN:
        ticket.status = TicketStatus.IN_PROGRESS
    await add_message(
        db,
        ticket_id=ticket.id,
        sender_type=TicketMessageSender.AGENT,
        content=answer,
        sources=sources,
        confidence_score=best_relevance,
        routing_hint=ticket.routing_target,
    )
    await db.flush()
    return await list_messages(db, ticket.id)

