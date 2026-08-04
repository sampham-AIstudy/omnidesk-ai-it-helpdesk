"""RAG node — Tìm kiếm knowledge base và tổng hợp giải pháp."""
from __future__ import annotations

import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.state import TicketAgentState
from src.services.llm import get_rag_llm
from src.services.rag_service import search_similar

logger = logging.getLogger(__name__)

RAG_SYNTHESIS_PROMPT = """Bạn là chuyên gia IT Support. Dựa trên các tài liệu knowledge base được cung cấp,
hãy đưa ra giải pháp cụ thể và actionable cho ticket IT của nhân viên.

Yêu cầu:
- Trả lời bằng tiếng Việt, rõ ràng và dễ hiểu
- Liệt kê các bước cụ thể (đánh số)
- Nếu cần leo thang hoặc liên hệ team khác, ghi rõ
- Nếu KB không có thông tin phù hợp, thừa nhận và đề xuất hướng xử lý chung
- Nếu có runbook, trích xuất các steps
- Giữ ngắn gọn (tối đa 300 words)"""


async def rag_node(state: TicketAgentState) -> TicketAgentState:
    """RAG node: tìm kiếm KB + tổng hợp giải pháp."""
    logger.info(f"[RAG] Searching KB for ticket #{state.get('ticket_number')}")

    title = state.get("title", "")
    description = state.get("description", "")
    category = state.get("category", "")
    company_unit = state.get("company_unit")
    department = state.get("department")
    query = f"{title}. {description}"

    # Tìm kiếm ChromaDB
    docs = search_similar(
        query=query,
        n_results=5,
        category_filter=category if category != "other" else None,
        user_company_unit=company_unit,
        user_department=department,
    )

    if not docs:
        logger.warning(f"[RAG] No KB docs found for ticket #{state.get('ticket_number')}")
        return {
            **state,
            "rag_context": [],
            "suggested_solution": "Không tìm thấy giải pháp phù hợp trong knowledge base. Vui lòng liên hệ IT Support trực tiếp.",
            "rag_sources": [],
            "runbook_steps": [],
        }

    # Lọc docs có relevance đủ cao
    relevant_docs = [d for d in docs if d.get("relevance_score", 0) > 0.3]
    if not relevant_docs:
        relevant_docs = docs[:2]  # Fallback lấy 2 docs tốt nhất

    # Chuẩn bị context cho LLM
    kb_context = "\n\n".join([
        f"--- Tài liệu {i+1}: {d['metadata'].get('title', 'N/A')} ---\n{d['content']}"
        for i, d in enumerate(relevant_docs[:3])
    ])

    # Trích xuất runbook nếu có
    runbook_steps = []
    for doc in relevant_docs[:2]:
        runbook_raw = doc.get("metadata", {}).get("runbook", "")
        if runbook_raw:
            try:
                rb = json.loads(runbook_raw)
                steps = rb.get("steps", [])
                if steps:
                    runbook_steps = steps
                    break
            except Exception:
                pass

    # LLM synthesis
    llm = get_rag_llm()
    try:
        response = await llm.ainvoke([
            SystemMessage(content=RAG_SYNTHESIS_PROMPT),
            HumanMessage(content=f"""TICKET:
Tiêu đề: {title}
Mô tả: {description}
Category: {category}

KNOWLEDGE BASE CONTEXT:
{kb_context}

Hãy đưa ra giải pháp step-by-step cho ticket này."""),
        ])

        solution = response.content.strip()
        sources = [d.get("metadata", {}).get("title", "KB Entry") for d in relevant_docs[:3]]

        logger.info(f"[RAG] Found {len(relevant_docs)} relevant docs, synthesized solution")

        from src.services.ai_logger import log_web_app_ai_event
        log_web_app_ai_event(
            event_name="RAGAgent",
            prompt=f"Title: {title}\nKB Context Docs: {len(relevant_docs)}",
            response_summary=f"Solution: {solution[:300]}... Sources: {', '.join(sources)}",
            model="mistral-small-latest",
            session_id=str(state.get("ticket_number", "INC-UNK")),
        )

        return {

            **state,
            "rag_context": relevant_docs,
            "suggested_solution": solution,
            "rag_sources": sources,
            "runbook_steps": runbook_steps,
        }

    except Exception as e:
        logger.error(f"[RAG] LLM synthesis error: {e}")
        # Fallback: return best matching KB solution
        fallback_solution = relevant_docs[0]["content"] if relevant_docs else "Liên hệ IT Support."
        return {
            **state,
            "rag_context": relevant_docs,
            "suggested_solution": fallback_solution,
            "rag_sources": [d.get("metadata", {}).get("title", "") for d in relevant_docs[:2]],
            "runbook_steps": runbook_steps,
        }
