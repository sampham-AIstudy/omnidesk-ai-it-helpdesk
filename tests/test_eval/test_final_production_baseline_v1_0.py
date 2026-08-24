from eval.final_production_baseline_v1_0 import (
    ALL_ROUTE_ASSERTION_IDS,
    CANONICAL_ROUTING_IDS,
    active_response,
    route_assertion,
    security_failure,
    trusted_tool_results_for_path,
)


def test_final_baseline_routes_non_retrieval_actions_through_accepted_grounding() -> None:
    answer, path, generation_ms, model = active_response("Tạo ticket giúp tôi.", [])

    assert path == "action_grounding"
    assert generation_ms == 0
    assert model == "none"
    assert "Chưa có thay đổi" in answer


def test_final_baseline_keeps_canonical_and_extra_route_denominators_explicit() -> None:
    assert len(CANONICAL_ROUTING_IDS) == 21
    assert len(ALL_ROUTE_ASSERTION_IDS) == 22
    assert route_assertion({"id": "unit", "query": "Chào bạn", "expected_route": "direct_response", "should_retrieve": False})["passed"]


def test_security_reporting_does_not_treat_safe_secret_refusal_as_leak() -> None:
    case = {"type": "prompt_injection_rag_security"}
    safe_refusal = {"response_path": "security_guardrail", "answer": "I cannot disclose an API key or password."}
    leaked_value = {"response_path": "generator", "answer": "API key: sk-live-abcdefghijk"}

    assert not security_failure(case, safe_refusal)
    assert security_failure(case, leaked_value)


def test_action_grounding_exposes_only_trusted_not_invoked_state_to_judge() -> None:
    assert trusted_tool_results_for_path("action_grounding") == [{"action_execution_state": "NOT_INVOKED", "executed": False}]
    assert trusted_tool_results_for_path("generator_control_template") == []
