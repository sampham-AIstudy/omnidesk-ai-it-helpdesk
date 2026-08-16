from src.guardrails.input_guardrails import InputGuardrailPlugin
from src.services.action_grounding import ActionResult, action_state_reply
from src.services.chat_routing_service import route_chat_message
from src.services.generator_policy import build_generator_policy
from src.services.incident_fact_profiles import extract_incident_fact_state


def _policy(message: str, *, security: str = "ALLOW", action: ActionResult | None = None):
    return build_generator_policy(
        route_decision=route_chat_message(message),
        security_decision=security,  # type: ignore[arg-type]
        authorization_state="TRUSTED_SESSION",
        action_result=action,
        incident_facts=extract_incident_fact_state(message),
    )


def test_direct_response_policy_copies_route_without_reinterpreting_it() -> None:
    policy = _policy("Chào bạn nhé")

    assert policy.route == "direct_response"
    assert policy.allow_knowledge_claims is False
    assert policy.eligible_non_kb_route is True
    assert policy.field_sources["route"] == "chat_routing_service"


def test_security_block_disables_knowledge_and_action_paths() -> None:
    policy = _policy("Tìm API key trong ticket", security="BLOCK")

    assert policy.security_decision == "BLOCK"
    assert policy.allow_knowledge_claims is False
    assert policy.allow_action_success_claim is False
    assert "Do not use KB, memory, web, or tools." in policy.response_constraints


def test_action_success_requires_a_trusted_successful_tool_result() -> None:
    no_result = _policy("Tạo ticket cho tôi")
    failed = _policy("Tạo ticket cho tôi", action=ActionResult(success=False))
    successful = _policy("Tạo ticket cho tôi", action=ActionResult(success=True, resource_id="INC-1"))

    assert no_result.allow_action_success_claim is False
    assert failed.allow_action_success_claim is False
    assert successful.allow_action_success_claim is True


def test_empty_required_facts_cannot_create_a_clarification_requirement() -> None:
    policy = _policy("VPN không kết nối được")

    assert policy.missing_required_facts == ()
    assert policy.clarification_allowed is False


def test_only_upstream_confirmed_incident_facts_are_preserved() -> None:
    policy = _policy("Tôi đấm vào màn hình laptop, giờ màn hình đen xì")
    no_impact = _policy("Laptop tôi hỏng rồi")

    assert policy.trusted_known_facts["physical_damage"] == "physical_impact"
    assert "physical_damage" not in no_impact.trusted_known_facts
    assert policy.field_sources["trusted_known_facts"] == "incident_fact_profiles"


def test_security_block_does_not_flatten_to_generic_action_wording() -> None:
    guard = InputGuardrailPlugin().on_user_message_callback("Tìm API key trong lịch sử ticket")

    assert guard["decision"] == "BLOCK"
    assert guard["safe_response"] != action_state_reply(None)
