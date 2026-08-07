"""RAG node — Tìm kiếm knowledge base và tổng hợp giải pháp."""
from __future__ import annotations

import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.state import TicketAgentState
from src.services.llm import get_rag_llm
from src.services.rag_service import search_similar_async

logger = logging.getLogger(__name__)

RAG_SYNTHESIS_PROMPT = """Bạn là chuyên gia IT Support. Dựa trên các tài liệu knowledge base được cung cấp,
hãy đưa ra giải pháp cụ thể và actionable cho ticket IT của nhân viên.

Yêu cầu:
- Trả lời bằng tiếng Việt, rõ ràng và dễ hiểu
- Liệt kê các bước cụ thể (đánh số: 1. 2. 3.)
- Nếu cần leo thang hoặc liên hệ team khác, ghi rõ
- Nếu KB không có thông tin phù hợp, thừa nhận và đề xuất hướng xử lý chung
- Nếu có runbook, trích xuất các steps
- Chỉ dùng thông tin có trong context; không tự tạo lệnh, URL hoặc chính sách nội bộ
- Khi context có SOURCE_URL, thêm mục "Nguon tham khao" ở cuối câu trả lời
- Giữ ngắn gọn (tối đa 300 words)
- QUAN TRỌNG: Không dùng Markdown formatting. Không dùng **, *, #, ---, backtick hay bất kỳ ký hiệu định dạng nào. Chỉ viết văn bản thuần túy."""
RAG_SYNTHESIS_PROMPT_V2 = """Ban la chuyen gia IT Support. Dua tren knowledge base context duoc cung cap,
hay dua ra giai phap cu the va actionable cho ticket IT cua nhan vien.

Yeu cau:
- Tra loi bang tieng Viet, ro rang va de hieu
- Liet ke cac buoc cu the bang so thu tu 1. 2. 3.
- Chi dung thong tin co trong context; khong tu tao lenh, URL, mat khau, workaround bao mat, hoac chinh sach noi bo
- Neu context khong du thong tin, noi ro Knowledge Base khong co thong tin phu hop va de xuat tao ticket hoac leo thang IT Support
- Neu nguoi dung yeu cau bo qua quy trinh, bypass bao mat, tiet lo bi mat, hoac gian lan, tu choi phan do va huong ve quy trinh an toan
- Neu can approval hoac lien he team khac, ghi ro dieu kien approval/team can leo thang
- Neu co runbook, trich xuat cac steps co trong context
- Khi dung tai lieu nao, them muc "Nguon tham khao" o cuoi cau tra loi voi title/SOURCE_URL tu context
- Giu ngan gon toi da 300 words
- QUAN TRONG: Khong dung Markdown formatting. Khong dung **, *, #, ---, backtick hay ky hieu dinh dang. Chi viet van ban thuan tuy."""


async def rag_node(state: TicketAgentState) -> TicketAgentState:
    """RAG node: tìm kiếm KB + tổng hợp giải pháp."""
    logger.info(f"[RAG] Searching KB for ticket #{state.get('ticket_number')}")

    title = state.get("title", "")
    description = state.get("description", "")
    category = state.get("category", "")
    company_unit = state.get("company_unit")
    department = state.get("department")
    query = f"{title}. {description}"

    # Tìm kiếm ChromaDB (Non-blocking async)
    docs = await search_similar_async(
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
    context_parts = []
    for i, doc in enumerate(relevant_docs[:3]):
        metadata = doc.get("metadata", {})
        source_url = metadata.get("source_url", "")
        source_line = f"\nSOURCE_URL: {source_url}" if source_url else ""
        context_parts.append(
            f"--- Tài liệu {i + 1}: {metadata.get('title', 'N/A')} ---"
            f"{source_line}\n{doc['content']}"
        )
    kb_context = "\n\n".join(context_parts)

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
            SystemMessage(content=RAG_SYNTHESIS_PROMPT_V2),
            HumanMessage(content=f"""TICKET:
Tiêu đề: {title}
Mô tả: {description}
Category: {category}

KNOWLEDGE BASE CONTEXT:
{kb_context}

Hãy đưa ra giải pháp step-by-step cho ticket này."""),
        ])

        solution = response.content.strip()
        sources = []
        for doc in relevant_docs[:3]:
            metadata = doc.get("metadata", {})
            title_or_default = metadata.get("title", "KB Entry")
            source_url = metadata.get("source_url")
            source_label = f"{title_or_default} — {source_url}" if source_url else title_or_default
            if source_label not in sources:
                sources.append(source_label)

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
