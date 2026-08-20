"""A/B retrieval evaluation for the immutable v2 KB and a v3 shadow collection."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eval.retrieval_metrics import evaluate_single_case, summarize_retrieval_evaluation  # noqa: E402
from src.services import bm25_retriever, rag_service  # noqa: E402


def _select_collection(name: str) -> None:
    """Switch only the in-process evaluator; no collection is created or modified."""
    rag_service.settings = rag_service.settings.model_copy(update={"chroma_collection_name": name})
    rag_service._collection = None
    rag_service._rag_query_cache.clear()
    bm25_retriever.invalidate_bm25_index()


def evaluate_collection(collection: str, cases: list[dict[str, Any]]) -> tuple[list, dict[str, Any]]:
    _select_collection(collection)
    results = []
    for case in cases:
        documents = rag_service.search_similar(
            query=case["query"], n_results=5, user_company_unit=case.get("tenant"),
            user_department=case.get("department"), use_reranker=False,
        )
        results.append(evaluate_single_case(case, documents, top_k=5))
    return results, summarize_retrieval_evaluation(results)


def _case_payload(result) -> dict[str, Any]:
    return {
        "id": result.case_id, "expected_source": result.expected_ids,
        "rank": result.first_hit_rank, "retrieved_ids": result.retrieved_ids,
        "hit_at_1": result.hit_at_1, "hit_at_3": result.hit_at_3, "hit_at_5": result.hit_at_5,
    }


def _metrics(summary: dict[str, Any]) -> dict[str, float]:
    return {name: summary[name] for name in (
        "hit_rate_at_1", "hit_rate_at_3", "hit_rate_at_5", "recall_at_1", "recall_at_3",
        "recall_at_5", "mrr_at_5", "ndcg_at_5",
    )}


def run_ab(*, canonical: str, shadow: str, locked_cases_path: Path, p0_cases_path: Path, output_path: Path) -> dict[str, Any]:
    locked_cases = json.loads(locked_cases_path.read_text(encoding="utf-8"))["cases"]
    p0_cases = json.loads(p0_cases_path.read_text(encoding="utf-8"))["cases"]
    v2_locked, v2_locked_summary = evaluate_collection(canonical, locked_cases)
    v3_locked, v3_locked_summary = evaluate_collection(shadow, locked_cases)
    v2_p0, v2_p0_summary = evaluate_collection(canonical, p0_cases)
    v3_p0, v3_p0_summary = evaluate_collection(shadow, p0_cases)
    comparisons = []
    for before, after in zip(v2_p0, v3_p0):
        if before.first_hit_rank is None and after.first_hit_rank is not None:
            change = "improved"
        elif before.first_hit_rank is not None and after.first_hit_rank is None:
            change = "regressed"
        elif before.first_hit_rank == after.first_hit_rank:
            change = "same"
        elif (after.first_hit_rank or 99) < (before.first_hit_rank or 99):
            change = "improved"
        else:
            change = "regressed"
        comparisons.append({"id": after.case_id, "expected_source": after.expected_ids,
                            "v2_rank": before.first_hit_rank, "v3_rank": after.first_hit_rank,
                            "outcome": change})
    baseline_regression = {
        metric: v3_locked_summary[metric] >= v2_locked_summary[metric]
        for metric in _metrics(v2_locked_summary)
    }
    safety = {
        "cross_tenant_leaks": v3_locked_summary["cross_tenant_leak_count"] + v3_p0_summary["cross_tenant_leak_count"],
        "forbidden_leaks": v3_locked_summary["forbidden_doc_retrieval_count"] + v3_p0_summary["forbidden_doc_retrieval_count"],
        "policy_violations": v3_locked_summary["policy_authority_violation_count"] + v3_p0_summary["policy_authority_violation_count"],
    }
    p0_improvements = sum(item["outcome"] == "improved" for item in comparisons)
    report = {
        "canonical_collection": canonical, "shadow_collection": shadow,
        "locked_dataset": str(locked_cases_path), "p0_dataset": str(p0_cases_path),
        "locked_baseline": {"v2": _metrics(v2_locked_summary), "v3": _metrics(v3_locked_summary),
                            "regression_check": baseline_regression},
        "p0_candidate": {"v2": _metrics(v2_p0_summary), "v3": _metrics(v3_p0_summary),
                           "per_case": comparisons, "improved_cases": p0_improvements},
        "safety": safety,
        "details": {"v2_locked": [_case_payload(item) for item in v2_locked],
                    "v3_locked": [_case_payload(item) for item in v3_locked],
                    "v2_p0": [_case_payload(item) for item in v2_p0],
                    "v3_p0": [_case_payload(item) for item in v3_p0]},
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical", default="helpdesk_kb_multilingual_v2_sentence_transformer")
    parser.add_argument("--shadow", default="helpdesk_kb_multilingual_v3_shadow")
    parser.add_argument("--locked-cases", type=Path, default=ROOT / "eval" / "retrieval_golden_v1.json")
    parser.add_argument("--p0-cases", type=Path, default=ROOT / "eval" / "p0_shadow_v3_cases.json")
    parser.add_argument("--output", type=Path, default=ROOT / "eval" / "results" / "p0_shadow_v3_ab.json")
    args = parser.parse_args()
    print(json.dumps(run_ab(canonical=args.canonical, shadow=args.shadow, locked_cases_path=args.locked_cases,
                            p0_cases_path=args.p0_cases, output_path=args.output), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
