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
    r"^(?:(?:hay|vui long)\s+)?(?:tao|gui|dang ky)\b|"
    r"^(?:toi|minh|em)\s+(?:muon|can)\s+(?:xin|dang ky|tao|gui)\b|"
    r"^xin(?:\s+cap)?\b.*\b(?:cho|giup)\s+(?:toi|minh|em|to)\b|"
    r"^lam\s+(?:giup|cho)\s+(?:toi|minh|em)\b.*\b(?:yeu cau|request|don)\b|"
    r"^yeu cau\b.*\b(?:cho|giup)\s+(?:toi|minh|em)\b|"
    r"^cap\b.*\bcho\s+(?:toi|minh|em)\b"
)
_INCIDENT = re.compile(
    r"\b(?:loi|khong len|khong mo|khong dung|mat ket noi|man hinh|laptop|may tinh|may in|ban phim|"
    r"wifi|wi-fi|vpn|outlook|email|app|phan mem|tai khoan|mat khau|mfa|sap|erp|virus|phishing|"
    r"roi|dam|va dap|nhap nhay|tu tat|tieng la)\b"
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
            "Ch\u00e0o b\u1ea1n! M\u00ecnh c\u00f3 th\u1ec3 h\u1ed7 tr\u1ee3 c\u00e1c v\u1ea5n \u0111\u1ec1 IT ho\u1eb7c tra c\u1ee9u Knowledge Base.",
        )
    if _THANKS.fullmatch(folded):
        return ChatRouteDecision("direct_response", "direct", 1.0, "R\u1ea5t s\u1eb5n l\u00f2ng h\u1ed7 tr\u1ee3 b\u1ea1n.")
    if _ACKNOWLEDGEMENT.fullmatch(folded):
        return ChatRouteDecision(
            "direct_response",
            "direct",
            1.0,
            "\u0110\u01b0\u1ee3c r\u1ed3i. Khi c\u1ea7n h\u1ed7 tr\u1ee3 th\u00eam, b\u1ea1n c\u1ee9 nh\u1eafn m\u00ecnh nh\u00e9.",
        )
    if _CASUAL_CHECK_IN.fullmatch(folded):
        return ChatRouteDecision(
            "direct_response",
            "direct",
            1.0,
            "M\u00ecnh s\u1eb5n s\u00e0ng h\u1ed7 tr\u1ee3. B\u1ea1n \u0111ang c\u1ea7n h\u1ed7 tr\u1ee3 v\u1ea5n \u0111\u1ec1 IT n\u00e0o?",
        )
    if _GARBAGE.fullmatch(folded):
        return ChatRouteDecision(
            "needs_clarification",
            "needs_clarification",
            0.98,
            "M\u00ecnh ch\u01b0a nh\u1eadn di\u1ec7n \u0111\u01b0\u1ee3c y\u00eau c\u1ea7u IT. B\u1ea1n h\u00e3y m\u00f4 t\u1ea3 thi\u1ebft b\u1ecb ho\u1eb7c d\u1ecbch v\u1ee5 \u0111ang g\u1eb7p v\u1ea5n \u0111\u1ec1 v\u00e0 bi\u1ec3u hi\u1ec7n l\u1ed7i.",
        )
    if _NON_IT_SOCIAL.search(folded):
        return ChatRouteDecision(
            "needs_clarification",
            "needs_clarification",
            0.99,
            "M\u00ecnh ch\u1ec9 h\u1ed7 tr\u1ee3 c\u00e1c v\u1ea5n \u0111\u1ec1 IT. B\u1ea1n h\u00e3y m\u00f4 t\u1ea3 thi\u1ebft b\u1ecb, \u1ee9ng d\u1ee5ng ho\u1eb7c d\u1ecbch v\u1ee5 IT c\u1ea7n h\u1ed7 tr\u1ee3.",
        )
    if _VAGUE_INCIDENT.fullmatch(folded):
        return ChatRouteDecision(
            "needs_clarification",
            "needs_clarification",
            0.94,
            "M\u00ecnh c\u1ea7n th\u00eam th\u00f4ng tin \u0111\u1ec3 h\u1ed7 tr\u1ee3: thi\u1ebft b\u1ecb hay \u1ee9ng d\u1ee5ng n\u00e0o g\u1eb7p l\u1ed7i, v\u00e0 d\u1ea5u hi\u1ec7u l\u1ed7i c\u1ee5 th\u1ec3 l\u00e0 g\u00ec?",
        )
    if _STATUS.search(folded) or _TICKET_REFERENCE_STATUS.search(folded):
        return ChatRouteDecision("ticket_status", "tool_required", 0.96)
    if _KNOWLEDGE_QUESTION.search(folded):
        return ChatRouteDecision("knowledge", "evidence_required", 0.88)
    if _EXECUTION_ACTION.search(folded) or _ACTION.search(folded):
        return ChatRouteDecision("action_request", "tool_required", 0.92)
    if _INCIDENT.search(folded):
        return ChatRouteDecision("incident", "evidence_required", 0.82)
    return ChatRouteDecision("knowledge", "evidence_required", 0.70)
