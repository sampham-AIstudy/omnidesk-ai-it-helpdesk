"""Context-aware retrieval query construction for multi-turn conversations.

This module deterministically reformulates search queries for context-dependent
follow-up turns using authorized recent conversation context. It operates
strictly on the RETRIEVAL QUERY and never mutates generation conversation
history, ACL scoping, or system prompts.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from src.config import get_settings
from src.services.recent_conversation_context import RecentConversationMessage

logger = logging.getLogger(__name__)
settings = get_settings()

_GREETING_OR_SHORT_NON_TECHNICAL = {
    "xin chào", "xin chao", "chào bạn", "chao ban", "chào ad", "chao ad",
    "hello", "hi", "alo", "chào bot", "chao bot", "chào", "chao",
    "cảm ơn", "cam on", "ok", "oke", "dạ", "da", "vâng", "vang",
    "thanks", "thank you",
    "tôi buồn quá", "toi buon qua", "buồn quá", "buon qua",
    "thôi để sau", "thoi de sau",
    "hiểu rồi", "hieu roi", "được rồi", "duoc roi",
}

_SOCIAL_OR_NON_TECHNICAL_PATTERNS = [
    # 1. Gratitude & thanks
    r"\b(cảm ơn|cam on|cám ơn|thanks|thank you)\b",
    # 2. Acknowledgements / confirmations / done / understood
    r"\b(được rồi|duoc roi|xong rồi|xong roi|ổn rồi|on roi|hiểu rồi|hieu roi|rõ rồi|ro roi|biết rồi|biet roi)\b",
    # 3. Dismissals / closing / stop
    r"\b(thôi|thoi)\s*(nhé|nhe|nha|ạ|a|được rồi|duoc roi|để sau|de sau|không cần|khong can|thế thôi|the thoi|nào|vay|vậy)?\b",
    # 4. Small talk / sentiment
    r"\b(buồn quá|buon qua|chán quá|chan qua|mệt quá|met qua|vui quá|vui qua)\b",
    r"\b(tôi|tao|tui|minh)\s+(buồn|buon|chán|chan|mệt|met)\b",
    # 5. Greetings & fillers
    r"\b(xin chào|xin chao|chào bạn|chao ban|chào ad|chao ad|chào bot|chao bot|hello|hi|alo)\b",
    r"^(ok|oke|dạ|da|vâng|vang|ừ|u|uh|ờ|o|yes|yeah|yep)[\s\.,!]*$",
    r"^(ok|oke|dạ|da|vâng|vang|ừ|u|uh)\s+(nhé|nhe|nha|ạ|a|ơi|oi|bạn|ad|bot|cảm ơn|cam on|được rồi|duoc roi)$",
]
_COMPILED_SOCIAL_PATTERNS = [re.compile(pattern, re.IGNORECASE) for pattern in _SOCIAL_OR_NON_TECHNICAL_PATTERNS]


def is_social_or_non_technical(text: str) -> bool:
    """Determine deterministically if a short message is a social / greeting / closing / acknowledgement."""
    normalized = text.strip().casefold()
    if not normalized:
        return False
    # Social / acknowledgement / dismissal messages are short fragments (<= 6 words).
    # Long sentences containing technical explanations (e.g. "VPN đã kết nối được rồi nhưng...") are substantive.
    if len(normalized.split()) > 6:
        return False
    clean = re.sub(r"[^\w\s]", "", normalized).strip()
    if clean in _GREETING_OR_SHORT_NON_TECHNICAL:
        return True
    return any(pattern.search(clean) or pattern.search(text) for pattern in _COMPILED_SOCIAL_PATTERNS)


# Regex patterns matching context-dependent follow-up signals in Vietnamese
_CONTEXT_DEPENDENT_PATTERNS = [
    # 1. Prepositional / complement follow-ups
    r"^(?:về|ve|cho|của|cua|với|voi|ở|o|tại|tai|thuộc|thuoc|trong|theo)\s+(?:giam\s+doc|director|sep|manager|admin|it|vpn|wifi|wi-fi|email|phan\s+mem|may\s+tinh|laptop|tai\s+khoan|\w+)",
    # 2. Step / Method references
    r"\b(bước|buoc)\s+(đầu|dau|đầu tiên|dau tien|1|một|mot|2|hai|thứ hai|thu hai|3|ba|thứ ba|thu ba|tiếp|tiep|tiếp theo|tiep theo|kế|ke|sau|đó|do|này|nay)\b",
    r"\b(cách|cach)\s+(đầu|dau|đầu tiên|dau tien|1|một|mot|2|hai|thứ hai|thu hai|3|ba|thứ ba|thu ba|tiếp|tiep|tiếp theo|tiep theo|khác|khac|đó|do|này|nay)\b",
    r"\b(hướng dẫn|huong dan|giải pháp|giai phap|phương án|phuong an|gợi ý|goi y)\s+(đó|do|trên|tren|này|nay)\b",
    # 3. Deictic reference pronouns pointing to previous turns
    r"\b(cái đó|cai do|cái này|cai nay|vấn đề đó|van de do|lỗi đó|loi do|lỗi này|loi nay|vụ này|vu nay|cổng đó|cong do|cổng này|cong nay|thiết bị đó|thiet bi do|thiết bị này|thiet bi nay|app đó|app nay|ứng dụng đó|ung dung do|ứng dụng này|ung dung nay)\b",
    r"\b(?:cổng đó|cổng này|cái đó|cái này|vấn đề đó|lỗi đó|chỗ đó|bước đó|thiết bị đó|ứng dụng đó)\s+(?:thì\s+)?(?:sao|như thế nào|thế nào)\b",
    r"\b(nó|no|em nó|em no)\s+(bị|bi|lại|vẫn|van|không|khong|chưa|chua|lỗi|loi|hỏng|hong|timeout|timed out|treo|tat|ngat)\b",
    r"\b(như trên|nhu tren|như vừa nói|nhu vua noi|như đã nói|nhu da noi|ở trên|o tren|lúc nãy|luc nay|như cũ|nhu cu|như trước|nhu truoc)\b",
    # 4. Follow-up status / failure / progress markers
    r"\b(vẫn không được|van khong duoc|vẫn chưa được|van chua duoc|vẫn bị lỗi|van bi loi|vẫn lỗi|van loi|vẫn báo lỗi|van bao loi|vẫn thế|van the|vẫn vậy|van vay)\b",
    r"\b(vẫn\s+timeout|van\s+timeout|vẫn\s+timed\s+out|van\s+timed\s+out|bị\s+timeout|bi\s+timeout)\b",
    r"\b(lại bị|lai bi|lại lỗi|lai loi|lỗi vẫn còn|loi van con)\b",
    r"\b(chưa được|chua duoc)\b",
    r"\b(thử rồi|thu roi|đã thử|da thu|đã làm|da lam|làm rồi|lam roi|làm theo rồi|lam theo roi|thử lại|thu lai)\b",
    # 5. Standalone failure / question markers
    r"^(không được|khong duoc|chưa được|chua duoc|vẫn lỗi|van loi|vẫn thế|van the|vẫn vậy|van vay)[\.\?!]*$",
    # 6. Follow-up inquiries
    r"\b(còn cách nào|con cach nao|còn cách khác|con cach khac|còn gì khác|con gi khac|tiếp theo làm gì|tiep theo lam gi|giờ làm gì|gio lam gi|làm sao nữa|lam sao nua|thế nào nữa|the nao nua|rồi sao nữa|roi sao nua)\b",
    r"\b(tại sao không được|tai sao khong duoc|tại sao lại lỗi|tai sao lai loi|tại sao bước đó|tai sao buoc do)\b",
    r"\b(có rủi ro gì|co rui ro gi|có ảnh hưởng gì|co anh huong gi|an toàn không|an toan khong)\b",
    r"\b(cấu hình ở đâu|cau hinh o dau|tìm ở đâu|tim o dau|chỉnh ở đâu|chinh o dau)\b",
    r"\b(thế\s+)?(ai là người|ai sẽ|ai|ai có quyền|ai chịu trách nhiệm)\s+(duyệt|phê duyệt|xử lý|tiếp nhận|giải quyết)\b",
    r"\b(mất bao lâu|bao lâu thì xong|bao lâu được duyệt|thời gian xử lý|khi nào xong)\b",
]

_COMPILED_CONTEXT_PATTERNS = [re.compile(pattern, re.IGNORECASE) for pattern in _CONTEXT_DEPENDENT_PATTERNS]

_STANDALONE_FAILURES = {
    "không được", "khong duoc", "chưa được", "chua duoc", "vẫn lỗi", "van loi",
    "vẫn thế", "van the", "vẫn vậy", "van vay", "vẫn chưa được", "van chua duoc",
    "vẫn không được", "van khong duoc", "làm rồi nhưng không được", "thử rồi vẫn lỗi",
}


@dataclass(frozen=True)
class RetrievalQueryResult:
    """The result of a context-aware retrieval query reformulation."""

    query: str
    rewritten: bool
    reason: str
    original_query: str


def is_context_dependent(query: str) -> bool:
    """Determine deterministically if a query relies on prior conversational context.

    Uses semantic, deictic, step-reference, and follow-up failure markers.
    Never relies on message length alone (e.g. 'VPN là gì?' is self-contained).
    """
    normalized = query.strip().casefold()
    if not normalized:
        return False

    if is_social_or_non_technical(query):
        return False

    # Check exact match against short standalone phrases
    clean_punct = re.sub(r"[^\w\s]", "", normalized).strip()
    if clean_punct in _STANDALONE_FAILURES:
        return True

    # Match compiled semantic patterns
    return any(pattern.search(normalized) for pattern in _COMPILED_CONTEXT_PATTERNS)


def _is_substantive_user_message(content: str) -> bool:
    if is_social_or_non_technical(content):
        return False
    clean = re.sub(r"[^\w\s]", "", content.strip().casefold())
    return len(clean.split()) >= 2


def extract_recent_conversation_context(
    recent_history: list[RecentConversationMessage],
    *,
    max_chars: int = 250,
) -> str:
    """Extract compact, relevant context from recent conversation turns.

    Prioritizes user-stated entities and problems over assistant responses
    to prevent assistant hallucinations from overriding facts.
    """
    if not recent_history:
        return ""

    # 1. Collect substantive user turns in reverse chronological order
    substantive_user_turns: list[str] = []
    for msg in reversed(recent_history):
        if msg.role == "user" and _is_substantive_user_message(msg.content):
            text = msg.content.strip()
            if text not in substantive_user_turns:
                substantive_user_turns.append(text)
            if len(substantive_user_turns) >= 2:
                break

    if substantive_user_turns:
        # Re-order chronologically: oldest of the recent to newest
        chronological = list(reversed(substantive_user_turns))
        combined = " ".join(chronological).strip()
        return combined[:max_chars].strip()

    # 2. Fallback: if user turns were too brief, check assistant messages for technical subject
    for msg in reversed(recent_history):
        if msg.role in {"assistant", "agent"}:
            first_line = msg.content.strip().split("\n")[0].strip()
            if len(first_line) > 10:
                return first_line[:max_chars].strip()

    return ""


def extract_recent_ticket_refined_context(
    recent_history: list[RecentConversationMessage],
    *,
    max_chars: int = 200,
) -> str:
    """Extract refined issue descriptions from recent user/technician messages in a ticket.

    Allows subsequent turns (e.g. 'VPN đã vào được nhưng giờ DNS không resolve')
    to properly inform retrieval without being dominated by the initial ticket title.
    """
    if not recent_history:
        return ""

    user_updates: list[str] = []
    for msg in reversed(recent_history):
        if msg.role in {"user", "technician"} and _is_substantive_user_message(msg.content):
            text = msg.content.strip()
            if text not in user_updates:
                user_updates.append(text)
            if len(user_updates) >= 2:
                break

    if user_updates:
        chronological = list(reversed(user_updates))
        combined = " ".join(chronological).strip()
        return combined[:max_chars].strip()

    return ""


def build_context_aware_retrieval_query(
    current_message: str,
    *,
    recent_history: list[RecentConversationMessage] | None = None,
    ticket_context: dict[str, Any] | None = None,
    max_chars: int | None = None,
) -> RetrievalQueryResult:
    """Construct a compact, search-oriented retrieval query using authorized context.

    Guarantees:
    - Zero LLM calls (deterministic & low-latency).
    - Current user intent is always preserved.
    - Query length is strictly bounded by max_chars (or settings.max_retrieval_query_chars).
    - Self-contained queries are not rewritten unnecessarily.
    - Preserves caller-scoped isolation (operates only on provided recent_history).
    """
    raw_message = current_message.strip()
    bound = max_chars if max_chars is not None else getattr(settings, "max_retrieval_query_chars", 400)
    history = recent_history or []

    # =========================================================================
    # A. Ticket Retrieval Path
    # =========================================================================
    if ticket_context is not None:
        title = str(ticket_context.get("title") or "").strip()
        description = str(ticket_context.get("description") or "").strip()
        base_ticket_parts = [p for p in (title, description) if p]
        base_ticket_str = ". ".join(base_ticket_parts).strip()

        # Check if recent ticket conversation refined or updated the problem
        refined_context = extract_recent_ticket_refined_context(history, max_chars=200)
        context_dep = is_context_dependent(raw_message)

        if refined_context and (context_dep or refined_context not in base_ticket_str):
            # Combine ticket metadata + refined context + current message
            candidates = [p for p in (base_ticket_str, refined_context, raw_message) if p]
            combined = ". ".join(candidates).strip()
            if len(combined) > bound:
                # Ensure current_message and refined_context are preserved; bound title/desc
                avail = max(50, bound - len(raw_message) - len(refined_context) - 6)
                bounded_base = base_ticket_str[:avail].strip()
                combined = f"{bounded_base}. {refined_context}. {raw_message}".strip()
            return RetrievalQueryResult(
                query=combined[:bound].strip(),
                rewritten=True,
                reason="ticket_context_with_recent_turns",
                original_query=raw_message,
            )

        # Standard ticket query (title + description + current message)
        candidates = [p for p in (base_ticket_str, raw_message) if p]
        combined = ". ".join(candidates).strip()
        if len(combined) > bound:
            avail = max(50, bound - len(raw_message) - 4)
            bounded_base = base_ticket_str[:avail].strip()
            combined = f"{bounded_base}. {raw_message}".strip()

        return RetrievalQueryResult(
            query=combined[:bound].strip(),
            rewritten=False,
            reason="standard_ticket_query",
            original_query=raw_message,
        )

    # =========================================================================
    # B. Workspace Chat Retrieval Path
    # =========================================================================
    if not history:
        return RetrievalQueryResult(
            query=raw_message[:bound].strip(),
            rewritten=False,
            reason="no_history",
            original_query=raw_message,
        )

    if not is_context_dependent(raw_message):
        return RetrievalQueryResult(
            query=raw_message[:bound].strip(),
            rewritten=False,
            reason="self_contained",
            original_query=raw_message,
        )

    # Extract minimum relevant prior context
    context = extract_recent_conversation_context(history, max_chars=250)
    if not context:
        return RetrievalQueryResult(
            query=raw_message[:bound].strip(),
            rewritten=False,
            reason="no_relevant_context",
            original_query=raw_message,
        )

    # Combine context and current message, ensuring current intent is strictly preserved
    avail_for_context = max(50, bound - len(raw_message) - 4)
    bounded_context = context[:avail_for_context].strip()
    rewritten_query = f"{bounded_context}. {raw_message}".strip()

    logger.info(
        "Context-Aware Retrieval Query Rewrite: '%s' -> '%s' (reason: context_dependent_followup)",
        raw_message,
        rewritten_query[:100],
    )

    return RetrievalQueryResult(
        query=rewritten_query[:bound].strip(),
        rewritten=True,
        reason="context_dependent_followup",
        original_query=raw_message,
    )


@dataclass(frozen=True)
class ContextualQueryResolution:
    raw_query: str
    resolved_query: str
    is_rewritten: bool
    reason: str


_PREPOSITIONAL_FOLLOWUP_PATTERN = re.compile(
    r"^(?:về|ve|cho|của|cua|với|voi|ở|o|tại|tai|thuộc|thuoc|trong|theo)\s+(.+)$",
    re.IGNORECASE,
)


def resolve_contextual_user_query(
    current_message: str,
    *,
    recent_history: list[RecentConversationMessage] | None = None,
    ticket_context: dict[str, Any] | None = None,
) -> ContextualQueryResolution:
    """Deterministically resolve follow-up queries into complete contextual queries.

    Runs BEFORE routing, privacy guardrails, and intent classification to guarantee
    consistent, context-aware decisions across the entire pipeline.
    """
    raw_message = current_message.strip()
    if not raw_message:
        return ContextualQueryResolution(
            raw_query=raw_message,
            resolved_query=raw_message,
            is_rewritten=False,
            reason="empty",
        )

    history = recent_history or []
    if not history and not ticket_context:
        return ContextualQueryResolution(
            raw_query=raw_message,
            resolved_query=raw_message,
            is_rewritten=False,
            reason="no_history",
        )

    # 0. Check if query is social / greeting / closing / acknowledgement (never merge)
    if is_social_or_non_technical(raw_message):
        return ContextualQueryResolution(
            raw_query=raw_message,
            resolved_query=raw_message,
            is_rewritten=False,
            reason="social_or_non_technical",
        )

    # 1. Check if query is explicitly self-contained with its own subject (e.g. "thông tin của tôi")
    from src.services.profile_chat_service import _SELF_PROFILE_PATTERNS, _fold
    folded_raw = _fold(raw_message)
    if any(re.search(pat, folded_raw) for pat in _SELF_PROFILE_PATTERNS):
        return ContextualQueryResolution(
            raw_query=raw_message,
            resolved_query=raw_message,
            is_rewritten=False,
            reason="explicit_self_profile",
        )

    # 2. Case A: Prepositional / complement follow-up (e.g. "về giám đốc", "cho nhân viên mới")
    prep_match = _PREPOSITIONAL_FOLLOWUP_PATTERN.match(raw_message)
    if prep_match:
        last_user_msg = next(
            (msg.content.strip() for msg in reversed(history) if msg.role == "user" and _is_substantive_user_message(msg.content)),
            None,
        )
        if last_user_msg:
            resolved = f"{last_user_msg} {raw_message}".strip()
            return ContextualQueryResolution(
                raw_query=raw_message,
                resolved_query=resolved,
                is_rewritten=True,
                reason="prepositional_followup_completion",
            )

    # 3. Case B: Entity / clarification follow-up after clarification prompt or incomplete phrase
    last_user_msg = next(
        (msg.content.strip() for msg in reversed(history) if msg.role == "user"),
        None,
    )
    last_assistant_msg = next(
        (msg.content.strip() for msg in reversed(history) if msg.role in {"assistant", "agent"}),
        None,
    )

    is_short_fragment = len(raw_message.split()) <= 4
    if is_short_fragment and last_user_msg:
        # Guard: never merge greetings, social phrases, or acknowledgements
        current_folded_clean = re.sub(r"[^\w\s]", "", _fold(raw_message)).strip()
        if current_folded_clean in _GREETING_OR_SHORT_NON_TECHNICAL:
            return ContextualQueryResolution(
                raw_query=raw_message,
                resolved_query=raw_message,
                is_rewritten=False,
                reason="greeting_or_social",
            )

        last_folded = _fold(last_user_msg)
        is_incomplete_user = any(last_folded.endswith(s) for s in ("cuc", "cai", "chiec", "loi", "hong", "bi", "bi hong", "khong vao duoc", "mat"))
        is_clarification_prompt = last_assistant_msg and any(term in _fold(last_assistant_msg) for term in ("thiet bi", "dich vu", "mo ta them", "cho minh biet", "cho toi biet"))

        if is_incomplete_user or is_clarification_prompt:
            user_tokens = last_user_msg.split()
            raw_tokens = raw_message.split()
            if user_tokens and raw_tokens and user_tokens[-1].lower() == raw_tokens[0].lower():
                merged = f"{last_user_msg} {' '.join(raw_tokens[1:])}".strip()
            else:
                merged = f"{last_user_msg} {raw_message}".strip()
            return ContextualQueryResolution(
                raw_query=raw_message,
                resolved_query=merged,
                is_rewritten=True,
                reason="entity_clarification_completion",
            )

    # 4. Deictic / Pronoun reference resolution (e.g. "nó vẫn không vào được", "cái đó bị lỗi")
    if is_context_dependent(raw_message):
        context = extract_recent_conversation_context(history, max_chars=200)
        if context:
            rewritten = f"{context}. {raw_message}".strip()
            return ContextualQueryResolution(
                raw_query=raw_message,
                resolved_query=rewritten,
                is_rewritten=True,
                reason="deictic_context_followup",
            )

    return ContextualQueryResolution(
        raw_query=raw_message,
        resolved_query=raw_message,
        is_rewritten=False,
        reason="standard_query",
    )

