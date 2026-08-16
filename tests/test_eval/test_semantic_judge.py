import asyncio
import json

import httpx
import pytest

from eval.judge.semantic_judge import (
    SEMANTIC_JUDGE_V1_3,
    JudgeResult,
    SemanticJudgeAdapter,
    final_pass_decision,
    judge_prompt,
    parse_judge_output,
)

VALID = {
    "faithfulness": 1.0, "completeness": 1.0, "relevance": 1.0,
    "correct_abstention": 1.0, "citation_correctness": 1.0, "pass": True,
    "failure_types": [], "unsupported_claims": [], "missing_points": [], "brief_rationale": "Supported.",
}


def response(payload, status=200):
    return httpx.Response(status, json=payload)


def make_adapter(transport, tmp_path):
    async def no_sleep(_):
        return None
    return SemanticJudgeAdapter(base_url="https://judge.invalid/v1", api_key="test", model="judge", transport=transport, cache_dir=tmp_path, sleeper=no_sleep)


def call(adapter, refresh=False):
    return asyncio.run(adapter.judge("q", "context", "answer", {"route": "knowledge_rag"}, ["kb-1"], refresh=refresh))


def test_parse_valid_and_fenced_json():
    assert parse_judge_output(json.dumps(VALID)).passed
    assert parse_judge_output("```json\n" + json.dumps(VALID) + "\n```").faithfulness == 1.0


def test_parse_malformed_or_missing_or_out_of_range_rejected():
    with pytest.raises(ValueError):
        parse_judge_output("not json")
    malformed = dict(VALID)
    malformed.pop("relevance")
    with pytest.raises(ValueError):
        parse_judge_output(json.dumps(malformed))
    malformed = dict(VALID)
    malformed["faithfulness"] = 1.1
    with pytest.raises(ValueError):
        parse_judge_output(json.dumps(malformed))


def test_429_retries_then_succeeds(tmp_path):
    calls = []
    async def transport(_):
        calls.append(1)
        return response({"error": "rate"}, 429) if len(calls) == 1 else response({"choices": [{"message": {"content": json.dumps(VALID)}}]})
    result = call(make_adapter(transport, tmp_path))
    assert result.successful and len(calls) == 2
    assert result.observations[0].infra_error_type == "HTTP_429"


def test_500_retries_and_401_does_not(tmp_path):
    five_calls = []
    async def transient(_):
        five_calls.append(1)
        return response({"error": "x"}, 500) if len(five_calls) < 3 else response({"choices": [{"message": {"content": json.dumps(VALID)}}]})
    assert call(make_adapter(transient, tmp_path)).successful and len(five_calls) == 3
    forbidden_calls = []

    async def permanent(_):
        forbidden_calls.append(1)
        return response({"error": "auth"}, 401)

    result = call(make_adapter(permanent, tmp_path / "auth"))
    assert result.infra_error_type == "HTTP_401_403" and len(forbidden_calls) == 1


def test_timeout_max_retry_and_success_cache(tmp_path):
    calls = []

    async def timeout(_):
        calls.append(1)
        raise httpx.ReadTimeout("late")

    result = call(make_adapter(timeout, tmp_path))
    assert result.infra_error_type == "TIMEOUT" and len(calls) == 3
    fresh_calls = []

    async def valid(_):
        fresh_calls.append(1)
        return response({"choices": [{"message": {"content": json.dumps(VALID)}}]})

    adapter = make_adapter(valid, tmp_path / "cache")
    assert call(adapter).successful
    cached = call(adapter)
    assert cached.cache_hit and len(fresh_calls) == 1


def test_schema_and_invalid_json_are_infra_errors(tmp_path):
    bad_schema = dict(VALID)
    bad_schema.pop("pass")
    calls = []

    async def invalid(_):
        calls.append(1)
        return response({"choices": [{"message": {"content": json.dumps(bad_schema)}}]})

    result = call(make_adapter(invalid, tmp_path))
    assert result.infra_error_type == "SCHEMA_MISMATCH" and len(calls) == 2
    raw_calls = []

    async def malformed(_):
        raw_calls.append(1)
        return response({"choices": [{"message": {"content": "{"}}]})

    result = call(make_adapter(malformed, tmp_path / "raw"))
    assert result.infra_error_type == "TRUNCATED_RESPONSE" and len(raw_calls) == 2


def test_v1_3_is_route_aware_and_keeps_short_safe_responses_complete():
    prompt = judge_prompt("q", "context", "answer", {"response_mode": "SECURITY_REFUSAL"}, [], version=SEMANTIC_JUDGE_V1_3)
    assert "SECURITY_REFUSAL" in prompt
    assert "concise safe refusal is complete" in prompt
    assert "PARTIAL_ANSWER" in prompt


def test_final_pass_has_non_compensatory_hallucination_hard_gate():
    result = JudgeResult(0.0, 1.0, 1.0, 1.0, 1.0, False, ["HALLUCINATION"], ["false fact"], [], "Unsupported material claim.")
    decision = final_pass_decision(result)
    assert not decision["passed"]
    assert decision["decision"] == "HARD_GATE"
    assert decision["hard_gates"] == ["HALLUCINATION"]


def test_final_pass_rejects_incorrect_refusal_without_averaging_scores():
    result = JudgeResult(1.0, 0.5, 1.0, 0.0, 1.0, False, ["INCORRECT_REFUSAL"], [], ["supported answer"], "Refused supported evidence.")
    decision = final_pass_decision(result)
    assert not decision["passed"]
    assert decision["decision"] == "SEMANTIC_FAILURE"


def test_gt_041_schema_behavior_retries_once_then_records_valid_result(tmp_path):
    """GT-041 was the historical schema-error case; retry stays bounded."""
    calls = []
    invalid = dict(VALID)
    invalid.pop("missing_points")

    async def transport(_):
        calls.append(1)
        content = json.dumps(invalid if len(calls) == 1 else VALID)
        return response({"choices": [{"message": {"content": content}}]})

    result = call(make_adapter(transport, tmp_path))
    assert result.successful
    assert len(calls) == 2
    assert result.observations[0].infra_error_type == "SCHEMA_MISMATCH"
    assert result.observations[1].schema_status == "OK"
