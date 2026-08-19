"""Evaluate fine-grained authority factors across all golden test cases."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from eval.retrieval_metrics import evaluate_single_case, summarize_retrieval_evaluation
from eval.scripts.experiment_authority import search_custom

golden_path = ROOT_DIR / "eval" / "retrieval_golden_v1.json"
golden_cases = json.load(open(golden_path, encoding="utf-8"))["cases"]

print("Testing Authority Multipliers with and without Canonical Source Deduplication:")
print("-" * 110)
print(f"{'Config':<35} | {'Hit@1':<7} | {'Recall@1':<9} | {'Hit@3':<7} | {'Hit@5':<7} | {'MRR@5':<7} | {'nDCG@5':<7} | {'B_exact@1':<10} | {'RET-B02 Rank':<12}")
print("-" * 110)

weights = [1.10, 1.15, 1.20, 1.25, 1.30, 1.33, 1.35, 1.40, 1.45, 1.50]

for dedup in [False, True]:
    for w in weights:
        results = []
        for c in golden_cases:
            docs = search_custom(
                c["query"],
                n_results=5,
                category_filter=None,
                user_company_unit=c.get("tenant"),
                user_department=c.get("department"),
                authority_weight=w,
                collapse_duplicates=dedup,
            )
            res = evaluate_single_case(c, docs, top_k=5)
            results.append(res)

        s = summarize_retrieval_evaluation(results)
        b02_res = [r for r in results if r.case_id == "RET-B02"][0]
        b02_rank = b02_res.first_hit_rank if b02_res.first_hit_rank is not None else "Miss"
        b_exact_hit1 = s["category_summary"]["B_exact_token"]["hit_at_1"]

        label = f"{'Dedup+' if dedup else 'NoDedup+'}Auth({w:.2f})"
        print(f"{label:<35} | {s['hit_rate_at_1']:<7.1%} | {s['recall_at_1']:<9.1%} | {s['hit_rate_at_3']:<7.1%} | {s['hit_rate_at_5']:<7.1%} | {s['mrr_at_5']:<7.4f} | {s['ndcg_at_5']:<7.4f} | {b_exact_hit1:<10.1%} | Rank {b02_rank}")
