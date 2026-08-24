"""Deterministic tests for Retrieval Evaluation Baseline and Release Gate."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from eval.retrieval_metrics import (
    RetrievalGateThresholds,
    compute_dcg,
    compute_ndcg,
    evaluate_retrieval_gate,
    evaluate_single_case,
    summarize_retrieval_evaluation,
)
from scripts.run_retrieval_gate import build_thresholds_from_args, compute_file_sha256
from src.config import get_settings

GOLDEN_PATH = Path(__file__).resolve().parent.parent.parent / "eval" / "retrieval_golden_v1.json"


@pytest.fixture(autouse=True)
def prepare_database():
    """No-op override of conftest autouse fixture for pure evaluation unit tests."""
    yield


# ─── 1. GOLDEN DATASET SCHEMA INTEGRITY ──────────────────────────────────────

CANONICAL_GOLDEN_SHA256 = "ca55989f841372f75f299492f4be8a3f9215acc37b7a7da72ecc7498b1eb59b3"


def test_golden_dataset_file_exists():
    assert GOLDEN_PATH.exists(), f"Golden dataset not found at {GOLDEN_PATH}"


def test_golden_dataset_schema_and_case_integrity():
    payload = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    assert payload.get("schema_version") == "retrieval-golden-v1"
    cases = payload.get("cases", [])
    assert len(cases) == 44, f"Expected exactly 44 cases, got {len(cases)}"

    seen_ids = set()
    category_counts: dict[str, int] = {}
    scorable_cases = []
    non_scorable_cases = []

    expected_category_distribution = {
        "A_semantic_paraphrase": 7,
        "B_exact_token": 7,
        "C_multilingual": 5,
        "D_typo_informal": 5,
        "E_ambiguous": 2,
        "F_policy_authority": 4,
        "G_tenant_isolation": 5,
        "H_no_evidence": 3,
        "I_hard_negative": 6,
    }

    for case in cases:
        case_id = case["id"]
        assert case_id not in seen_ids, f"Duplicate case ID: {case_id}"
        seen_ids.add(case_id)

        cat = case["category_group"]
        category_counts[cat] = category_counts.get(cat, 0) + 1

        assert case.get("query", "").strip(), f"Empty query in case {case_id}"
        assert isinstance(case.get("expected_source_ids"), list)
        assert isinstance(case.get("acceptable_source_ids"), list)
        assert isinstance(case.get("forbidden_source_ids"), list)

        if case.get("expected_source_ids"):
            scorable_cases.append(case_id)
        else:
            non_scorable_cases.append(case_id)

        # Invariant: No overlap between expected/acceptable and forbidden
        expected_set = set(case.get("expected_source_ids", []))
        acceptable_set = set(case.get("acceptable_source_ids", []))
        forbidden_set = set(case.get("forbidden_source_ids", []))
        assert not (expected_set & forbidden_set), f"Overlap between expected and forbidden in {case_id}"
        assert not (acceptable_set & forbidden_set), f"Overlap between acceptable and forbidden in {case_id}"

    # Verify exact category counts
    assert category_counts == expected_category_distribution, (
        f"Category mismatch: got {category_counts}, expected {expected_category_distribution}"
    )

    # Verify scorable / non-scorable counts
    assert len(scorable_cases) == 39
    assert len(non_scorable_cases) == 5
    assert set(non_scorable_cases) == {"RET-E01", "RET-E02", "RET-H01", "RET-H02", "RET-H03"}


def test_golden_dataset_sha256_computation():
    digest = compute_file_sha256(GOLDEN_PATH)
    assert digest == CANONICAL_GOLDEN_SHA256, f"Golden SHA mismatch! Expected {CANONICAL_GOLDEN_SHA256}, got {digest}"


def test_default_threshold_values_pinned():
    t = RetrievalGateThresholds()
    assert t.min_hit_rate_at_1 == 0.970
    assert t.min_recall_at_1 == 0.940
    assert t.min_hit_rate_at_3 == 0.970
    assert t.min_recall_at_3 == 0.940
    assert t.min_hit_rate_at_5 == 0.970
    assert t.min_recall_at_5 == 0.940
    assert t.min_mrr_at_5 == 0.980
    assert t.min_ndcg_at_5 == 0.930
    assert t.min_d_typo_hit_rate_at_1 == 0.900
    assert t.min_b_exact_hit_rate_at_1 == 0.950
    assert t.max_cross_tenant_leaks == 0
    assert t.max_forbidden_doc_leaks == 0
    assert t.max_policy_authority_violations == 0


# ─── 2. PURE METRICS COMPUTATION UNIT TESTS ──────────────────────────────────

def test_compute_dcg_calculation():
    # Rank 1: rel=1.0 / log2(2) = 1.0
    assert pytest.approx(compute_dcg([1.0], 1)) == 1.0

    # Rank 1: rel=1.0, Rank 2: rel=0.5 / log2(3) = 0.5 / 1.5849625 = 0.31546
    assert pytest.approx(compute_dcg([1.0, 0.5], 2)) == 1.0 + (0.5 / 1.5849625)

    # Empty
    assert compute_dcg([], 5) == 0.0
    assert compute_dcg([0.0, 0.0], 2) == 0.0


def test_compute_ndcg_perfect_ranking():
    # Rank 1 has expected doc -> nDCG@5 should be 1.0
    retrieved = ["kb-001", "other-1", "other-2"]
    expected = ["kb-001"]
    acceptable = []
    assert pytest.approx(compute_ndcg(retrieved, expected, acceptable, 5)) == 1.0


def test_compute_ndcg_suboptimal_ranking():
    # Expected doc at rank 2
    retrieved = ["other-1", "kb-001", "other-2"]
    expected = ["kb-001"]
    acceptable = []
    # Ideal DCG = 1.0 / log2(2) = 1.0
    # Actual DCG = 0.0 + 1.0 / log2(3) = 0.6309
    ndcg = compute_ndcg(retrieved, expected, acceptable, 5)
    assert 0.60 < ndcg < 0.65


def test_compute_ndcg_with_acceptable_source():
    # Acceptable doc at rank 1, expected at rank 2
    retrieved = ["kb-002", "kb-001"]
    expected = ["kb-001"]
    acceptable = ["kb-002"]
    # Actual: 0.5/log2(2) + 1.0/log2(3) = 0.5 + 0.6309 = 1.1309
    # Ideal: 1.0/log2(2) + 0.5/log2(3) = 1.0 + 0.3155 = 1.3155
    ndcg = compute_ndcg(retrieved, expected, acceptable, 5)
    assert 0.80 < ndcg < 0.90


# ─── 3. SINGLE CASE EVALUATION UNIT TESTS ────────────────────────────────────

def test_evaluate_single_case_hit_at_1():
    case = {
        "id": "TEST-01",
        "category_group": "A_semantic_paraphrase",
        "query": "VPN issue",
        "expected_source_ids": ["kb-001"],
        "acceptable_source_ids": [],
        "forbidden_source_ids": [],
    }
    retrieved_docs = [
        {"doc_id": "kb-001", "relevance_score": 0.95, "metadata": {"title": "VPN Guide"}},
        {"doc_id": "kb-002", "relevance_score": 0.80, "metadata": {"title": "WiFi Guide"}},
    ]
    res = evaluate_single_case(case, retrieved_docs, top_k=5)
    assert res.hit_at_1 is True
    assert res.hit_at_3 is True
    assert res.hit_at_5 is True
    assert res.recall_at_1 == 1.0
    assert res.recall_at_5 == 1.0
    assert res.first_hit_rank == 1
    assert res.reciprocal_rank == 1.0
    assert res.forbidden_leak_count == 0
    assert res.cross_tenant_leak_count == 0
    assert res.failure_category is None


def test_evaluate_single_case_hit_at_3():
    case = {
        "id": "TEST-02",
        "category_group": "A_semantic_paraphrase",
        "query": "VPN issue",
        "expected_source_ids": ["kb-001"],
        "acceptable_source_ids": [],
        "forbidden_source_ids": [],
    }
    retrieved_docs = [
        {"doc_id": "other-1", "relevance_score": 0.90, "metadata": {"title": "Other"}},
        {"doc_id": "other-2", "relevance_score": 0.85, "metadata": {"title": "Other 2"}},
        {"doc_id": "kb-001", "relevance_score": 0.80, "metadata": {"title": "VPN Guide"}},
    ]
    res = evaluate_single_case(case, retrieved_docs, top_k=5)
    assert res.hit_at_1 is False
    assert res.hit_at_3 is True
    assert res.hit_at_5 is True
    assert res.first_hit_rank == 3
    assert pytest.approx(res.reciprocal_rank) == 1.0 / 3.0
    assert res.recall_at_1 == 0.0
    assert res.recall_at_3 == 1.0


# ─── 4. SAFETY INVARIANTS UNIT TESTS ─────────────────────────────────────────

def test_forbidden_document_leakage_detection():
    case = {
        "id": "TEST-FORBIDDEN",
        "category_group": "I_hard_negative",
        "query": "SAP issue",
        "expected_source_ids": ["kb-019"],
        "acceptable_source_ids": [],
        "forbidden_source_ids": ["kb-001", "kb-010"],
    }
    # Retrieved includes forbidden doc kb-001
    retrieved_docs = [
        {"doc_id": "kb-001", "relevance_score": 0.90, "metadata": {"title": "VPN"}},
        {"doc_id": "kb-019", "relevance_score": 0.85, "metadata": {"title": "SAP"}},
    ]
    res = evaluate_single_case(case, retrieved_docs, top_k=5)
    assert res.forbidden_leak_count == 1
    assert res.failure_category == "CONFUSABLE_DOCUMENT"


def test_cross_tenant_leakage_detection():
    case = {
        "id": "TEST-TENANT",
        "category_group": "G_tenant_isolation",
        "query": "HIS hospital issue",
        "expected_source_ids": ["kb-025"],
        "acceptable_source_ids": [],
        "forbidden_source_ids": [],
        "tenant": "healthcare",
    }
    # Retrieved includes a doc scoped to real_estate only (applicable_to_all=False)
    retrieved_docs = [
        {
            "doc_id": "kb-021",
            "relevance_score": 0.90,
            "metadata": {
                "title": "BĐS CRM",
                "company_unit": "real_estate",
                "applicable_to_all": False,
            },
        },
        {
            "doc_id": "kb-025",
            "relevance_score": 0.85,
            "metadata": {
                "title": "HIS System",
                "company_unit": "healthcare",
                "applicable_to_all": False,
            },
        },
    ]
    res = evaluate_single_case(case, retrieved_docs, top_k=5)
    assert res.cross_tenant_leak_count == 1
    assert res.failure_category == "TENANT_FILTER_FAILURE"


# ─── 5. SUMMARY AGGREGATOR UNIT TESTS ────────────────────────────────────────

def test_summarize_retrieval_evaluation_computation():
    case1 = {
        "id": "CASE-1",
        "category_group": "A_semantic_paraphrase",
        "expected_source_ids": ["kb-001"],
    }
    case2 = {
        "id": "CASE-2",
        "category_group": "A_semantic_paraphrase",
        "expected_source_ids": ["kb-002"],
    }
    case3_ambiguous = {
        "id": "CASE-3",
        "category_group": "E_ambiguous",
        "expected_source_ids": [],
        "acceptable_source_ids": ["kb-001", "kb-002"],
    }

    res1 = evaluate_single_case(case1, [{"doc_id": "kb-001"}], top_k=5)
    res2 = evaluate_single_case(case2, [{"doc_id": "other"}, {"doc_id": "kb-002"}], top_k=5)
    res3 = evaluate_single_case(case3_ambiguous, [{"doc_id": "kb-001"}], top_k=5)

    summary = summarize_retrieval_evaluation([res1, res2, res3])

    # Case 3 (ambiguous) is excluded from scorable count
    assert summary["total_cases"] == 3
    assert summary["scorable_cases"] == 2
    assert summary["hit_rate_at_1"] == 0.5  # Case 1 hit@1, Case 2 hit@2
    assert summary["hit_rate_at_5"] == 1.0  # Both hit in top 5
    assert pytest.approx(summary["mrr_at_5"]) == (1.0 + 0.5) / 2.0  # 0.75
    assert summary["cross_tenant_leak_count"] == 0
    assert summary["forbidden_doc_retrieval_count"] == 0


# ─── 6. REGRESSION GATE THRESHOLD & DECISION TESTS ───────────────────────────

BASELINE_VERIFIED_SUMMARY = {
    "hit_rate_at_1": 1.000000,
    "recall_at_1": 0.974359,
    "hit_rate_at_3": 1.000000,
    "recall_at_3": 0.974359,
    "hit_rate_at_5": 1.000000,
    "recall_at_5": 0.974359,
    "mrr_at_5": 1.000000,
    "ndcg_at_5": 0.961663,
    "cross_tenant_leak_count": 0,
    "forbidden_doc_retrieval_count": 0,
    "policy_authority_violation_count": 0,
    "category_summary": {
        "D_typo_informal": {"hit_at_1": 1.0, "hit_at_5": 1.0, "mrr": 1.0},
        "B_exact_token": {"hit_at_1": 1.0, "hit_at_5": 1.0, "mrr": 1.0},
    },
}


def test_evaluate_retrieval_gate_passes_on_verified_baseline():
    decision = evaluate_retrieval_gate(BASELINE_VERIFIED_SUMMARY)
    assert decision.passed is True, f"Gate failed unexpectedly: {decision.reasons}"
    assert len(decision.reasons) == 0
    assert len(decision.checks) == 13  # 8 global quality + 2 category floors + 3 safety
    assert all(c.passed for c in decision.checks)


@pytest.mark.parametrize(
    "metric_key,degraded_value,expected_reason_substr",
    [
        ("hit_rate_at_1", 0.90, "HitRate@1"),
        ("recall_at_1", 0.85, "Recall@1"),
        ("hit_rate_at_3", 0.95, "HitRate@3"),
        ("recall_at_3", 0.90, "Recall@3"),
        ("hit_rate_at_5", 0.95, "HitRate@5"),
        ("recall_at_5", 0.90, "Recall@5"),
        ("mrr_at_5", 0.95, "MRR@5"),
        ("ndcg_at_5", 0.90, "nDCG@5"),
    ],
)
def test_evaluate_retrieval_gate_fails_on_each_quality_floor_drop(
    metric_key: str, degraded_value: float, expected_reason_substr: str
):
    degraded_summary = {**BASELINE_VERIFIED_SUMMARY, metric_key: degraded_value}
    decision = evaluate_retrieval_gate(degraded_summary)
    assert decision.passed is False
    assert any(expected_reason_substr in r for r in decision.reasons)


@pytest.mark.parametrize(
    "cat_name,degraded_hit1,expected_reason_substr",
    [
        ("D_typo_informal", 0.80, "D_typo_informal HitRate@1"),
        ("B_exact_token", 0.85, "B_exact_token HitRate@1"),
    ],
)
def test_evaluate_retrieval_gate_fails_on_category_floor_drop(
    cat_name: str, degraded_hit1: float, expected_reason_substr: str
):
    degraded_summary = {
        **BASELINE_VERIFIED_SUMMARY,
        "category_summary": {
            **BASELINE_VERIFIED_SUMMARY["category_summary"],
            cat_name: {"hit_at_1": degraded_hit1},
        },
    }
    decision = evaluate_retrieval_gate(degraded_summary)
    assert decision.passed is False
    assert any(expected_reason_substr in r for r in decision.reasons)


@pytest.mark.parametrize(
    "safety_key,violation_value,expected_reason_substr",
    [
        ("cross_tenant_leak_count", 1, "Cross-Tenant Leaks"),
        ("forbidden_doc_retrieval_count", 1, "Forbidden Doc Leaks"),
        ("policy_authority_violation_count", 1, "Policy Authority Violations"),
    ],
)
def test_evaluate_retrieval_gate_fails_on_each_safety_violation(
    safety_key: str, violation_value: int, expected_reason_substr: str
):
    violating_summary = {**BASELINE_VERIFIED_SUMMARY, safety_key: violation_value}
    decision = evaluate_retrieval_gate(violating_summary)
    assert decision.passed is False
    assert any("HARD SAFETY VIOLATION" in r and expected_reason_substr in r for r in decision.reasons)


def test_build_thresholds_from_args_validation():
    class MockArgs:
        min_hit_rate_1 = 0.98
        min_recall_1 = None
        min_hit_rate_3 = None
        min_recall_3 = None
        min_hit_rate_5 = 0.98
        min_recall_5 = None
        min_mrr_5 = 0.99
        min_ndcg_5 = None
        min_d_typo_hit_1 = 0.95
        min_b_exact_hit_1 = 0.98

    t = build_thresholds_from_args(MockArgs())
    assert t.min_hit_rate_at_1 == 0.98
    assert t.min_hit_rate_at_5 == 0.98
    assert t.min_mrr_at_5 == 0.99
    assert t.min_d_typo_hit_rate_at_1 == 0.95
    assert t.min_b_exact_hit_rate_at_1 == 0.98
    assert t.min_ndcg_at_5 == RetrievalGateThresholds().min_ndcg_at_5

    # Invalid range should raise ValueError
    class InvalidArgs:
        min_hit_rate_1 = 1.5
        min_recall_1 = None
        min_hit_rate_3 = None
        min_recall_3 = None
        min_hit_rate_5 = None
        min_recall_5 = None
        min_mrr_5 = None
        min_ndcg_5 = None
        min_d_typo_hit_1 = None
        min_b_exact_hit_1 = None

    with pytest.raises(ValueError, match="must be in range"):
        build_thresholds_from_args(InvalidArgs())


# ─── 7. ARTIFACT IMMUTABILITY & PROVENANCE TESTS ─────────────────────────────

def test_historical_dense_baseline_artifact_immutability():
    """Historical Step 1 dense baseline artifact must remain preserved."""
    path = Path(__file__).resolve().parent.parent.parent / "eval" / "results" / "retrieval_baseline_v1_0.json"
    assert path.exists(), f"Historical baseline not found at {path}"
    data = json.loads(path.read_text(encoding="utf-8"))
    summary = data.get("summary", {})
    assert pytest.approx(summary.get("hit_rate_at_1", 0.0), abs=1e-3) == 0.846
    assert pytest.approx(summary.get("mrr_at_5", 0.0), abs=1e-3) == 0.905
    assert pytest.approx(summary.get("ndcg_at_5", 0.0), abs=1e-3) == 0.872


def test_hybrid_lock_artifact_immutability():
    """Historical Step 2 hybrid lock artifact must remain preserved."""
    path = Path(__file__).resolve().parent.parent.parent / "eval" / "results" / "retrieval_hybrid_lock_v1_0.json"
    assert path.exists(), f"Hybrid lock artifact not found at {path}"
    data = json.loads(path.read_text(encoding="utf-8"))
    meta = data.get("meta", {})
    assert meta.get("golden_sha256") == compute_file_sha256(GOLDEN_PATH)
    assert meta.get("collection_count") == 433


def test_authority_lock_artifact_provenance():
    """Active canonical authority-lock artifact must match its versioned provenance."""
    path = Path(__file__).resolve().parent.parent.parent / "eval" / "results" / "retrieval_authority_lock_v1_0.json"
    assert path.exists(), f"Authority lock artifact not found at {path}"
    data = json.loads(path.read_text(encoding="utf-8"))
    meta = data.get("meta", {})
    assert meta.get("golden_sha256") == compute_file_sha256(GOLDEN_PATH)
    expected_collection_counts = {
        "helpdesk_kb_multilingual_v2_sentence_transformer": 433,
        "helpdesk_kb_multilingual_v3_sentence_transformer": 443,
    }
    active_collection = get_settings().chroma_collection_name
    assert active_collection in expected_collection_counts
    assert meta.get("collection") == active_collection
    assert meta.get("collection_count") == expected_collection_counts[active_collection]
    summary = data.get("summary", {})
    assert summary.get("hit_rate_at_1", 0.0) == 1.0
    assert summary.get("hit_rate_at_3", 0.0) == 1.0
    assert summary.get("hit_rate_at_5", 0.0) == 1.0
    assert summary.get("mrr_at_5", 0.0) == 1.0
    assert summary.get("cross_tenant_leak_count") == 0
    assert summary.get("forbidden_doc_retrieval_count") == 0
    assert summary.get("policy_authority_violation_count") == 0
