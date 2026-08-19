"""Find non-rank-1 cases under current hybrid search."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from eval.retrieval_metrics import evaluate_single_case, summarize_retrieval_evaluation
from src.services.rag_service import search_similar

golden = json.load(open(ROOT_DIR / "eval" / "retrieval_golden_v1.json", encoding="utf-8"))["cases"]
results = []
for c in golden:
    docs = search_similar(c["query"], n_results=10, user_company_unit=c.get("tenant"), user_department=c.get("department"))
    res = evaluate_single_case(c, docs, top_k=10)
    results.append(res)
    if not res.hit_at_1:
        top_meta = (docs[0].get("metadata") or {}) if docs else {}
        print(f"NON-RANK-1: {res.case_id} [{res.category_group}]")
        print(f"  Query: \"{res.query}\"")
        print(f"  Expected: {res.expected_ids} / Acceptable: {res.acceptable_ids}")
        print(f"  Rank 1 returned: {docs[0].get('doc_id')} ({top_meta.get('title')})")
        print(f"  First hit rank for expected doc: {res.first_hit_rank}")
        print("  All top-10 retrieved IDs:", [d.get("doc_id") for d in docs])
        print()

summary = summarize_retrieval_evaluation(results)
print("=== CURRENT HYBRID SUMMARY ===")
print(f"HitRate@1: {summary['hit_rate_at_1']:.1%} ({sum(1 for r in results if r.hit_at_1)}/{summary['scorable_cases']})")
print(f"HitRate@3: {summary['hit_rate_at_3']:.1%}")
print(f"HitRate@5: {summary['hit_rate_at_5']:.1%}")
print(f"MRR@5:     {summary['mrr_at_5']:.4f}")
print(f"nDCG@5:    {summary['ndcg_at_5']:.4f}")
for cat, cs in summary["category_summary"].items():
    print(f"  {cat:<25}: Hit@1={cs['hit_at_1']:.1%} ({cs['scorable_cases']} scorable)")
