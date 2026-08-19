"""Verify 3 consecutive runs of promoted authority-aware retrieval for determinism.

Performs case-by-case rank and retrieved-ID snapshot comparisons across runs.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from eval.retrieval_metrics import evaluate_single_case, summarize_retrieval_evaluation  # noqa: E402
from src.services.rag_service import _rag_query_cache, search_similar  # noqa: E402


def run_pipeline():
    _rag_query_cache.clear()
    golden_path = ROOT_DIR / "eval" / "retrieval_golden_v1.json"
    golden_cases = json.load(open(golden_path, encoding="utf-8"))["cases"]

    results = []
    for c in golden_cases:
        docs = search_similar(
            c["query"],
            n_results=5,
            user_company_unit=c.get("tenant"),
            user_department=c.get("department"),
        )
        res = evaluate_single_case(c, docs, top_k=5)
        results.append(res)

    summary = summarize_retrieval_evaluation(results)
    # Per-case snapshot of doc IDs and first hit rank
    case_snapshots = {
        r.case_id: {
            "retrieved_ids": r.retrieved_ids,
            "first_hit_rank": r.first_hit_rank,
            "hit_at_1": r.hit_at_1,
        }
        for r in results
    }
    return summary, case_snapshots


def main():
    print("Running 3 consecutive evaluation cycles with full per-case snapshot...")
    runs = []
    for i in range(1, 4):
        s, snapshots = run_pipeline()
        runs.append((s, snapshots))
        b02_rank = snapshots["RET-B02"]["first_hit_rank"]
        print(
            f"Run {i}: Hit@1={s['hit_rate_at_1']:.4f}, Recall@1={s['recall_at_1']:.4f}, "
            f"MRR@5={s['mrr_at_5']:.4f}, nDCG@5={s['ndcg_at_5']:.4f}, "
            f"B_exact@1={s['category_summary']['B_exact_token']['hit_at_1']:.4f}, "
            f"D_typo@1={s['category_summary']['D_typo_informal']['hit_at_1']:.4f}, "
            f"RET-B02_Rank={b02_rank}"
        )

    s1, snap1 = runs[0]
    s2, snap2 = runs[1]
    s3, snap3 = runs[2]

    # Global quality assertions
    assert s1["hit_rate_at_1"] == s2["hit_rate_at_1"] == s3["hit_rate_at_1"] == 1.0
    assert s1["recall_at_1"] == s2["recall_at_1"] == s3["recall_at_1"]
    assert s1["hit_rate_at_3"] == s2["hit_rate_at_3"] == s3["hit_rate_at_3"] == 1.0
    assert s1["hit_rate_at_5"] == s2["hit_rate_at_5"] == s3["hit_rate_at_5"] == 1.0
    assert s1["mrr_at_5"] == s2["mrr_at_5"] == s3["mrr_at_5"] == 1.0
    assert abs(s1["ndcg_at_5"] - s2["ndcg_at_5"]) < 1e-9
    assert abs(s1["ndcg_at_5"] - s3["ndcg_at_5"]) < 1e-9

    # Category-level assertions
    for cat in ["A_semantic_paraphrase", "B_exact_token", "C_multilingual", "D_typo_informal", "F_policy_authority", "G_tenant_isolation", "I_hard_negative"]:
        assert s1["category_summary"][cat]["hit_at_1"] == s2["category_summary"][cat]["hit_at_1"] == s3["category_summary"][cat]["hit_at_1"] == 1.0

    # Safety invariants
    assert s1["cross_tenant_leak_count"] == s2["cross_tenant_leak_count"] == s3["cross_tenant_leak_count"] == 0
    assert s1["forbidden_doc_retrieval_count"] == s2["forbidden_doc_retrieval_count"] == s3["forbidden_doc_retrieval_count"] == 0
    assert s1["policy_authority_violation_count"] == s2["policy_authority_violation_count"] == s3["policy_authority_violation_count"] == 0

    # Per-case exact ranking and retrieved ID equality across all 44 cases
    for case_id in snap1:
        assert snap1[case_id]["retrieved_ids"] == snap2[case_id]["retrieved_ids"] == snap3[case_id]["retrieved_ids"], (
            f"Non-deterministic retrieved IDs in case {case_id}!"
        )
        assert snap1[case_id]["first_hit_rank"] == snap2[case_id]["first_hit_rank"] == snap3[case_id]["first_hit_rank"], (
            f"Non-deterministic hit rank in case {case_id}!"
        )

    # Specific case check: RET-B02
    assert snap1["RET-B02"]["first_hit_rank"] == 1
    assert snap1["RET-B02"]["retrieved_ids"][0] == "kb-015"

    print("\n>>> DETERMINISM VERIFIED: 0.0000 variance across all 44 cases, retrieved IDs, and aggregate metrics! <<<")


if __name__ == "__main__":
    main()
