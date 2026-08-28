"""RAG node — Tìm kiếm knowledge base và tổng hợp giải pháp."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.state import TicketAgentState
from src.config import get_settings
from src.observability.tracing import set_current_attributes, traced_async_operation
from src.prompts import (
    PRODUCTION_RAG_SYSTEM_PROMPT,
    build_authorized_evidence,
    evidence_source_ids,
    remove_unrecognized_source_ids,
)
from src.services.llm import get_rag_llm
from src.services.rag_confidence_service import extract_consensus_score, extract_retrieval_score
from src.services.rag_service import get_collection, search_similar
from src.services.source_provenance_service import knowledge_source_payload
from src.services.ticket_text import user_report
from src.services.token_cost import dispatch_token_logging
from src.services.web_research_service import has_actionable_external_context, maybe_research_web

logger = logging.getLogger(__name__)
settings = get_settings()

INSUFFICIENT_KB_MARKERS = (
    "knowledge base chưa có",
    "knowledge base không có",
    "không tìm thấy giải pháp phù hợp",
    "không có thông tin phù hợp trong knowledge base",
)

# Public research is only considered evidence after the system tool returns it.
# The same production grounding policy applies to this narrower path as well.
EXTERNAL_RESEARCH_PROMPT = PRODUCTION_RAG_SYSTEM_PROMPT


def _safe_initial_triage(title: str, description: str) -> str:
    """Return answerability-aware fallback without undocumented troubleshooting."""
    report = f"{title} {description}".casefold()
    incident_markers = (
        "laptop", "máy tính", "màn hình", "bàn phím", "máy in", "rơi",
        "đấm", "va đập", "nhấp nháy", "tự tắt", "tiếng lạ", "không lên",
    )
    if any(marker in report for marker in incident_markers):
        return (
            "Mình đã nhận diện đây là một sự cố cần xử lý, nhưng Knowledge Base hiện chưa đủ "
            "để xác định nguyên nhân kỹ thuật hoặc đưa ra bước khắc phục cụ thể. "
            "Bạn không cần nhắc lại các chi tiết đã mô tả. Nếu có thể, hãy bổ sung model/nhãn tài sản "
            "và cho biết thiết bị còn hoạt động hay không để kỹ thuật viên kiểm tra tiếp."
        )
    return "Rất tiếc, thông tin hiện có chưa đủ để trả lời câu hỏi này."


def _web_source_payload(source) -> dict[str, str]:
    return {
        "label": source.title,
        "kind": "web",
        "url": source.url,
    }


async def _research_or_safe_triage(title: str, description: str, docs: list[dict]) -> tuple[str, list[dict[str, str]]]:
    """Use public research only for a specific product/error; otherwise ask safely."""
    query = f"{title}. {description}".strip()
    fallback = _safe_initial_triage(title, description)
    if not has_actionable_external_context(query):
        return fallback, []

    research = await maybe_research_web(query, docs)
    if not research.triggered or not research.sources:
        return fallback, []

    context = "\n\n".join(
        f"[Nguồn web {index}] {source.title}\nURL: {source.url}\n{source.content[:2500]}"
        for index, source in enumerate(research.sources, start=1)
    )
    try:
        response = await get_rag_llm().ainvoke([
            SystemMessage(content=EXTERNAL_RESEARCH_PROMPT),
            HumanMessage(content=(
                f"[AUTHORIZED_EVIDENCE]\n{context}\n\n"
                f"[USER QUESTION]\n{query}"
            )),
        ])
        answer = str(response.content).strip()
        # Theo dõi token cho lần tổng hợp external research (không có user_id ở đây)
        _rag_llm = get_rag_llm()
        dispatch_token_logging(
            ai_message=response,
            model_name=str(getattr(_rag_llm, "model_name", getattr(_rag_llm, "model", "mistral-small-latest"))),
            user_id=None,
        )
        answer, _ = remove_unrecognized_source_ids(answer, set())
        if answer:
            return answer, [_web_source_payload(source) for source in research.sources]
    except Exception as exc:
        logger.info("External research synthesis unavailable for ticket triage: %s", exc)
    return fallback, []

RAG_SYNTHESIS_PROMPT = """Bạn là chuyên gia IT Support. Dựa trên các tài liệu knowledge base được cung cấp,
hãy đưa ra giải pháp cụ thể và actionable cho ticket IT của nhân viên.

Yêu cầu:
- Trả lời bằng tiếng Việt, rõ ràng và dễ hiểu
- Liệt kê các bước cụ thể (đánh số: 1. 2. 3.)
- Nếu tài liệu nói về sản phẩm khác với ticket (ví dụ Outlook trong khi ticket nói Gmail), không được áp dụng lẫn các bước. Hãy nói rõ KB không có bài khớp trực tiếp.
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
- Neu tai lieu noi ve san pham khac voi ticket (vi du Outlook trong khi ticket noi Gmail), khong ap dung lan cac buoc. Hay noi ro KB khong co bai khop truc tiep.
- Neu context khong du thong tin, noi ro Knowledge Base khong co thong tin phu hop va de xuat tao ticket hoac leo thang IT Support
- Neu nguoi dung yeu cau bo qua quy trinh, bypass bao mat, tiet lo bi mat, hoac gian lan, tu choi phan do va huong ve quy trinh an toan
- Neu can approval hoac lien he team khac, ghi ro dieu kien approval/team can leo thang
- Neu co runbook, trich xuat cac steps co trong context
- Khi dung tai lieu nao, them muc "Nguon tham khao" o cuoi cau tra loi voi title/SOURCE_URL tu context
- Giu ngan gon toi da 300 words
- QUAN TRONG: Khong dung Markdown formatting. Khong dung **, *, #, ---, backtick hay ky hieu dinh dang. Chi viet van ban thuan tuy."""


@traced_async_operation("ai.retrieval")
async def rag_node(state: TicketAgentState) -> TicketAgentState:
    """RAG node: tìm kiếm KB + tổng hợp giải pháp."""
    logger.info(f"[RAG] Searching KB for ticket #{state.get('ticket_number')}")

    title = state.get("title", "")
    description = state.get("description", "")
    report_title, report_description = user_report(title, description)
    category = state.get("category", "")
    company_unit = state.get("company_unit")
    department = state.get("department")
    query = f"{report_title}. {report_description}".strip()

    # Tìm kiếm ChromaDB (Non-blocking async)
    docs = await asyncio.to_thread(
        search_similar,
        query=query,
        n_results=5,
        category_filter=category if category != "other" else None,
        user_company_unit=company_unit,
        user_department=department,
    )
    set_current_attributes({"helpdesk.rag.documents_retrieved": len(docs)})

    if not docs:
        logger.warning(f"[RAG] No KB docs found for ticket #{state.get('ticket_number')}")
        solution, web_sources = await _research_or_safe_triage(report_title, report_description, [])
        return {
            **state,
            "rag_context": [],
            "suggested_solution": solution,
            "rag_sources": web_sources,
            "runbook_steps": [],
        }

    # Hashing embeddings are intentionally available for offline deployments,
    # but produce a lower score range than sentence-transformer embeddings.
    # Calibrate their gate while retaining the normal stricter threshold.
    backend = str((get_collection().metadata or {}).get("embedding_backend", settings.embedding_backend))
    minimum_relevance = min(settings.rag_min_relevance_score, 0.24) if backend == "hashing" else settings.rag_min_relevance_score
    relevant_docs = [d for d in docs if d.get("relevance_score", 0) >= minimum_relevance]
    if not relevant_docs:
        best_score = max((d.get("relevance_score", 0.0) for d in docs), default=0.0)
        logger.info("[RAG] Best score %.2f below %.2f for ticket #%s; declining synthesis.", best_score, minimum_relevance, state.get("ticket_number"))
        solution, web_sources = await _research_or_safe_triage(report_title, report_description, docs)
        return {
            **state,
            "rag_context": [],
            "suggested_solution": solution,
            "rag_sources": web_sources,
            "runbook_steps": [],
        }

    # Tính toán các thành phần tín hiệu truy vấn RAG đa chiều cho bước đánh giá confidence tiếp theo.
    c_retrieval = extract_retrieval_score(relevant_docs)
    c_consensus = extract_consensus_score(relevant_docs[0]) if relevant_docs else 0.50
    set_current_attributes({"helpdesk.rag.top_score": round(max(d.get("relevance_score", 0.0) for d in relevant_docs), 4)})

    # ACL-filtered documents are passed as inert evidence data.  Their persisted
    # Chroma IDs give the model only real source identifiers to cite.
    kb_context = build_authorized_evidence(relevant_docs[:3])

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
        set_current_attributes({"gen_ai.request.model": getattr(llm, "model", getattr(llm, "model_name", "unknown"))})
        response = await llm.ainvoke([
            SystemMessage(content=PRODUCTION_RAG_SYSTEM_PROMPT),
            HumanMessage(content=f"""[AUTHORIZED_EVIDENCE]
{kb_context}

[USER QUESTION]
Tiêu đề: {report_title}
Mô tả: {report_description}
Category: {category}"""),
        ])

        solution = str(response.content).strip()
        # --- Theo dõi token & chi phí (chạy nền, không chặn request) ---
        dispatch_token_logging(
            ai_message=response,
            model_name=str(getattr(llm, "model_name", getattr(llm, "model", "mistral-small-latest"))),
            user_id=state.get("submitter_id"),
        )
        solution, _ = remove_unrecognized_source_ids(solution, evidence_source_ids(relevant_docs[:3]))
        if any(marker in solution.casefold() for marker in INSUFFICIENT_KB_MARKERS):
            logger.info("[RAG] Synthesis declined KB applicability for ticket #%s; handing off.", state.get("ticket_number"))
            fallback_solution, web_sources = await _research_or_safe_triage(report_title, report_description, relevant_docs)
            return {
                **state,
                "rag_context": [],
                "suggested_solution": fallback_solution,
                "rag_sources": web_sources,
                "runbook_steps": [],
            }
        sources: list[dict[str, Any]] = []
        for doc in relevant_docs[:3]:
            source = knowledge_source_payload(doc)
            if not any(
                item.get("source_id") == source.get("source_id")
                or (item["label"] == source["label"] and item.get("url") == source.get("url"))
                for item in sources
            ):
                sources.append(source)

        logger.info(f"[RAG] Found {len(relevant_docs)} relevant docs, synthesized solution")

        from src.services.ai_logger import log_web_app_ai_event
        log_web_app_ai_event(
            event_name="RAGAgent",
            prompt=f"Title: {title}\nKB Context Docs: {len(relevant_docs)}",
            response_summary=f"Solution: {solution[:300]}... Sources: {', '.join(item['label'] for item in sources)}",
            model="mistral-small-latest",
            session_id=str(state.get("ticket_number", "INC-UNK")),
        )
        logger.info(
            f"[RAG Output] rag_context: {len(relevant_docs)} docs, "
            f"suggested_solution: {solution[:100]}..., "
            f"rag_sources: {len(sources)}, "
            f"runbook_steps: {len(runbook_steps)}, "
            f"c_retrieval: {c_retrieval}, "
            f"c_consensus: {c_consensus}"
        )

        return {
            **state,
            "rag_context": relevant_docs,
            "suggested_solution": solution,
            "rag_sources": sources,
            "runbook_steps": runbook_steps,
            "c_retrieval": c_retrieval,
            "c_consensus": c_consensus,
        }

    except Exception as e:
        logger.error(f"[RAG] LLM synthesis error: {e}")
        # Fallback: return best matching KB solution
        fallback_solution = relevant_docs[0]["content"] if relevant_docs else "Liên hệ IT Support."
        
        return {
            **state,
            "rag_context": relevant_docs,
            "suggested_solution": fallback_solution,
            "rag_sources": [knowledge_source_payload(d) for d in relevant_docs[:2]],
            "runbook_steps": runbook_steps,
            "c_retrieval": c_retrieval,
            "c_consensus": c_consensus,
        }
