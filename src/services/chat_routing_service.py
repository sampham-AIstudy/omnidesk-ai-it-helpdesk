"""Fast, deterministic request gate for interactive Help Desk chat.

The gate runs before retrieval and episodic-memory lookup. Conversational or
out-of-scope turns therefore do not acquire unrelated KB sources or pay the
latency cost of RAG.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Literal

ChatRoute = Literal[
    "direct_response",
    "needs_clarification",
    "ticket_status",
    "action_request",
    "incident",
    "knowledge",
]
Answerability = Literal["direct", "needs_clarification", "tool_required", "evidence_required"]


@dataclass(frozen=True)
class ChatRouteDecision:
    route: ChatRoute
    answerability: Answerability
    classification_confidence: float
    direct_reply: str | None = None

    @property
    def should_retrieve(self) -> bool:
        return self.route in {"incident", "knowledge"}

    @property
    def retrieval_required(self) -> bool:
        """Named gate for telemetry and evaluation contracts."""
        return self.should_retrieve

    @property
    def retrieval_decision(self) -> Literal["required", "not_required"]:
        return "required" if self.should_retrieve else "not_required"

    @property
    def should_use_memory(self) -> bool:
        return self.route in {"incident", "knowledge"}

    @property
    def should_search_web(self) -> bool:
        """The deterministic gate never authorizes web search by itself."""
        return False

    @property
    def should_invoke_tool(self) -> bool:
        return self.route in {"ticket_status", "action_request"}


def _fold(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text.casefold())
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn").replace("\u0111", "d")


_GREETING = re.compile(r"^(?:xin )?(?:chao|hello|hi|hey)(?: ban)?(?: nhe| a| ah)?[!., ]*$")
_THANKS = re.compile(r"^(?:cam on|thanks|thank you)(?: ban)?(?: nhe| a| ah)?[!., ]*$")
_ACKNOWLEDGEMENT = re.compile(
    r"^(?:(?:ok|oke|okay)(?: hieu roi)?|da hieu|hieu roi|ro roi|duoc roi)[!., ]*$"
)
_CASUAL_CHECK_IN = re.compile(r"^(?:ban )?khoe(?: khong)?[?!. ]*$")
_NON_IT_SOCIAL = re.compile(
    r"\b(?:hom nay an gi|mua xe may|toi buon qua|ban buon qua|am sad|what should i eat)\b"
)
_VAGUE_INCIDENT = re.compile(
    r"^(?:may(?: tinh)? toi bi loi|khong dung duoc|khong duoc|no cu bi the ay|app bi ngu roi)[!., ]*$"
)
_STATUS = re.compile(
    r"\b(?:trang thai|tinh trang|status|kiem tra).*\b(?:ticket|incident|yeu cau|request)\b|"
    r"\b(?:ticket|incident)\b.*\b(?:trang thai|status)\b"
)
_TICKET_REFERENCE_STATUS = re.compile(
    r"\b(?:ticket|incident)\s*#?\s*(?:inc|req)-[a-z0-9-]+\b.*"
    r"\b(?:sao roi|the nao|cap nhat|tinh hinh)\b"
)
_ACTION = re.compile(
    r"\b(?:tao|mo|dong|cap nhat|reset|doi|yeu cau|chuyen|escalate)\b.*"
    r"\b(?:ticket|incident|request|tai khoan|quyen|approval)\b"
)
# A process/policy question may mention the verb used by a real workflow
# (for example, "quy trinh tao Service Request"). It is still retrieval work,
# not an instruction to mutate a resource. Keep this narrow and run it before
# execution matching below.
_KNOWLEDGE_QUESTION = re.compile(
    r"^(?:(?:cho toi biet|toi muon biet)\s+)?(?:quy trinh|cach|huong dan|chinh sach|dieu kien)\b|"
    r"\b(?:la gi|nghia la gi|ai duyet|can nhung thong tin gi|gom nhung buoc nao|"
    r"hoat dong (?:the nao|ra sao)|mat bao lau)\b"
)
_EXECUTION_ACTION = re.compile(
    r"^(?:(?:hay|vui long)\s+)?(?:gui|dang ky)\b|"
    r"^(?:(?:hay|vui long)\s+)?tao\s+(?:service request|ticket|incident|yeu cau|request|don|issue|tai khoan|form|m365|microsoft 365)\b|"
    r"^(?:toi|minh|em|tao)\s+(?:muon|can)\s+(?:xin|dang ky|tao|gui)\b|"
    r"^xin(?:\s+cap)?\b.*\b(?:cho|giup)\s+(?:toi|minh|em|to|tao)\b|"
    r"^lam\s+(?:giup|cho)\s+(?:toi|minh|em|to|tao)\b.*\b(?:yeu cau|request|don)\b|"
    r"^yeu cau\b.*\b(?:cho|giup)\s+(?:toi|minh|em|to|tao)\b|"
    r"^cap\b.*\bcho\s+(?:toi|minh|em|to|tao)\b"
)
_INCIDENT = re.compile(
    r"\b(?:loi|khong len|khong mo|khong dung|mat ket noi|man hinh|laptop|may tinh|may in|ban phim|"
    r"wifi|wi-fi|vpn|outlook|email|app|phan mem|tai khoan|mat khau|mfa|sap|erp|virus|phishing|"
    r"roi|dam|va dap|nhap nhay|tu tat|tieng la)\b"
)
_CONDITIONAL_OR_HOLD_ACTION = re.compile(
    r"\b(?:huong dan\s+(?:toi\s+)?(?:xu ly|truoc)|neu khong duoc\s+moi\s+tao|chua\s+tao|dung\s+tao|khoan\s+tao|chua\s+can\s+tao)\b"
)
_GARBAGE = re.compile(r"^(?:\d+|[a-z]{5,}|[^\w\s]{3,})$")


def route_chat_message(message: str) -> ChatRouteDecision:
    """Choose the least expensive safe path for one chat turn."""
    folded = _fold(message).strip()
    if _GREETING.fullmatch(folded):
        return ChatRouteDecision(
            "direct_response",
            "direct",
            1.0,
            "Chào bạn! Mình có thể hỗ trợ các vấn đề IT hoặc tra cứu Knowledge Base.",
        )
    if _THANKS.fullmatch(folded):
        return ChatRouteDecision("direct_response", "direct", 1.0, "Rất sẵn lòng hỗ trợ bạn.")
    if _ACKNOWLEDGEMENT.fullmatch(folded):
        return ChatRouteDecision(
            "direct_response",
            "direct",
            1.0,
            "Được rồi. Khi cần hỗ trợ thêm, bạn cứ nhắn mình nhé.",
        )
    if _CASUAL_CHECK_IN.fullmatch(folded):
        return ChatRouteDecision(
            "direct_response",
            "direct",
            1.0,
            "Mình sẵn sàng hỗ trợ. Bạn đang cần hỗ trợ vấn đề IT nào?",
        )
    if _GARBAGE.fullmatch(folded):
        return ChatRouteDecision(
            "needs_clarification",
            "needs_clarification",
            0.98,
            "Mình chưa nhận diện được yêu cầu IT. Bạn hãy mô tả thiết bị hoặc dịch vụ đang gặp vấn đề và biểu hiện lỗi.",
        )
    if _NON_IT_SOCIAL.search(folded):
        return ChatRouteDecision(
            "needs_clarification",
            "needs_clarification",
            0.99,
            "Mình chỉ hỗ trợ các vấn đề IT. Bạn hãy mô tả thiết bị, ứng dụng hoặc dịch vụ IT cần hỗ trợ.",
        )
    if _VAGUE_INCIDENT.fullmatch(folded):
        return ChatRouteDecision(
            "needs_clarification",
            "needs_clarification",
            0.94,
            "Mình cần thêm thông tin để hỗ trợ: thiết bị hay ứng dụng nào gặp lỗi, và dấu hiệu lỗi cụ thể là gì?",
        )
    if _STATUS.search(folded) or _TICKET_REFERENCE_STATUS.search(folded):
        return ChatRouteDecision("ticket_status", "tool_required", 0.96)
    if _KNOWLEDGE_QUESTION.search(folded):
        return ChatRouteDecision("knowledge", "evidence_required", 0.88)
    if _CONDITIONAL_OR_HOLD_ACTION.search(folded) and _INCIDENT.search(folded):
        return ChatRouteDecision("incident", "evidence_required", 0.88)
    if _EXECUTION_ACTION.search(folded) or _ACTION.search(folded):
        return ChatRouteDecision("action_request", "tool_required", 0.92)
    if _INCIDENT.search(folded):
        return ChatRouteDecision("incident", "evidence_required", 0.82)
    return ChatRouteDecision("knowledge", "evidence_required", 0.70)
