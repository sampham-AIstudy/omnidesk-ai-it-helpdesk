"""Deterministic retrieval evaluation metrics for P-236 Help Desk AI.

Computes Recall@K, MRR@K, nDCG@K, HitRate@K and enforces safety invariants
(cross-tenant leakage, forbidden document retrieval, policy authority).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RetrievalGateThresholds:
    """Tightly calibrated regression lock thresholds based on deterministic Step 4 authority baseline."""

    min_hit_rate_at_1: float = 0.970
    min_recall_at_1: float = 0.940
    min_hit_rate_at_3: float = 0.970
    min_recall_at_3: float = 0.940
    min_hit_rate_at_5: float = 0.970
    min_recall_at_5: float = 0.940
    min_mrr_at_5: float = 0.980
    min_ndcg_at_5: float = 0.930
    # Category-level regression floors
    min_d_typo_hit_rate_at_1: float = 0.900
    min_b_exact_hit_rate_at_1: float = 0.950
    # Safety invariants are non-negotiable hard zeros
    max_cross_tenant_leaks: int = 0
    max_forbidden_doc_leaks: int = 0
    max_policy_authority_violations: int = 0


@dataclass(frozen=True)
class MetricCheck:
    """Status of an individual metric evaluation against its threshold."""

    metric_name: str
    measured_value: float
    threshold_value: float
    comparison_op: str  # ">=" or "=="
    passed: bool
    is_safety_invariant: bool


@dataclass(frozen=True)
class GateDecision:
    """Overall release gate evaluation decision."""

    passed: bool
    reasons: list[str]
    checks: list[MetricCheck]


@dataclass
class CaseRetrievalResult:
    """Evaluation result for a single retrieval test case."""

    case_id: str
    category_group: str
    query: str
    expected_ids: list[str]
    acceptable_ids: list[str]
    forbidden_ids: list[str]
    retrieved_ids: list[str]
    retrieved_docs: list[dict[str, Any]]
    first_hit_rank: int | None  # 1-indexed rank of first relevant doc
    hit_at_1: bool
    hit_at_3: bool
    hit_at_5: bool
    recall_at_1: float
    recall_at_3: float
    recall_at_5: float
    reciprocal_rank: float
    ndcg_at_5: float
    ndcg_at_10: float
    forbidden_leak_count: int
    cross_tenant_leak_count: int
    policy_authority_violation: bool
    failure_category: str | None  # None if passed
    relevance_scores: list[float] = field(default_factory=list)


def compute_dcg(relevances: list[float], k: int) -> float:
    """Compute Discounted Cumulative Gain at rank K."""
    dcg = 0.0
    for idx, rel in enumerate(relevances[:k]):
        if rel > 0:
            dcg += rel / math.log2(idx + 2)  # idx+2 since idx is 0-indexed (rank=idx+1)
    return dcg


def compute_ndcg(retrieved_ids: list[str], expected_ids: list[str], acceptable_ids: list[str], k: int) -> float:
    """Compute normalized Discounted Cumulative Gain at rank K."""
    if not expected_ids and not acceptable_ids:
        return 1.0  # No expectation defined

    # Relevance assignment: expected=1.0, acceptable=0.5, else=0.0
    actual_relevances = []
    seen = set()
    for doc_id in retrieved_ids[:k]:
        if doc_id in seen:
            actual_relevances.append(0.0)
            continue
        seen.add(doc_id)
        if doc_id in expected_ids:
            actual_relevances.append(1.0)
        elif doc_id in acceptable_ids:
            actual_relevances.append(0.5)
        else:
            actual_relevances.append(0.0)

    # Ideal ranking: all expected items first, then acceptable items
    ideal_relevances = [1.0] * min(k, len(expected_ids))
    remaining_slots = k - len(ideal_relevances)
    if remaining_slots > 0 and acceptable_ids:
        ideal_relevances.extend([0.5] * min(remaining_slots, len(acceptable_ids)))

    actual_dcg = compute_dcg(actual_relevances, k)
    ideal_dcg = compute_dcg(ideal_relevances, k)

    if ideal_dcg == 0.0:
        return 1.0 if actual_dcg == 0.0 else 0.0
    return min(1.0, actual_dcg / ideal_dcg)


def evaluate_single_case(
    case: dict[str, Any],
    retrieved_docs: list[dict[str, Any]],
    top_k: int = 5,
) -> CaseRetrievalResult:
    """Evaluate retrieval results for one case."""
    case_id = case.get("id", "UNKNOWN")
    category = case.get("category_group", "unknown")
    query = case.get("query", "")
    expected = case.get("expected_source_ids", [])
    acceptable = case.get("acceptable_source_ids", [])
    forbidden = set(case.get("forbidden_source_ids", []))
    tenant = case.get("tenant")

    retrieved_ids = [str(doc.get("doc_id", "")) for doc in retrieved_docs]
    relevance_scores = [float(doc.get("relevance_score", 0.0)) for doc in retrieved_docs]

    # Find first hit rank
    relevant_ids = set(expected) | set(acceptable)
    first_hit_rank = None
    for idx, doc_id in enumerate(retrieved_ids):
        if doc_id in relevant_ids:
            first_hit_rank = idx + 1
            break

    hit_at_1 = first_hit_rank == 1
    hit_at_3 = first_hit_rank is not None and first_hit_rank <= 3
    hit_at_5 = first_hit_rank is not None and first_hit_rank <= 5

    # Recall calculation
    if expected:
        found_expected_at_1 = len(set(retrieved_ids[:1]) & set(expected))
        found_expected_at_3 = len(set(retrieved_ids[:3]) & set(expected))
        found_expected_at_5 = len(set(retrieved_ids[:5]) & set(expected))
        recall_at_1 = found_expected_at_1 / len(expected)
        recall_at_3 = found_expected_at_3 / len(expected)
        recall_at_5 = found_expected_at_5 / len(expected)
    elif acceptable:
        found_acc_at_1 = 1.0 if any(doc_id in acceptable for doc_id in retrieved_ids[:1]) else 0.0
        found_acc_at_3 = 1.0 if any(doc_id in acceptable for doc_id in retrieved_ids[:3]) else 0.0
        found_acc_at_5 = 1.0 if any(doc_id in acceptable for doc_id in retrieved_ids[:5]) else 0.0
        recall_at_1 = found_acc_at_1
        recall_at_3 = found_acc_at_3
        recall_at_5 = found_acc_at_5
    else:
        # Ambiguous / No evidence cases
        recall_at_1 = 1.0
        recall_at_3 = 1.0
        recall_at_5 = 1.0

    reciprocal_rank = (1.0 / first_hit_rank) if first_hit_rank is not None else 0.0
    ndcg_at_5 = compute_ndcg(retrieved_ids, expected, acceptable, 5)
    ndcg_at_10 = compute_ndcg(retrieved_ids, expected, acceptable, 10)

    # Safety checks
    forbidden_leak_count = sum(1 for doc_id in retrieved_ids if doc_id in forbidden)

    # Tenant isolation check
    cross_tenant_leak_count = 0
    if tenant and tenant != "corporate":
        for doc in retrieved_docs:
            meta = doc.get("metadata", {}) or {}
            applicable_all = meta.get("applicable_to_all", True)
            if isinstance(applicable_all, str):
                applicable_all = applicable_all.lower() in ("true", "1", "yes", "all")
            doc_company = meta.get("company_unit") or "all"
            if not applicable_all and doc_company not in ("all", tenant):
                cross_tenant_leak_count += 1

    # Policy authority violation check
    policy_authority_violation = False
    if "F_policy_authority" in category or "WRONG_POLICY_SOURCE" in case.get("failure_modes", []):
        # Must retrieve authoritative internal KB (kb-NNN) at top rank
        top_doc = retrieved_docs[0] if retrieved_docs else {}
        top_meta = top_doc.get("metadata", {}) or {}
        top_source = top_meta.get("source", "")
        top_id = top_doc.get("doc_id", "")
        if top_id not in expected and top_source != "internal_curated_kb":
            policy_authority_violation = True

    # Failure mode classification
    failure_category = None
    if cross_tenant_leak_count > 0:
        failure_category = "TENANT_FILTER_FAILURE"
    elif forbidden_leak_count > 0:
        failure_category = "CONFUSABLE_DOCUMENT"
    elif policy_authority_violation:
        failure_category = "WRONG_POLICY_SOURCE"
    elif not hit_at_5 and relevant_ids:
        top_scores = relevance_scores[:5]
        if top_scores and max(top_scores) < 0.50:
            failure_category = "LOW_RELEVANCE"
        elif any(term in query.lower() for term in ["lỗi", "error", "auth", "sync"]):
            failure_category = "LEXICAL_MISS"
        else:
            failure_category = "SEMANTIC_MISS"

    return CaseRetrievalResult(
        case_id=case_id,
        category_group=category,
        query=query,
        expected_ids=expected,
        acceptable_ids=acceptable,
        forbidden_ids=list(forbidden),
        retrieved_ids=retrieved_ids,
        retrieved_docs=retrieved_docs,
        first_hit_rank=first_hit_rank,
        hit_at_1=hit_at_1,
        hit_at_3=hit_at_3,
        hit_at_5=hit_at_5,
        recall_at_1=recall_at_1,
        recall_at_3=recall_at_3,
        recall_at_5=recall_at_5,
        reciprocal_rank=reciprocal_rank,
        ndcg_at_5=ndcg_at_5,
        ndcg_at_10=ndcg_at_10,
        forbidden_leak_count=forbidden_leak_count,
        cross_tenant_leak_count=cross_tenant_leak_count,
        policy_authority_violation=policy_authority_violation,
        failure_category=failure_category,
        relevance_scores=relevance_scores,
    )


def summarize_retrieval_evaluation(case_results: list[CaseRetrievalResult]) -> dict[str, Any]:
    """Aggregate per-case metrics into overall summary and category breakdowns."""
    # Exclude ambiguous and out-of-scope/no_evidence cases from strict Recall/MRR/nDCG
    scorable_cases = [
        r for r in case_results
        if "ambiguous" not in r.category_group.lower()
        and "no_evidence" not in r.category_group.lower()
        and (r.expected_ids or r.acceptable_ids)
    ]

    total_scorable = len(scorable_cases)

    hit_at_1_count = sum(1 for r in scorable_cases if r.hit_at_1)
    hit_at_3_count = sum(1 for r in scorable_cases if r.hit_at_3)
    hit_at_5_count = sum(1 for r in scorable_cases if r.hit_at_5)

    recall_at_1_sum = sum(r.recall_at_1 for r in scorable_cases)
    recall_at_3_sum = sum(r.recall_at_3 for r in scorable_cases)
    recall_at_5_sum = sum(r.recall_at_5 for r in scorable_cases)
    mrr_sum = sum(r.reciprocal_rank for r in scorable_cases)
    ndcg_5_sum = sum(r.ndcg_at_5 for r in scorable_cases)
    ndcg_10_sum = sum(r.ndcg_at_10 for r in scorable_cases)

    # Invariants checked across ALL cases (including ambiguous/no_evidence)
    total_forbidden_leak = sum(r.forbidden_leak_count for r in case_results)
    total_cross_tenant_leak = sum(r.cross_tenant_leak_count for r in case_results)
    total_policy_violations = sum(1 for r in case_results if r.policy_authority_violation)

    # Category breakdown
    categories: dict[str, list[CaseRetrievalResult]] = {}
    for r in case_results:
        categories.setdefault(r.category_group, []).append(r)

    category_summary = {}
    for cat_name, cat_results in sorted(categories.items()):
        cat_scorable = [r for r in cat_results if r in scorable_cases]
        n_scorable = len(cat_scorable)
        category_summary[cat_name] = {
            "total_cases": len(cat_results),
            "scorable_cases": n_scorable,
            "hit_at_1": sum(1 for r in cat_scorable if r.hit_at_1) / n_scorable if n_scorable else 1.0,
            "hit_at_5": sum(1 for r in cat_scorable if r.hit_at_5) / n_scorable if n_scorable else 1.0,
            "recall_at_5": sum(r.recall_at_5 for r in cat_scorable) / n_scorable if n_scorable else 1.0,
            "mrr": sum(r.reciprocal_rank for r in cat_scorable) / n_scorable if n_scorable else 1.0,
            "ndcg_at_5": sum(r.ndcg_at_5 for r in cat_scorable) / n_scorable if n_scorable else 1.0,
            "forbidden_leaks": sum(r.forbidden_leak_count for r in cat_results),
            "cross_tenant_leaks": sum(r.cross_tenant_leak_count for r in cat_results),
        }

    # Failure breakdown
    failure_breakdown: dict[str, int] = {}
    for r in case_results:
        if r.failure_category:
            failure_breakdown[r.failure_category] = failure_breakdown.get(r.failure_category, 0) + 1

    return {
        "total_cases": len(case_results),
        "scorable_cases": total_scorable,
        "hit_rate_at_1": hit_at_1_count / total_scorable if total_scorable else 0.0,
        "hit_rate_at_3": hit_at_3_count / total_scorable if total_scorable else 0.0,
        "hit_rate_at_5": hit_at_5_count / total_scorable if total_scorable else 0.0,
        "recall_at_1": recall_at_1_sum / total_scorable if total_scorable else 0.0,
        "recall_at_3": recall_at_3_sum / total_scorable if total_scorable else 0.0,
        "recall_at_5": recall_at_5_sum / total_scorable if total_scorable else 0.0,
        "mrr_at_5": mrr_sum / total_scorable if total_scorable else 0.0,
        "ndcg_at_5": ndcg_5_sum / total_scorable if total_scorable else 0.0,
        "ndcg_at_10": ndcg_10_sum / total_scorable if total_scorable else 0.0,
        "cross_tenant_leak_count": total_cross_tenant_leak,
        "forbidden_doc_retrieval_count": total_forbidden_leak,
        "policy_authority_violation_count": total_policy_violations,
        "category_summary": category_summary,
        "failure_breakdown": failure_breakdown,
    }


def evaluate_retrieval_gate(
    summary: dict[str, Any],
    thresholds: RetrievalGateThresholds | None = None,
) -> GateDecision:
    """Pure evaluation function that validates summary metrics against regression thresholds.

    Evaluates both quality regression floors and zero-tolerance safety invariants.
    """
    t = thresholds or RetrievalGateThresholds()
    checks: list[MetricCheck] = []
    reasons: list[str] = []

    # Quality floors
    quality_checks = [
        ("HitRate@1", summary.get("hit_rate_at_1", 0.0), t.min_hit_rate_at_1),
        ("Recall@1", summary.get("recall_at_1", 0.0), t.min_recall_at_1),
        ("HitRate@3", summary.get("hit_rate_at_3", 0.0), t.min_hit_rate_at_3),
        ("Recall@3", summary.get("recall_at_3", 0.0), t.min_recall_at_3),
        ("HitRate@5", summary.get("hit_rate_at_5", 0.0), t.min_hit_rate_at_5),
        ("Recall@5", summary.get("recall_at_5", 0.0), t.min_recall_at_5),
        ("MRR@5", summary.get("mrr_at_5", 0.0), t.min_mrr_at_5),
        ("nDCG@5", summary.get("ndcg_at_5", 0.0), t.min_ndcg_at_5),
    ]

    # Category quality floors
    cat_summary = summary.get("category_summary", {})
    d_typo_val = cat_summary.get("D_typo_informal", {}).get("hit_at_1", summary.get("d_typo_hit_rate_at_1", 0.0))
    b_exact_val = cat_summary.get("B_exact_token", {}).get("hit_at_1", summary.get("b_exact_hit_rate_at_1", 0.0))

    if t.min_d_typo_hit_rate_at_1 is not None:
        quality_checks.append(("D_typo_informal HitRate@1", d_typo_val, t.min_d_typo_hit_rate_at_1))
    if t.min_b_exact_hit_rate_at_1 is not None:
        quality_checks.append(("B_exact_token HitRate@1", b_exact_val, t.min_b_exact_hit_rate_at_1))

    for name, measured, threshold in quality_checks:
        passed = measured >= threshold
        checks.append(
            MetricCheck(
                metric_name=name,
                measured_value=measured,
                threshold_value=threshold,
                comparison_op=">=",
                passed=passed,
                is_safety_invariant=False,
            )
        )
        if not passed:
            is_pct = "Rate" in name or "Recall" in name
            m_str = f"{measured:.1%}" if is_pct else f"{measured:.3f}"
            t_str = f"{threshold:.1%}" if is_pct else f"{threshold:.3f}"
            reasons.append(f"{name} ({m_str}) below threshold ({t_str})")

    # Safety invariants
    safety_checks = [
        ("Cross-Tenant Leaks", summary.get("cross_tenant_leak_count", 0), t.max_cross_tenant_leaks),
        ("Forbidden Doc Leaks", summary.get("forbidden_doc_retrieval_count", 0), t.max_forbidden_doc_leaks),
        ("Policy Authority Violations", summary.get("policy_authority_violation_count", 0), t.max_policy_authority_violations),
    ]

    for name, measured, threshold in safety_checks:
        passed = measured == threshold
        checks.append(
            MetricCheck(
                metric_name=name,
                measured_value=float(measured),
                threshold_value=float(threshold),
                comparison_op="==",
                passed=passed,
                is_safety_invariant=True,
            )
        )
        if not passed:
            reasons.append(f"HARD SAFETY VIOLATION: {name} ({int(measured)}) must be {int(threshold)}")

    all_passed = len(reasons) == 0
    return GateDecision(passed=all_passed, reasons=reasons, checks=checks)
