"""
Output Guardrail Node — Bước 2 Guardrail Hậu sinh (Post-Generation).

Chạy sau khi tổng hợp giải pháp RAG để:
1. Phân loại & ẩn thông tin nhạy cảm (PII, secrets, API key, credential).
2. Tính C_groundedness qua mô hình CrossEncoder Reranker (chỉ khi có ngữ cảnh RAG).
3. Tổng hợp C_RAG = w1*C_retrieval + w2*C_consensus + w3*C_groundedness và lưu điểm
   confidence_score vào state của agent để Policy Engine điều hướng và UI hiển thị.

Khi không có ngữ cảnh RAG (trò chuyện thông thường), toàn bộ quá trình tính toán điểm
được bỏ qua hoàn toàn — đảm bảo 0ms độ trễ overhead cho các phản hồi không RAG.
"""
import logging
import re
from typing import Any

from src.agents.state import TicketAgentState
from src.guardrails.output_guardrails import format_plain_text_response, redact_secrets_and_pii
from src.observability.tracing import set_current_attributes, traced_async_operation

logger = logging.getLogger(__name__)

# Pattern lọc thông tin PII / Dữ liệu nhạy cảm
SECRET_PATTERNS = [
    (r"sk-[a-zA-Z0-9]{32,}", "[REDACTED_API_KEY]"),
    (r"(password|paswd|pwd)\s*=\s*['\"]?[^'\"]+['\"]?", "[REDACTED_CREDENTIAL]"),
    (r"postgres://[^\s]+", "[REDACTED_DB_URI]"),
    (r"mongodb(\+srv)?://[^\s]+", "[REDACTED_DB_URI]"),
]


@traced_async_operation("ai.guardrail.output")
async def output_guardrail_node(state: TicketAgentState) -> dict[str, Any]:
    """Node Output Guardrail Bước 2: Ẩn thông tin nhạy cảm và tính điểm C_RAG confidence."""
    solution = state.get("suggested_solution", "")
    if not solution:
        return {}

    logger.info(
        "[OutputGuardrailNode] Bước 2: Lọc thông tin nhạy cảm cho ticket #%s",
        state.get("ticket_number"),
    )

    # ── 1. Lọc PII & Secrets ───────────────────────────────────────────────────
    sanitized = solution
    for pattern, replacement in SECRET_PATTERNS:
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)

    # Sử dụng bộ lọc chuẩn để đảm bảo nhất quán với API/Chat response
    sanitized = redact_secrets_and_pii(sanitized)["redacted"]
    formatted = format_plain_text_response(sanitized)
    set_current_attributes({"helpdesk.guardrail.result": "REDACTED" if formatted != solution else "ALLOW"})
    if formatted != solution:
        logger.warning(
            "[OutputGuardrailNode] Đã bọc/ẩn thông tin nhạy cảm từ giải pháp ticket #%s",
            state.get("ticket_number"),
        )

    # ── 2. Đánh giá RAG Confidence Score (chỉ thực hiện khi có ngữ cảnh RAG) ────
    rag_context: list[dict] = state.get("rag_context") or []
    update: dict[str, Any] = {}

    if formatted != solution:
        update["suggested_solution"] = formatted

    if rag_context:
        # Trích xuất các thành phần trung gian đã tính ở rag_node.
        c_retrieval: float = float(state.get("c_retrieval") or 0.0)
        c_consensus: float = float(state.get("c_consensus") or 0.50)

        # Tính C_groundedness qua mô hình CrossEncoder Reranker (có fallback = 0.0 nếu lỗi).
        from src.services.rag_confidence_service import (
            calculate_groundedness_with_reranker,
            compute_final_rag_confidence,
        )
        c_groundedness = calculate_groundedness_with_reranker(formatted or solution, rag_context)
        c_rag = compute_final_rag_confidence(c_retrieval, c_consensus, c_groundedness)

        logger.info(
            "[OutputGuardrailNode] C_RAG=%.3f (retrieval=%.3f, consensus=%.3f, groundedness=%.3f) cho ticket #%s",
            c_rag,
            c_retrieval,
            c_consensus,
            c_groundedness,
            state.get("ticket_number"),
        )
        set_current_attributes({
            "helpdesk.confidence.c_retrieval": round(c_retrieval, 4),
            "helpdesk.confidence.c_consensus": round(c_consensus, 4),
            "helpdesk.confidence.c_groundedness": round(c_groundedness, 4),
            "helpdesk.confidence.c_rag": round(c_rag, 4),
        })

        update["confidence_score"] = c_rag
    else:
        # Không có ngữ cảnh RAG → Lượt trò chuyện thông thường. Bỏ qua toàn bộ bước tính toán.
        # confidence_score giữ nguyên là None; UI sẽ tự động ẩn chỉ số này.
        logger.debug(
            "[OutputGuardrailNode] Không có ngữ cảnh RAG — bỏ qua tính toán confidence cho ticket #%s",
            state.get("ticket_number"),
        )

    return update
