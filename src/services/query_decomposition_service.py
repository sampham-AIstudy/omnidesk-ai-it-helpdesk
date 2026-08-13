"""Retrieval-only query decomposition for knowledge-oriented Help Desk chat."""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from langchain_core.messages import HumanMessage, SystemMessage

from src.prompts import QUERY_DECOMPOSITION_SYSTEM_PROMPT
from src.services.llm import get_fast_classifier_llm

logger = logging.getLogger(__name__)

_ACTION_ONLY = re.compile(
    r"\b(tạo|mo|mở|cập nhật|cap nhat|đóng|dong|xóa|xoa|reset|đổi|doi|cấp|cap|"
    r"approve|phê duyệt|phe duyet|install|cài đặt|cai dat|escalate)\b.*\b("
    r"ticket|incident|request|tài khoản|tai khoan|quyền|quyen|approval)\b",
    re.IGNORECASE,
)
_KNOWLEDGE_SIGNAL = re.compile(
    r"\b(là gì|la gi|như thế nào|nhu the nao|bao nhiêu|bao nhieu|khi nào|khi nao|"
    r"điều kiện|dieu kien|chính sách|chinh sach|quy trình|quy trinh|SLA|policy|"
    r"how|what|when|which|why|where)\b|\?",
    re.IGNORECASE,
)
_COMPLEX_SIGNAL = re.compile(r"\?|\b(và|va|also|and|sau đó|sau do|đồng thời|dong thoi)\b|;", re.IGNORECASE)


@dataclass(frozen=True)
class DecompositionResult:
    """The decomposition decision, separate from the strict model JSON schema."""

    is_knowledge_question: bool
    is_complex: bool
    sub_queries: list[str]


def is_knowledge_question(question: str) -> bool:
    """Keep ticket/account/approval actions out of the retrieval decomposer."""
    normalized = question.strip()
    return bool(normalized) and (not _ACTION_ONLY.search(normalized) or bool(_KNOWLEDGE_SIGNAL.search(normalized)))


def _clean_sub_queries(value: object, original_question: str) -> list[str]:
    if not isinstance(value, list):
        return [original_question]
    cleaned: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        query = item.strip()
        if query and query not in cleaned:
            cleaned.append(query)
        if len(cleaned) == 4:
            break
    return cleaned or [original_question]


async def decompose_knowledge_query(question: str) -> DecompositionResult:
    """Use an LLM only for potentially multi-part knowledge retrieval requests."""
    original_question = question.strip()
    if not is_knowledge_question(original_question):
        return DecompositionResult(False, False, [])
    if not _COMPLEX_SIGNAL.search(original_question):
        return DecompositionResult(True, False, [original_question])

    try:
        response = await get_fast_classifier_llm().ainvoke(
            [
                SystemMessage(content=QUERY_DECOMPOSITION_SYSTEM_PROMPT),
                HumanMessage(content=f"USER QUESTION:\n{original_question}\n\nJSON OUTPUT:"),
            ]
        )
        payload = json.loads(str(response.content).strip())
        sub_queries = _clean_sub_queries(payload.get("sub_queries"), original_question)
        return DecompositionResult(
            True,
            bool(payload.get("is_complex", False)) and len(sub_queries) > 1,
            sub_queries,
        )
    except (json.JSONDecodeError, TypeError, ValueError, AttributeError) as exc:
        logger.info("Query decomposition unavailable; using original query: %s", type(exc).__name__)
        return DecompositionResult(True, False, [original_question])
