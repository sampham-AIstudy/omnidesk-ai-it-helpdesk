from eval.baseline_v1 import (
    FAILURES,
    deterministic_generation_checks,
    evaluate_clarification,
    evaluate_partial_answer,
    layer_membership,
    route_result,
)


def test_failure_taxonomy_is_controlled() -> None:
    assert "HALLUCINATION" in FAILURES
    assert "SECRET_LEAK" in FAILURES
    assert "unknown" not in FAILURES


def test_partial_evidence_answers_supported_part_and_abstains_for_missing_part() -> None:
    answer = "VPN dùng cổng 443. Thông tin được cung cấp hiện chưa đủ để xác định chính sách khóa account."
    assert evaluate_partial_answer(answer) == []


def test_partial_evidence_rejects_full_refusal_and_hallucinated_lockout_threshold() -> None:
    assert "INCORRECT_REFUSAL" in evaluate_partial_answer("Chưa đủ thông tin để trả lời.")
    assert "HALLUCINATION" in evaluate_partial_answer("VPN dùng cổng 443 và account khóa sau 5 lần.")


def test_generation_checks_detect_invalid_citation_duplicate_and_ungrounded_action() -> None:
    checks, failures = deterministic_generation_checks(
        {}, "Tạo ticket thành công [KB-999] [kb-001] [kb-001]", [{"doc_id": "kb-001", "content": "x", "metadata": {}}]
    )
    assert checks["invalid_citation_ids"] == ["KB-999"]
    assert {"CITATION_ERROR", "TOOL_GROUNDING_ERROR"} <= set(failures)


def test_clarifier_does_not_repeat_known_physical_impact_facts() -> None:
    result = evaluate_clarification(
        "Bạn có thể cho biết mã tài sản hoặc serial để kỹ thuật viên kiểm tra không?",
        {"device": "laptop", "symptom": "black_screen", "cause": "physical_impact", "temporal_relation": "immediate"}, [],
    )
    assert result["redundant_question_count"] == 0


def test_clarifier_flags_repeated_known_facts() -> None:
    result = evaluate_clarification(
        "Thiết bị nào bị rơi? Có va đập không và xảy ra sau khi rơi không?",
        {"device": "laptop", "symptom": "black_screen", "cause": "physical_impact", "temporal_relation": "immediate"}, [],
    )
    assert result["redundant_question_count"] >= 3


def test_routing_result_and_layer_membership_are_separated() -> None:
    case = {"id": "x", "query": "Chào bạn nhé", "expected_route": "direct_response", "should_retrieve": False, "type": "small_talk"}
    actual, failures, status = route_result(case)
    assert actual["route"] == "direct_response"
    assert failures == [] and status == "PASS"
    assert layer_membership(case) == ["routing", "generation"]
