"""Single confirmation contract for mutating Help Desk actions."""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

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
