"""Interactive AI Chat API — trực tiếp hỗ trợ người dùng bằng RAG + LLM."""
from __future__ import annotations

import logging
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException

from src.api.auth import get_current_active_user
from src.models.user import User
from src.services.rag_service import search_similar
from src.services.llm import get_rag_llm

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["AI Chat"])


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    suggested_solution: str | None = None
    sources: list[str] = []
    confidence: float = 0.90


@router.post("", response_model=ChatResponse)
async def chat_with_agent(
    payload: ChatRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Trò chuyện trực tiếp với Help Desk AI Agent (RAG + LLM)."""
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Nội dung câu hỏi không được để trống")

    # 1. Search RAG
    rag_docs = search_similar(
        message,
        n_results=3,
        user_company_unit=current_user.company_unit.value,
        user_department=current_user.department,
    )

    context_text = "\n\n".join([
        f"--- Tai lieu #{i+1}: {doc['metadata'].get('title', '')} ---\n{doc['content']}"
        for i, doc in enumerate(rag_docs)
    ]) if rag_docs else "Khong tìm thấy tài liệu phù hợp trong Knowledge Base."

    sources = [doc['metadata'].get('title', f"KB #{i+1}") for i, doc in enumerate(rag_docs) if doc['metadata'].get('title')]

    # 2. Query LLM
    llm = get_rag_llm()

    prompt = f"""Bạn là Help Desk AI Agent của Tập đoàn. Hãy trả lời thân thiện, chuyên nghiệp cho nhân viên {current_user.full_name}.

TÀI LIỆU KNOWLEDGE BASE THAM KHẢO:
{context_text}

CÂU HỎI CỦA NHÂN VIÊN:
{message}

YÊU CẦU:
1. Đưa ra câu trả lời trực tiếp, rõ ràng và các bước khắc phục cụ thể (nếu có).
2. Nếu là sự cố phức tạp, khuyên nhân viên tạo ticket để bộ phận IT xử lý.
3. Chỉ dùng tài liệu đã được lọc theo quyền công ty/phòng ban của người dùng; nếu thiếu quyền, hướng dẫn tạo ticket.
"""

    try:
        response = await llm.ainvoke(prompt)
        reply = response.content.strip()
    except Exception as e:
        logger.error(f"LLM Chat Error: {e}")
        reply = "Tôi là Help Desk AI Agent. Dựa trên tri thức hệ thống, bạn nên khởi động lại thiết bị hoặc tạo ticket để bộ phận kỹ thuật hỗ trợ."

    from src.services.ai_logger import log_web_app_ai_event
    log_web_app_ai_event(
        event_name="AIChatCopilot",
        prompt=message,
        response_summary=reply,
        model="mistral-small-latest",
        session_id=f"chat-user-{current_user.id}",
    )

    return ChatResponse(

        reply=reply,
        suggested_solution=rag_docs[0]['metadata'].get('solution') if rag_docs and rag_docs[0]['metadata'].get('solution') else None,
        sources=sources,
        confidence=0.88 if rag_docs else 0.60,
    )
