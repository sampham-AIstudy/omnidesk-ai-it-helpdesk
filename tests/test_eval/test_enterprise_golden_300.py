"""Integrity checks for the 300-case enterprise golden evaluation dataset."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOLDEN_PATH = ROOT / "eval" / "golden_testset_enterprise.json"
REQUIRED_FIELDS = {
    "id", "type", "category", "query", "expected_intent",
    "expected_behavior", "must_not_do", "context_info", "should_retrieve",
    "should_use_memory", "should_search_web", "should_create_ticket",
    "should_escalate", "expected_titles", "expected_context_terms",
    "expected_answer_terms", "forbidden_answer_terms", "reference_answer",
}


def test_enterprise_golden_has_300_unique_well_formed_cases() -> None:
    cases = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert len(cases) == 300
    assert [case["id"] for case in cases] == [f"GT-{number:03d}" for number in range(1, 301)]
    original_queries = {case["query"].casefold().strip() for case in cases[:90]}
    expanded_queries = [case["query"].casefold().strip() for case in cases[90:]]
    # The legacy 90-case baseline intentionally contains two greeting variants
    # with identical text.  The expansion itself must add no duplicates and
    # must not overlap any legacy query.
    assert len(set(expanded_queries)) == 210
    assert not original_queries.intersection(expanded_queries)
    for case in cases:
        assert REQUIRED_FIELDS <= set(case), case["id"]
        assert case["query"].strip(), case["id"]
        assert case["expected_behavior"], case["id"]
        assert case["reference_answer"].strip(), case["id"]
        assert all(isinstance(case[field], bool) for field in (
            "should_retrieve", "should_use_memory", "should_search_web",
            "should_create_ticket", "should_escalate",
        )), case["id"]
    assert all("expected_route" in case for case in cases[90:])


def test_expansion_preserves_the_original_90_case_prefix() -> None:
    cases = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    assert [case["id"] for case in cases[:90]] == [f"GT-{number:03d}" for number in range(1, 91)]
    assert [case["id"] for case in cases[90:]] == [f"GT-{number:03d}" for number in range(91, 301)]
