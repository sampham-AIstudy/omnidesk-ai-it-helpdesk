"""Investigate exact reason for the slight difference in baseline MRR/nDCG."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from eval.retrieval_metrics import evaluate_single_case, summarize_retrieval_evaluation
from src.services.rag_service import (
    _expand_query,
    _lexical_score,
    _metadata_allowed,
    embed_query,
    get_collection,
    scan_indirect_injection,
)


def pure_dense_old_retriever(query: str, tenant: str | None = None, dept: str | None = None) -> list[dict]:
    col = get_collection()
    exp = _expand_query(query)
    q_emb = embed_query(exp)
    res = col.query(query_embeddings=[q_emb], n_results=40, include=["documents", "metadatas", "distances"])
    docs = []
    if res and res.get("documents"):
        for i, doc in enumerate(res["documents"][0]):
            meta = res["metadatas"][0][i]
            if not _metadata_allowed(meta, tenant, dept) or scan_indirect_injection(doc):
                continue
            dist = res["distances"][0][i]
            sem = max(0.0, 1.0 - dist)
            docs.append({
                "doc_id": res["ids"][0][i],
                "content": doc,
                "metadata": meta,
                "semantic_score": sem,
                "distance": dist,
            })
    for d in docs:
        lex = _lexical_score(exp, d["metadata"], d["content"])
        d["relevance_score"] = min(1.0, 0.82 * d["semantic_score"] + 0.35 * lex)
    docs.sort(key=lambda x: x["relevance_score"], reverse=True)
    return docs[:5]


def main():
    golden = json.load(open(ROOT_DIR / "eval" / "retrieval_golden_v1.json", encoding="utf-8"))["cases"]
    res_old = [
        evaluate_single_case(c, pure_dense_old_retriever(c["query"], c.get("tenant"), c.get("department")), top_k=5)
        for c in golden
    ]
    s_old = summarize_retrieval_evaluation(res_old)
    print(f"Pure Dense Old Baseline:")
    print(f"HitRate@1: {s_old['hit_rate_at_1']:.6f} ({sum(1 for r in res_old if r.hit_at_1)}/39)")
    print(f"HitRate@3: {s_old['hit_rate_at_3']:.6f} ({sum(1 for r in res_old if r.hit_at_3)}/39)")
    print(f"HitRate@5: {s_old['hit_rate_at_5']:.6f} ({sum(1 for r in res_old if r.hit_at_5)}/39)")
    print(f"MRR@5:     {s_old['mrr_at_5']:.6f}")
    print(f"nDCG@5:    {s_old['ndcg_at_5']:.6f}")

    for r in res_old:
        if r.first_hit_rank and r.first_hit_rank > 1:
            print(f"Case {r.case_id} [{r.category_group}]: rank={r.first_hit_rank}, 1/rank={r.reciprocal_rank:.4f}, ndcg5={r.ndcg_at_5:.4f}")


if __name__ == "__main__":
    main()
