from pathlib import Path

from src.services.action_grounding import ActionResult
from src.services.chat_routing_service import route_chat_message
from src.services.generator_policy import build_generator_policy
from src.services.incident_fact_profiles import extract_incident_fact_state


def test_policy_has_no_response_planner_dependency() -> None:
    service_source = Path("src/services/generator_policy.py").read_text(encoding="utf-8")
    runtime_source = Path("src/api/chat.py").read_text(encoding="utf-8")

    assert "chat_response_planning" not in service_source
    assert "chat_response_planning" not in runtime_source
    assert "build_response_plan" not in runtime_source


def test_policy_does_not_reclassify_route_or_add_unknown_facts() -> None:
    message = "Laptop tôi hỏng rồi"
    route = route_chat_message(message)
    policy = build_generator_policy(
        route_decision=route,
        security_decision="ALLOW",
        authorization_state="TRUSTED_SESSION",
        incident_facts=extract_incident_fact_state(message),
    )

    assert policy.route == route.route
    assert "physical_damage" not in policy.trusted_known_facts
    assert "requested_parts" not in policy.as_dict()
    assert "coverage_mode" not in policy.as_dict()


def test_untrusted_action_state_never_allows_success_language() -> None:
    route = route_chat_message("Tạo ticket cho tôi")
    policy = build_generator_policy(
        route_decision=route,
        security_decision="ALLOW",
        authorization_state="TRUSTED_SESSION",
        action_result=ActionResult(success=False),
    )

    assert policy.tool_success is False
    assert policy.allow_action_success_claim is False
