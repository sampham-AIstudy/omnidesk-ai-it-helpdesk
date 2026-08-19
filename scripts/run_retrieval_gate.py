#!/usr/bin/env python3
"""Retrieval Evaluation Baseline and Release Gate for P-236 Help Desk AI.

Evaluates the CURRENT retrieval pipeline deterministically without external LLMs or network access.
Enforces tight regression lock floors and zero-tolerance safety invariants.

Usage:
    python scripts/run_retrieval_gate.py
    python scripts/run_retrieval_gate.py --golden-path eval/retrieval_golden_v1.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Ensure workspace root is in path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
os.environ.setdefault("HF_DEACTIVATE_ASYNC_LOAD", "1")

from eval.retrieval_metrics import (  # noqa: E402
    CaseRetrievalResult,
    GateDecision,
    RetrievalGateThresholds,
    evaluate_retrieval_gate,
    evaluate_single_case,
    summarize_retrieval_evaluation,
)
from src.config import get_settings  # noqa: E402
from src.services.rag_service import get_collection_count, search_similar  # noqa: E402


def compute_file_sha256(path: Path) -> str:
    """Compute SHA-256 digest of a dataset file for provenance locking."""
    if not path.exists():
        return ""
    hasher = hashlib.sha256()
    hasher.update(path.read_bytes())
    return hasher.hexdigest()


def run_retrieval_evaluation(
    golden_cases: list[dict[str, Any]],
    top_k: int = 5,
) -> tuple[list[CaseRetrievalResult], dict[str, Any]]:
    """Run retrieval for all golden cases and compute comprehensive metrics."""
    case_results: list[CaseRetrievalResult] = []

    for case in golden_cases:
        query = case["query"]
        tenant = case.get("tenant")
        department = case.get("department")

        retrieved_docs = search_similar(
            query=query,
            n_results=top_k,
            user_company_unit=tenant,
            user_department=department,
        )

        res = evaluate_single_case(case, retrieved_docs, top_k=top_k)
        case_results.append(res)

    summary = summarize_retrieval_evaluation(case_results)
    return case_results, summary


def generate_markdown_report(
    summary: dict[str, Any],
    gate_decision: GateDecision,
    case_results: list[CaseRetrievalResult],
    meta: dict[str, Any],
) -> str:
    """Generate clean GitHub Flavored Markdown report with dynamic threshold checks."""
    lines = [
        "# P-236 Retrieval Evaluation Baseline & Release Gate Report",
        "",
        f"- **Generated At**: `{meta['timestamp']}`",
        f"- **Collection**: `{meta['collection']}`",
        f"- **Embedding Model**: `{meta['embedding_model']}`",
        f"- **Collection Size**: {meta['collection_count']} documents/chunks",
        f"- **Golden Test Cases**: {summary['total_cases']} total ({summary['scorable_cases']} scorable)",
        f"- **Golden File SHA-256**: `{meta.get('golden_sha256', 'N/A')[:16]}...`",
        f"- **Evaluation Mode**: Raw Retriever (`search_similar()`, Top-{meta['top_k']})",
        f"- **Gate Overall Status**: **{'✅ PASSED' if gate_decision.passed else '❌ FAILED'}**",
        "",
        "## 1. Regression Lock & Quality Metrics",
        "",
        "| Metric | Measured Value | Threshold | Status |",
        "|---|---:|---:|:---:|",
    ]

    for check in gate_decision.checks:
        is_pct = "Rate" in check.metric_name or "Recall" in check.metric_name
        measured_fmt = f"{check.measured_value:.1%}" if is_pct else (f"{int(check.measured_value)}" if check.is_safety_invariant else f"{check.measured_value:.3f}")
        threshold_fmt = f"{check.comparison_op} {check.threshold_value:.1%}" if is_pct else (f"{check.comparison_op} {int(check.threshold_value)}" if check.is_safety_invariant else f"{check.comparison_op} {check.threshold_value:.3f}")
        status_label = "✅ PASS" if check.passed else ("❌ HARD FAIL" if check.is_safety_invariant else "❌ FAIL")
        lines.append(f"| **{check.metric_name}** | {measured_fmt} | {threshold_fmt} | {status_label} |")

    lines.extend([
        "",
        "## 2. Category Breakdown",
        "",
        "| Category Group | Cases | Scorable | HitRate@1 | HitRate@5 | Recall@5 | MRR | nDCG@5 | Leaks |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])

    for cat_name, cat in sorted(summary["category_summary"].items()):
        lines.append(
            f"| `{cat_name}` | {cat['total_cases']} | {cat['scorable_cases']} | "
            f"{cat['hit_at_1']:.1%} | {cat['hit_at_5']:.1%} | {cat['recall_at_5']:.1%} | "
            f"{cat['mrr']:.3f} | {cat['ndcg_at_5']:.3f} | {cat['forbidden_leaks'] + cat['cross_tenant_leaks']} |"
        )

    lines.extend([
        "",
        "## 3. Failure Breakdown",
        "",
    ])

    if summary["failure_breakdown"]:
        lines.extend([
            "| Failure Category | Count | Description |",
            "|---|---:|---|",
        ])
        descriptions = {
            "TENANT_FILTER_FAILURE": "Cross-tenant document retrieved for isolated tenant scope",
            "CONFUSABLE_DOCUMENT": "Forbidden or confusing document outranked correct KB",
            "WRONG_POLICY_SOURCE": "Policy query did not retrieve authoritative internal KB",
            "LEXICAL_MISS": "Dense retrieval underweighted technical/error token",
            "SEMANTIC_MISS": "Semantic embedding did not capture intent closely enough",
            "LOW_RELEVANCE": "All retrieved candidates scored below minimum relevance",
        }
        for fail_cat, count in sorted(summary["failure_breakdown"].items()):
            desc = descriptions.get(fail_cat, "Other retrieval failure")
            lines.append(f"| `{fail_cat}` | {count} | {desc} |")
    else:
        lines.append("No failures detected across all test cases. ✅")

    lines.extend([
        "",
        "## 4. Case-by-Case Results",
        "",
        "| ID | Category | Query | Expected | 1st Hit Rank | Top Retrieved ID & Title | Status |",
        "|---|---|---|---|:---:|---|:---:|",
    ])

    for r in case_results:
        exp_str = ", ".join(r.expected_ids) if r.expected_ids else (", ".join(r.acceptable_ids) or "None")
        rank_str = str(r.first_hit_rank) if r.first_hit_rank is not None else "Miss"
        top_doc = r.retrieved_docs[0] if r.retrieved_docs else {}
        top_id = top_doc.get("doc_id", "N/A")
        top_title = (top_doc.get("metadata", {}) or {}).get("title", "N/A")
        top_score = top_doc.get("relevance_score", 0.0)
        top_info = f"`{top_id}` ({top_score:.2f}): {top_title[:30]}"

        status_icon = "✅ PASS" if (r.hit_at_5 or not r.expected_ids) and r.forbidden_leak_count == 0 and r.cross_tenant_leak_count == 0 else "❌ FAIL"
        lines.append(
            f"| `{r.case_id}` | `{r.category_group}` | {r.query[:40]} | `{exp_str}` | {rank_str} | {top_info} | {status_icon} |"
        )

    return "\n".join(lines) + "\n"


def build_thresholds_from_args(args: argparse.Namespace) -> RetrievalGateThresholds:
    """Validate and build threshold configuration from CLI arguments."""
    defaults = RetrievalGateThresholds()

    def _val(param_val: float | None, default_val: float, name: str) -> float:
        if param_val is None:
            return default_val
        if not 0.0 <= param_val <= 1.0:
            raise ValueError(f"Threshold {name} must be in range [0.0, 1.0], got {param_val}")
        return param_val

    return RetrievalGateThresholds(
        min_hit_rate_at_1=_val(args.min_hit_rate_1, defaults.min_hit_rate_at_1, "--min-hit-rate-1"),
        min_recall_at_1=_val(args.min_recall_1, defaults.min_recall_at_1, "--min-recall-1"),
        min_hit_rate_at_3=_val(args.min_hit_rate_3, defaults.min_hit_rate_at_3, "--min-hit-rate-3"),
        min_recall_at_3=_val(args.min_recall_3, defaults.min_recall_at_3, "--min-recall-3"),
        min_hit_rate_at_5=_val(args.min_hit_rate_5, defaults.min_hit_rate_at_5, "--min-hit-rate-5"),
        min_recall_at_5=_val(args.min_recall_5, defaults.min_recall_at_5, "--min-recall-5"),
        min_mrr_at_5=_val(args.min_mrr_5, defaults.min_mrr_at_5, "--min-mrr-5"),
        min_ndcg_at_5=_val(args.min_ndcg_5, defaults.min_ndcg_at_5, "--min-ndcg-5"),
        min_d_typo_hit_rate_at_1=_val(args.min_d_typo_hit_1, defaults.min_d_typo_hit_rate_at_1, "--min-d-typo-hit-1"),
        min_b_exact_hit_rate_at_1=_val(args.min_b_exact_hit_1, defaults.min_b_exact_hit_rate_at_1, "--min-b-exact-hit-1"),
    )


def main() -> int:
    defaults = RetrievalGateThresholds()
    parser = argparse.ArgumentParser(description="P-236 Retrieval Evaluation Baseline & Release Gate")
    parser.add_argument(
        "--golden-path",
        type=Path,
        default=ROOT_DIR / "eval" / "retrieval_golden_v1.json",
        help="Path to retrieval golden dataset JSON",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=ROOT_DIR / "eval" / "results" / "retrieval_authority_lock_v1_0.json",
        help="Output path for baseline JSON results",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=ROOT_DIR / "eval" / "results" / "retrieval_authority_lock_v1_0.md",
        help="Output path for baseline Markdown report",
    )
    parser.add_argument("--top-k", type=int, default=5, help="Number of retrieved results to evaluate (minimum 5)")
    parser.add_argument("--min-hit-rate-1", type=float, default=None, help=f"HitRate@1 threshold (default {defaults.min_hit_rate_at_1:.3f})")
    parser.add_argument("--min-recall-1", type=float, default=None, help=f"Recall@1 threshold (default {defaults.min_recall_at_1:.3f})")
    parser.add_argument("--min-hit-rate-3", type=float, default=None, help=f"HitRate@3 threshold (default {defaults.min_hit_rate_at_3:.3f})")
    parser.add_argument("--min-recall-3", type=float, default=None, help=f"Recall@3 threshold (default {defaults.min_recall_at_3:.3f})")
    parser.add_argument("--min-hit-rate-5", type=float, default=None, help=f"HitRate@5 threshold (default {defaults.min_hit_rate_at_5:.3f})")
    parser.add_argument("--min-recall-5", type=float, default=None, help=f"Recall@5 threshold (default {defaults.min_recall_at_5:.3f})")
    parser.add_argument("--min-mrr-5", type=float, default=None, help=f"MRR@5 threshold (default {defaults.min_mrr_at_5:.3f})")
    parser.add_argument("--min-ndcg-5", type=float, default=None, help=f"nDCG@5 threshold (default {defaults.min_ndcg_at_5:.3f})")
    parser.add_argument("--min-d-typo-hit-1", type=float, default=None, help=f"D_typo HitRate@1 threshold (default {defaults.min_d_typo_hit_rate_at_1:.3f})")
    parser.add_argument("--min-b-exact-hit-1", type=float, default=None, help=f"B_exact HitRate@1 threshold (default {defaults.min_b_exact_hit_rate_at_1:.3f})")
    args = parser.parse_args()

    if args.top_k < 5:
        print(f"ERROR: --top-k must be >= 5, got {args.top_k}", file=sys.stderr)
        return 1

    if not args.golden_path.exists():
        print(f"ERROR: Golden dataset not found at {args.golden_path}", file=sys.stderr)
        return 1

    try:
        thresholds = build_thresholds_from_args(args)
    except ValueError as exc:
        print(f"ERROR: Invalid threshold argument: {exc}", file=sys.stderr)
        return 1

    print("=== P-236 Retrieval Evaluation Baseline & Release Gate ===")
    print(f"Loading golden dataset: {args.golden_path}")
    golden_data = json.loads(args.golden_path.read_text(encoding="utf-8"))
    cases = golden_data.get("cases", [])
    golden_sha256 = compute_file_sha256(args.golden_path)
    print(f"Loaded {len(cases)} retrieval cases (SHA-256: {golden_sha256[:16]}...).")

    settings = get_settings()
    collection_name = settings.chroma_collection_name
    embedding_model = settings.embedding_model
    col_count = get_collection_count()

    print(f"ChromaDB Collection: {collection_name} ({col_count} docs)")
    print(f"Embedding Model: {embedding_model}")
    print(f"Evaluating top_k={args.top_k}...")

    start_time = time.perf_counter()
    case_results, summary = run_retrieval_evaluation(cases, top_k=args.top_k)
    elapsed = time.perf_counter() - start_time

    # Evaluate gate using pure function
    gate_decision = evaluate_retrieval_gate(summary, thresholds)

    meta = {
        "timestamp": datetime.now(UTC).isoformat(),
        "collection": collection_name,
        "embedding_model": embedding_model,
        "collection_count": col_count,
        "top_k": args.top_k,
        "elapsed_seconds": round(elapsed, 2),
        "golden_sha256": golden_sha256,
    }

    report_data = {
        "meta": meta,
        "gate_status": "PASSED" if gate_decision.passed else "FAILED",
        "thresholds": {
            "min_hit_rate_at_1": thresholds.min_hit_rate_at_1,
            "min_recall_at_1": thresholds.min_recall_at_1,
            "min_hit_rate_at_3": thresholds.min_hit_rate_at_3,
            "min_recall_at_3": thresholds.min_recall_at_3,
            "min_hit_rate_at_5": thresholds.min_hit_rate_at_5,
            "min_recall_at_5": thresholds.min_recall_at_5,
            "min_mrr_at_5": thresholds.min_mrr_at_5,
            "min_ndcg_at_5": thresholds.min_ndcg_at_5,
            "min_d_typo_hit_rate_at_1": thresholds.min_d_typo_hit_rate_at_1,
            "min_b_exact_hit_rate_at_1": thresholds.min_b_exact_hit_rate_at_1,
            "max_cross_tenant_leaks": thresholds.max_cross_tenant_leaks,
            "max_forbidden_doc_leaks": thresholds.max_forbidden_doc_leaks,
            "max_policy_authority_violations": thresholds.max_policy_authority_violations,
        },
        "metric_checks": [
            {
                "metric": c.metric_name,
                "measured": c.measured_value,
                "threshold": c.threshold_value,
                "comparison": c.comparison_op,
                "passed": c.passed,
                "is_safety": c.is_safety_invariant,
            }
            for c in gate_decision.checks
        ],
        "failure_reasons": gate_decision.reasons,
        "summary": summary,
        "case_results": [
            {
                "case_id": r.case_id,
                "category_group": r.category_group,
                "query": r.query,
                "expected_ids": r.expected_ids,
                "acceptable_ids": r.acceptable_ids,
                "forbidden_ids": r.forbidden_ids,
                "retrieved_ids": r.retrieved_ids,
                "first_hit_rank": r.first_hit_rank,
                "hit_at_1": r.hit_at_1,
                "hit_at_5": r.hit_at_5,
                "recall_at_5": r.recall_at_5,
                "reciprocal_rank": r.reciprocal_rank,
                "ndcg_at_5": r.ndcg_at_5,
                "forbidden_leak_count": r.forbidden_leak_count,
                "cross_tenant_leak_count": r.cross_tenant_leak_count,
                "policy_authority_violation": r.policy_authority_violation,
                "failure_category": r.failure_category,
                "relevance_scores": r.relevance_scores,
            }
            for r in case_results
        ],
    }

    # Write output files
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote JSON baseline report: {args.output_json}")

    md_report = generate_markdown_report(summary, gate_decision, case_results, meta)
    args.output_md.write_text(md_report, encoding="utf-8")
    print(f"Wrote Markdown baseline report: {args.output_md}")

    d_typo_measured = summary.get("category_summary", {}).get("D_typo_informal", {}).get("hit_at_1", 0.0)
    b_exact_measured = summary.get("category_summary", {}).get("B_exact_token", {}).get("hit_at_1", 0.0)

    # Print console summary
    print("\n" + "=" * 65)
    print("RETRIEVAL REGRESSION GATE EVALUATION")
    print("=" * 65)
    print(f"Total Cases:     {summary['total_cases']} ({summary['scorable_cases']} scorable)")
    print(f"HitRate@1:       {summary['hit_rate_at_1']:.1%} (floor >= {thresholds.min_hit_rate_at_1:.1%})")
    print(f"Recall@1:        {summary['recall_at_1']:.1%} (floor >= {thresholds.min_recall_at_1:.1%})")
    print(f"HitRate@3:       {summary['hit_rate_at_3']:.1%} (floor >= {thresholds.min_hit_rate_at_3:.1%})")
    print(f"Recall@3:        {summary['recall_at_3']:.1%} (floor >= {thresholds.min_recall_at_3:.1%})")
    print(f"HitRate@5:       {summary['hit_rate_at_5']:.1%} (floor >= {thresholds.min_hit_rate_at_5:.1%})")
    print(f"Recall@5:        {summary['recall_at_5']:.1%} (floor >= {thresholds.min_recall_at_5:.1%})")
    print(f"MRR@5:           {summary['mrr_at_5']:.3f} (floor >= {thresholds.min_mrr_at_5:.3f})")
    print(f"nDCG@5:          {summary['ndcg_at_5']:.3f} (floor >= {thresholds.min_ndcg_at_5:.3f})")
    print(f"D_typo Hit@1:    {d_typo_measured:.1%} (floor >= {thresholds.min_d_typo_hit_rate_at_1:.1%})")
    print(f"B_exact Hit@1:   {b_exact_measured:.1%} (floor >= {thresholds.min_b_exact_hit_rate_at_1:.1%})")
    print(f"Cross-Tenant:    {summary['cross_tenant_leak_count']} (MUST BE 0)")
    print(f"Forbidden Leaks: {summary['forbidden_doc_retrieval_count']} (MUST BE 0)")
    print(f"Policy Violate:  {summary['policy_authority_violation_count']} (MUST BE 0)")
    print(f"Time Taken:      {elapsed:.2f}s")
    print("=" * 65)

    if gate_decision.passed:
        print("\n>>> RETRIEVAL GATE STATUS: PASSED <<<")
        return 0
    else:
        print("\n>>> RETRIEVAL GATE STATUS: FAILED <<<", file=sys.stderr)
        for r in gate_decision.reasons:
            print(f"  - {r}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
