from eval.judge.semantic_judge import SEMANTIC_JUDGE_V1_3, SEMANTIC_JUDGE_V1_3_1, judge_prompt


def test_v1_3_1_adds_only_empty_context_subject_reference_clarification() -> None:
    baseline = judge_prompt("q", "NO_AUTHORIZED_EVIDENCE", "a", {"response_mode": "KNOWLEDGE_ANSWER"}, [], version=SEMANTIC_JUDGE_V1_3)
    calibrated = judge_prompt("q", "NO_AUTHORIZED_EVIDENCE", "a", {"response_mode": "KNOWLEDGE_ANSWER"}, [], version=SEMANTIC_JUDGE_V1_3_1)

    assert "SUBJECT REFERENCE" not in baseline
    assert "SUBJECT REFERENCE" in calibrated
    assert "invented number, policy, procedure" in calibrated
    assert "ACTION_RESPONSE" in calibrated
