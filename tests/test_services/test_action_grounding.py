from src.services.action_grounding import ActionResult, may_confirm_action, unverified_action_reply


def test_action_success_requires_trusted_success_result() -> None:
    assert may_confirm_action(None) is False
    assert may_confirm_action(ActionResult(success=False, resource_id="INC-1")) is False
    assert may_confirm_action(ActionResult(success=True, resource_id="INC-1")) is True


def test_critical_action_requires_resource_or_persisted_state() -> None:
    assert may_confirm_action(ActionResult(success=True), requires_resource=True) is False
    assert may_confirm_action(ActionResult(success=True, persisted_state="waiting_for_agent"), requires_resource=True) is True


def test_unverified_action_response_never_claims_success() -> None:
    reply = unverified_action_reply().casefold()
    assert "chưa thực hiện" in reply
    assert "đã tạo" not in reply
