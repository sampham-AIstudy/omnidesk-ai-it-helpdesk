"""Audit exact unrounded nDCG@5 across all files and functions."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from eval.retrieval_metrics import evaluate_single_case, summarize_retrieval_evaluation
from src.services.rag_service import _rag_query_cache, search_similar

# 1. Check JSON files in eval/results/
print("=== 1. Existing JSON Artifacts in eval/results/ ===")
for p in sorted((ROOT_DIR / "eval" / "results").glob("*.json")):
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if "summary" in data and "ndcg_at_5" in data["summary"]:
            print(f"{p.name:<35}: summary.ndcg_at_5 = {data['summary']['ndcg_at_5']:.8f}")
        elif "experiments" in data:
            for exp_k, exp_v in data["experiments"].items():
                print(f"{p.name} [{exp_k}]: ndcg_at_5 = {exp_v.get('ndcg_at_5')}")
    except Exception as e:
        pass

# 2. Run live retrieval pipeline
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

print("\n=== 2. Live Retrieval Evaluation Results ===")
print(f"summary['ndcg_at_5'] raw float: {summary['ndcg_at_5']!r}")
print(f"summary['ndcg_at_5'] formatted .4f: {summary['ndcg_at_5']:.4f}")
print(f"summary['ndcg_at_5'] formatted .3f: {summary['ndcg_at_5']:.3f}")
print(f"summary['ndcg_at_5'] formatted .6f: {summary['ndcg_at_5']:.6f}")

print("\nPer-case nDCG@5 for all 39 scorable cases:")
scorable = [r for r in results if r.expected_ids or r.acceptable_ids]
for r in scorable:
    if "ambiguous" not in r.category_group.lower() and "no_evidence" not in r.category_group.lower():
        print(f"  {r.case_id} ({r.category_group}): first_hit_rank={r.first_hit_rank}, ndcg@5={r.ndcg_at_5:.6f}")
