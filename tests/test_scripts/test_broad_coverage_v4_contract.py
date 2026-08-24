"""Regression coverage for the V4 broad-coverage evaluation contract."""
from __future__ import annotations

import json
from pathlib import Path

from eval.broad_coverage_contract import (
    AMBIGUOUS,
    COVERAGE_GAP,
    acceptable_doc_ids,
    case_override,
    contract_counts,
    load_contract,
    metric_summary,
    target_doc_ids,
    validate_contract,
)
from eval.v4_eval_matching import doc_matches_targets, targets_canonical_aliases
from scripts import evaluate_v4_broad_coverage as broad_evaluator

ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = ROOT / "eval" / "broad_coverage_v4.json"


def _dataset() -> list[dict]:
    return json.loads(DATASET_PATH.read_text(encoding="utf-8"))


def test_canonical_id_corrections_point_to_available_internal_resource_source() -> None:
    dataset = {item["id"]: item for item in _dataset()}
    for number in range(136, 141):
        assert dataset[f"COV-{number}"]["expected_doc_ids"] == [
            "p0-06-vpn-connected-internal-unreachable-c001"
        ]


def test_contract_has_valid_source_level_targets_and_explicit_classifications() -> None:
    dataset = _dataset()
    contract = load_contract()
    validate_contract(dataset, contract)
    assert contract_counts(contract) == {"ambiguous_cases": 7, "coverage_gap_cases": 10}

    for item in dataset:
        alternatives = acceptable_doc_ids(contract, item["id"])
        if alternatives:
            assert contract["acceptable_alternatives"][item["id"]]["rationale"]
            aliases = targets_canonical_aliases(target_doc_ids(item, contract))
            assert all(doc_matches_targets({"doc_id": source_id, "metadata": {}}, aliases) for source_id in alternatives)


def test_ambiguous_and_coverage_cases_are_explicit_not_removed_from_contract() -> None:
    contract = load_contract()
    assert case_override(contract, "COV-004")["classification"] == AMBIGUOUS
    assert case_override(contract, "COV-239")["classification"] == AMBIGUOUS
    for number in [131, 132, 133, 134, 135, 286, 287, 288, 289, 290]:
        assert case_override(contract, f"COV-{number}")["classification"] == COVERAGE_GAP


def test_raw_and_scorable_metrics_use_documented_denominators() -> None:
    outcomes = [
        {"target_available": True, "classification": None, "rank": 1},
        {"target_available": True, "classification": AMBIGUOUS, "rank": None},
        {"target_available": False, "classification": COVERAGE_GAP, "rank": None},
    ]
    summary = metric_summary(outcomes)
    assert summary["total_cases"] == 3
    assert summary["available_cases"] == 2
    assert summary["ambiguous_cases"] == 1
    assert summary["coverage_gap_cases"] == 1
    assert summary["raw_all_cases_metrics"] == {
        "denominator": 3,
        "hit_rate_at_1": 33.33,
        "hit_rate_at_3": 33.33,
        "hit_rate_at_5": 33.33,
    }
    assert summary["scorable_available_metrics"] == {
        "denominator": 1,
        "hit_rate_at_1": 100.0,
        "hit_rate_at_3": 100.0,
        "hit_rate_at_5": 100.0,
    }


def test_evaluator_isolates_bm25_cache_each_time_it_switches_collection(monkeypatch) -> None:
    collections = {"v3": object(), "v4": object()}

    class FakeClient:
        def get_collection(self, name: str) -> object:
            return collections[name]

    invalidations: list[bool] = []
    monkeypatch.setattr(broad_evaluator.rag, "get_chroma_client", lambda: FakeClient())
    monkeypatch.setattr(broad_evaluator.rag, "_collection", None)
    monkeypatch.setattr(broad_evaluator.rag, "_rag_query_cache", {"old": "value"})
    monkeypatch.setattr(broad_evaluator.bm25, "invalidate_bm25_index", lambda: invalidations.append(True))

    assert broad_evaluator.activate_collection("v3") is collections["v3"]
    assert broad_evaluator.activate_collection("v4") is collections["v4"]
    assert broad_evaluator.rag._collection is collections["v4"]
    assert broad_evaluator.rag._rag_query_cache == {}
    assert invalidations == [True, True]


def test_production_runtime_does_not_import_broad_evaluation_metadata() -> None:
    runtime_sources = (ROOT / "src" / "services").glob("*.py")
    forbidden = ("broad_coverage_v4", "acceptable_alternatives", "COVERAGE_GAP")
    for path in runtime_sources:
        source = path.read_text(encoding="utf-8")
        assert not any(marker in source for marker in forbidden), path
