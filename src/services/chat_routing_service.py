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


_GREETING = re.compile(r"^(?:xin )?(?:chao|hello|hi|hey)(?: ban| chat| bot)?(?: nhe| a| ah)?[!., ]*$")
_THANKS = re.compile(r"^(?:cam on|thanks|thank you)(?: ban)?(?: nhe| a| ah)?[!., ]*$")
_ACKNOWLEDGEMENT = re.compile(
    r"^(?:(?:ok|oke|okay|da|vâng|vang)(?: hieu roi)?|da hieu|hieu roi|ro roi|duoc roi)[!., ]*$"
)
_DEFERRAL = re.compile(
    r"^(?:thoi de sau|de sau nhe|de sau|luc khac|khi khac|khong can nua|de luc khac)[!., ]*$"
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
_SOCIAL_DIRECT = re.compile(
    r"^(?:"
    r"(?:xin )?(?:chao|hello|hi|hey)(?: (?:ban|chat|bot|tro ly(?: it)?|doi it|helpdesk|team|buoi sang))?"
    r"|xin chao,? toi chi muon chao"
    r"|good (?:morning|afternoon)"
    r"|(?:cam on|thanks|thank you)(?: (?:ban|doi ho tro|da phan hoi|ban nhieu))?(?: nhe| a| ah)?"
    r"|cam on ban da ho tro"
    r"|chuc (?:ban )?(?:mot )?ngay tot lanh"
    r"|hen gap lai|tam biet"
    r"|(?:ok|oke|okay|da|u|vang)(?: hieu roi| roi)?|da hieu|hieu roi|ro roi|duoc roi"
    r"|thoi de sau|de sau nhe|de sau|luc khac|khi khac|khong can nua|de luc khac"
    r"|(?:ban )?co ranh khong|(?:toi nay )?ban khoe chu|ban ten gi"
    r"|ban co the (?:tro chuyen|noi chuyen) (?:mot chut|it) khong"
    r")[!?,. ]*$"
)
_TECHNICAL_SIGNAL = re.compile(
    r"\b(?:vpn|wifi|wi-fi|dns|bitlocker|outlook|mfa|forticlient|sap|erp|"
    r"tcp|http|port|timeout|timed out|0x[0-9a-f]+|khong ket noi|mat mang|"
    r"khong mo|khong vao|khong dang nhap|mat ket noi|tu tat|nhap nhay|man hinh den)\b"
)
_NOISE_OR_EMPTY_CONTENT = re.compile(
    r"\b(?:asdf|qwer|lorem|ipsum|test|khong biet go gi|bam nham|gui nham|"
    r"khong co noi dung|ky tu la|mot hai ba bon)\b"
)
_UNDERSPECIFIED_INCIDENT = re.compile(
    r"(?:"
    r"\b(?:may(?: tinh)?|he thong|ung dung|app|mang|tai khoan|man hinh|email|cai nay|no|su co|it)\b"
    r".*\b(?:co van de|bi sao|bi gi do|hong roi|khong on|ky lam|cham qua|"
    r"khong chay|loi|cuu toi|gap)\b"
    r"|^(?:khong the thao tac|giup toi voi|toi khong lam viec duoc)[!., ]*$"
    r")"
)


def _is_uninterpretable(folded: str) -> bool:
    """Return true only when no usable technical or task signal is present."""
    if _TECHNICAL_SIGNAL.search(folded):
        return False
    if _GARBAGE.fullmatch(folded) or _NOISE_OR_EMPTY_CONTENT.search(folded):
        return True
    tokens = re.findall(r"[a-z0-9]+", folded)
    return not tokens or len(tokens) == 1


def _is_underspecified_incident(folded: str) -> bool:
    """Potential incidents need an object plus a concrete failure signal."""
    return not _TECHNICAL_SIGNAL.search(folded) and bool(_UNDERSPECIFIED_INCIDENT.search(folded))


def route_chat_message(message: str) -> ChatRouteDecision:
    """Choose the least expensive safe path for one chat turn."""
    folded = _fold(message).strip()
    # Explicit conversational topic shifts must not inherit a previous IT turn.
    if _SOCIAL_DIRECT.fullmatch(folded):
        return ChatRouteDecision(
            "direct_response",
            "direct",
            1.0,
            "Mình sẵn sàng hỗ trợ khi bạn cần.",
        )
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
    if _DEFERRAL.fullmatch(folded):
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
    if _is_uninterpretable(folded):
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
    if _is_underspecified_incident(folded):
        return ChatRouteDecision(
            "needs_clarification",
            "needs_clarification",
            0.94,
            "Mình cần thêm thông tin để hỗ trợ: thiết bị hay ứng dụng nào gặp lỗi, và dấu hiệu lỗi cụ thể là gì?",
        )
    if _INCIDENT.search(folded):
        return ChatRouteDecision("incident", "evidence_required", 0.82)
    return ChatRouteDecision("knowledge", "evidence_required", 0.70)
