"""Single confirmation contract for mutating Help Desk actions."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from src.observability.tracing import operation, record_tool_result


class ActionExecutionState(StrEnum):
    """Only states proved by a trusted tool result."""

    NOT_INVOKED = "NOT_INVOKED"
    FAILED = "FAILED"
    SUCCEEDED = "SUCCEEDED"


@dataclass(frozen=True)
class ActionResult:
    success: bool
    resource_id: str | None = None
    persisted_state: str | None = None
    error_code: str | None = None


def action_execution_state(result: ActionResult | None) -> ActionExecutionState:
    if result is None:
        return ActionExecutionState.NOT_INVOKED
    return ActionExecutionState.SUCCEEDED if result.success else ActionExecutionState.FAILED


def allowed_action_facts(result: ActionResult | None) -> dict[str, str | bool]:
    """Project a tool result to exactly the facts a response may claim."""
    state = action_execution_state(result)
    if state is ActionExecutionState.NOT_INVOKED:
        return {"executed": False}
    if state is ActionExecutionState.FAILED:
        facts: dict[str, str | bool] = {"executed": False}
        if result and result.error_code:
            facts["error_code"] = result.error_code
        return facts

    facts = {"executed": True}
    if result and result.resource_id:
        facts["resource_id"] = result.resource_id
    if result and result.persisted_state:
        facts["persisted_state"] = result.persisted_state
    return facts


_SAFE_ERROR_MESSAGES = {
    "TICKET_ALREADY_CLOSED": "Ticket đã ở trạng thái đóng.",
}


def action_state_reply(result: ActionResult | None) -> str:
    """Render only tool-proven action state; never infer process explanations."""
    state = action_execution_state(result)
    success = state is ActionExecutionState.SUCCEEDED
    with operation("ai.tool", {"ai.tool.name": "action_state_renderer", "ai.tool.success": success}):
        record_tool_result("action_state_renderer", success)
        if state is ActionExecutionState.NOT_INVOKED:
            return "Chưa có thay đổi nào được thực hiện."
        if state is ActionExecutionState.FAILED:
            safe_error = _SAFE_ERROR_MESSAGES.get(result.error_code or "") if result else None
            return f"Thao tác chưa hoàn tất. {safe_error}" if safe_error else "Thao tác chưa hoàn tất."

        assert result is not None
        if result.resource_id and result.persisted_state:
            return f"Đã cập nhật {result.resource_id} sang trạng thái {result.persisted_state}."
        if result.resource_id:
            return f"Đã hoàn tất thao tác với {result.resource_id}."
        if result.persisted_state:
            return f"Đã cập nhật trạng thái thành {result.persisted_state}."
        return "Thao tác đã hoàn tất."


def may_confirm_action(result: ActionResult | None, *, requires_resource: bool = False) -> bool:
    """Only trusted successful tool output may authorize a success statement."""
    if result is None or not result.success:
        return False
    return not requires_resource or bool(result.resource_id or result.persisted_state)


def unverified_action_reply() -> str:
    """Compatibility alias for a routed request with no tool invocation."""
    return action_state_reply(None)


# Workspace Chat has no mutating handoff tool. Keep this detection beside the
# trusted action-state contract so untrusted conversation text can never be
# mistaken for a successful workflow result.
_WORKSPACE_HANDOFF_TARGET = re.compile(
    r"(?:k(?:ỹ|y) thuật viên|chuyên viên(?: it)?|nhân viên hỗ trợ|"
    r"người hỗ trợ|người thật|con người|human (?:agent|support))",
    re.IGNORECASE,
)
_WORKSPACE_HANDOFF_INTENT = re.compile(
    r"(?:gặp|chuyển(?: tôi)?|escalat(?:e|ion)?|handoff|transfer|"
    r"cần|muốn|yêu cầu|đã chuyển|đã escalat(?:e|ion)?)",
    re.IGNORECASE,
)


def workspace_handoff_not_invoked_reply(message: str) -> str | None:
    """Return the canonical safe reply for a handoff request in Workspace Chat.

    A Workspace Chat turn has no authoritative ticket/workflow mutation. This
    gate runs before retrieval or generation, including streaming, so a model
    cannot emit a handoff success claim that would later need to be corrected.
    """
    normalized = " ".join(message.split())
    has_target = bool(_WORKSPACE_HANDOFF_TARGET.search(normalized))
    has_explicit_confirmation = bool(
        re.search(r"(?:đã\s+)?(?:chuyển|escalat(?:e|ion)?|handoff|transfer)\s+(?:tôi|mình|em|tớ)", normalized, re.IGNORECASE)
    )
    has_direct_handoff_request = bool(
        re.search(r"\b(?:escalate|handoff|transfer)\b", normalized, re.IGNORECASE)
    )
    if not (
        (has_target and _WORKSPACE_HANDOFF_INTENT.search(normalized))
        or has_explicit_confirmation
        or has_direct_handoff_request
    ):
        return None

    return (
        f"{action_state_reply(None)} Workspace Chat không thể tự chuyển bạn cho kỹ thuật viên. "
        "Để nhận hỗ trợ, hãy tạo Incident Ticket hoặc mở ticket hiện có rồi dùng chức năng Yêu cầu kỹ thuật viên."
    )


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(char for char in decomposed if unicodedata.category(char) != "Mn").replace("đ", "d")


_HOLD_PATTERNS = [
    r"\b(?:dung|khong|chua|khoan)\s+(?:tao|thuc hien|gui|lam|mo)\s+(?:gi|ticket|don|yeu cau|request)?\b.*(?:cho den khi|khi chua|truoc khi|cho toi)?.*(?:xac nhan|dong y|confirm)",
    r"\b(?:nhung|tuy nhien)?\s*(?:dung|chua|khoan)\s+tao\s+gi\b",
    r"\bchua\s+tao\s+(?:gi|ticket|don|yeu cau)\b",
    r"\bcho\s+(?:khi\s+)?(?:toi|minh|em)\s+xac nhan\b",
]


def is_hold_requested(message: str) -> bool:
    """Return True if the user explicitly requested holding mutations until confirmation."""
    folded = _fold(" ".join(message.split()))
    return any(re.search(p, folded, re.IGNORECASE) for p in _HOLD_PATTERNS)


def parse_multi_intents(message: str) -> list[dict[str, str]]:
    """Identify distinct intents (Incidents, Service Requests, Access Requests) in a composite turn."""
    folded = _fold(" ".join(message.split()))
    intents: list[dict[str, str]] = []

    # 1. Incident Intents
    if re.search(r"\bvpn\b.*(?:loi|hong|failed|khong|authentication|khong vao|mat ket noi)", folded):
        intents.append({
            "key": "incident_vpn",
            "title": "Sự cố kỹ thuật (Incident)",
            "detail": "Sự cố kết nối / lỗi VPN",
        })
    elif re.search(r"\b(?:wifi|wi-fi|mang|internet)\b.*(?:loi|hong|chap chon|khong|rot)", folded):
        intents.append({
            "key": "incident_network",
            "title": "Sự cố kỹ thuật (Incident)",
            "detail": "Sự cố mạng / Wi-Fi",
        })
    elif re.search(r"\b(?:laptop|may tinh|pc|man hinh|ban phim|chuot)\b.*(?:loi|hong|va dap|roi|rot|den|vo|nut)", folded):
        intents.append({
            "key": "incident_hardware",
            "title": "Sự cố kỹ thuật (Incident)",
            "detail": "Sự cố phần cứng thiết bị",
        })
    elif re.search(r"\b(?:outlook|teams|email|app|phan mem|sap|erp)\b.*(?:loi|hong|khong vao|crash)", folded):
        intents.append({
            "key": "incident_software",
            "title": "Sự cố kỹ thuật (Incident)",
            "detail": "Sự cố ứng dụng / phần mềm",
        })

    # 2. Service Request: Hardware
    if re.search(r"\b(?:xin|cap|can|yeu cau|dang ky)\b.*\b(?:laptop|may tinh|pc)\b(?:\s+(?:moi|thay the))?", folded):
        intents.append({
            "key": "sr_laptop",
            "title": "Yêu cầu dịch vụ (Service Request)",
            "detail": "Yêu cầu cấp laptop mới",
        })
    elif re.search(r"\b(?:xin|cap|can|yeu cau|dang ky)\b.*\b(?:may in|man hinh|ban phim|chuot|tai nghe|thiet bi ngoai vi)\b", folded):
        intents.append({
            "key": "sr_peripheral",
            "title": "Yêu cầu dịch vụ (Service Request)",
            "detail": "Yêu cầu thiết bị ngoại vi",
        })

    # 3. Access Request / Permissions
    if re.search(r"(?:(?:quyen|xin quyen|truy cap|xin)\b.*\b(?:git|repo|repository|github|gitlab)\b|\b(?:git|repo|repository|github|gitlab)\b.*(?:read-only|read\s+only|access|quyen|write)|\bquyen\s+git\b)", folded):
        is_ro = "read-only" in folded or "read only" in folded
        detail_suffix = " (read-only)" if is_ro else ""
        intents.append({
            "key": "access_git",
            "title": "Yêu cầu quyền truy cập (Access Request)",
            "detail": f"Yêu cầu quyền truy cập Git repository{detail_suffix}",
        })
    elif re.search(r"\b(?:xin|cap|dang ky)\b.*\bquyen\s+vpn\b", folded):
        intents.append({
            "key": "access_vpn",
            "title": "Yêu cầu quyền truy cập (Access Request)",
            "detail": "Yêu cầu cấp quyền VPN",
        })
    elif re.search(r"\b(?:xin|cap|dang ky)\b.*\bquyen\s+(?:db|database|csdl)\b", folded):
        intents.append({
            "key": "access_db",
            "title": "Yêu cầu quyền truy cập (Access Request)",
            "detail": "Yêu cầu cấp quyền Database",
        })

    # 4. Software License
    if re.search(r"\b(?:xin|cap|cai|dang ky)\b.*\b(?:license|m365|office|phan mem)\b", folded):
        intents.append({
            "key": "sr_software",
            "title": "Yêu cầu dịch vụ (Service Request)",
            "detail": "Yêu cầu cấp bản quyền / cài đặt phần mềm",
        })

    return intents


def multi_intent_hold_reply(
    message: str,
    recent_history: list[Any] | None = None,
) -> str | None:
    """Return structured hold response recognizing all intents without executing mutations."""
    texts: list[str] = []
    if recent_history:
        for m in recent_history:
            content = getattr(m, "content", None) or (m.get("content") if isinstance(m, dict) else None)
            role = getattr(m, "role", None) or (m.get("role") if isinstance(m, dict) else None)
            if role == "user" and content:
                texts.append(content)
    texts.append(message)
    combined = " ".join(texts)

    if not is_hold_requested(message) and not is_hold_requested(combined):
        return None

    intents = parse_multi_intents(combined)
    if len(intents) < 2:
        return None

    intent_summary = "\n".join(f"{i+1}. {item['title']}: {item['detail']}" for i, item in enumerate(intents))
    return (
        f"Tôi đã ghi nhận {len(intents)} yêu cầu của bạn:\n\n"
        f"{intent_summary}\n\n"
        f"Chưa có thay đổi nào được thực hiện theo yêu cầu chờ xác nhận của bạn.\n"
        f"Vui lòng xác nhận nếu bạn muốn tôi tiến hành tạo Incident cho sự cố kỹ thuật và khởi tạo các Service Request tương ứng."
    )
