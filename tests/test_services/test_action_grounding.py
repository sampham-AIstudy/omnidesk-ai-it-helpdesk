from src.services.action_grounding import (
    ActionExecutionState,
    ActionResult,
    action_execution_state,
    action_state_reply,
    allowed_action_facts,
    may_confirm_action,
    unverified_action_reply,
)


def test_action_success_requires_trusted_success_result() -> None:
    assert may_confirm_action(None) is False
    assert may_confirm_action(ActionResult(success=False, resource_id="INC-1")) is False
    assert may_confirm_action(ActionResult(success=True, resource_id="INC-1")) is True


def test_critical_action_requires_resource_or_persisted_state() -> None:
    assert may_confirm_action(ActionResult(success=True), requires_resource=True) is False
    assert may_confirm_action(ActionResult(success=True, persisted_state="waiting_for_agent"), requires_resource=True) is True


def test_unverified_action_response_never_claims_success() -> None:
    reply = unverified_action_reply().casefold()
    assert reply == "chưa có thay đổi nào được thực hiện."
    assert all(term not in reply for term in ("workflow", "phê duyệt", "phân quyền", "xác nhận"))


def test_not_invoked_projects_only_no_change_executed() -> None:
    assert action_execution_state(None) is ActionExecutionState.NOT_INVOKED
    assert allowed_action_facts(None) == {"executed": False}
    assert action_state_reply(None) == "Chưa có thay đổi nào được thực hiện."


def test_failed_action_only_exposes_allowlisted_error_detail() -> None:
    unknown = ActionResult(success=False, error_code="DATABASE_TIMEOUT")
    closed = ActionResult(success=False, error_code="TICKET_ALREADY_CLOSED")

    assert action_execution_state(unknown) is ActionExecutionState.FAILED
    assert allowed_action_facts(unknown) == {"executed": False, "error_code": "DATABASE_TIMEOUT"}
    assert action_state_reply(unknown) == "Thao tác chưa hoàn tất."
    assert action_state_reply(closed) == "Thao tác chưa hoàn tất. Ticket đã ở trạng thái đóng."


def test_success_response_projects_only_returned_resource_and_state() -> None:
    result = ActionResult(success=True, resource_id="INC-1234", persisted_state="waiting_for_agent")

    assert action_execution_state(result) is ActionExecutionState.SUCCEEDED
    assert allowed_action_facts(result) == {
        "executed": True,
        "resource_id": "INC-1234",
        "persisted_state": "waiting_for_agent",
    }
    assert action_state_reply(result) == "Đã cập nhật INC-1234 sang trạng thái waiting_for_agent."
