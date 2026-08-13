"""Single confirmation contract for mutating Help Desk actions."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ActionResult:
    success: bool
    resource_id: str | None = None
    persisted_state: str | None = None


def may_confirm_action(result: ActionResult | None, *, requires_resource: bool = False) -> bool:
    """Only trusted successful tool output may authorize a success statement."""
    if result is None or not result.success:
        return False
    return not requires_resource or bool(result.resource_id or result.persisted_state)


def unverified_action_reply() -> str:
    """Stable wording for a routed request before a workflow tool runs."""
    return (
        "Yêu cầu này cần được thực hiện qua workflow ticket có xác nhận và phân quyền phù hợp. "
        "Mình chưa thực hiện thay đổi nào."
    )
