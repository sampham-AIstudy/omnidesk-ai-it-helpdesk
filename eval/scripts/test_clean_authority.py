"""Evaluate correct canonical source deduplication and authority ranking."""
from __future__ import annotations

import json
import re
import sys
import urllib.parse
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from eval.retrieval_metrics import evaluate_single_case, summarize_retrieval_evaluation
from src.services.bm25_retriever import get_bm25_index
from src.services.query_normalization_service import (
    extract_exact_technical_tokens,
    normalize_informal_query,
)
from src.services.rag_service import (
    _expand_query,
    _lexical_score,
    _metadata_allowed,
    embed_query,
    get_collection,
    scan_indirect_injection,
)

SOURCE_AUTHORITY_FACTORS = {
    "internal_curated_kb": 1.40,
    "approved_internal_source": 1.20,
    "official_web_documentation": 1.00,
    "historical_resolved_ticket": 0.95,
    "NO_SOURCE_KEY": 0.90,
}


def get_canonical_source_id(doc_id: str, metadata: dict[str, Any] | None = None) -> str:
    meta = metadata or {}
    source_url = meta.get("source_url", "").strip()
    if source_url:
        try:
            parsed = urllib.parse.urlparse(source_url)
            norm_url = f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{parsed.path.rstrip('/')}"
            if parsed.query:
                norm_url = f"{norm_url}?{parsed.query}"
            return f"url:{norm_url}"
        except Exception:
            return f"url:{source_url.lower().rstrip('/')}"

    if meta.get("parent_id"):
        return f"parent:{meta['parent_id']}"
    if meta.get("canonical_source_id"):
        return f"canon:{meta['canonical_source_id']}"

    if doc_id.startswith("web-"):
        m = re.match(r"^(web-.+)-\d{3,}$", doc_id)
        if m:
            return f"web_base:{m.group(1)}"

    if doc_id.startswith("kb-"):
        m = re.match(r"^(kb-\d+)[_-](?:chunk|part|c)\d+$", doc_id, re.IGNORECASE)
        if m:
            return f"kb_base:{m.group(1)}"
        return f"kb:{doc_id}"

    return doc_id


def search_authority(
    query: str,
    n_results: int = 5,
    category_filter: str | None = None,
    user_company_unit: str | None = None,
    user_department: str | None = None,
    *,
    authority_map: dict[str, float] = SOURCE_AUTHORITY_FACTORS,
    dedup: bool = True,
) -> list[dict]:
    collection = get_collection()
    norm_query = normalize_informal_query(query)
    exact_tokens = extract_exact_technical_tokens(query) | extract_exact_technical_tokens(norm_query)

    # 1. Dense retrieval
    expanded_query = _expand_query(norm_query if norm_query != query else query)
    query_embedding = embed_query(expanded_query)

    where_conditions = []
    if category_filter:
        where_conditions.append({"category": category_filter})
    if user_company_unit and user_company_unit != "corporate":
        where_conditions.append({"$or": [{"applicable_to_all": True}, {"company_unit": user_company_unit}, {"company_unit": "all"}]})

    where_filter = None
    if len(where_conditions) == 1:
        where_filter = where_conditions[0]
    elif len(where_conditions) > 1:
        where_filter = {"$and": where_conditions}

    dense_candidates_raw = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(collection.count(), n_results * 8),
        where=where_filter,
        include=["documents", "metadatas", "distances"],
    )

    dense_docs = []
    if dense_candidates_raw and dense_candidates_raw.get("documents"):
        raw_docs = dense_candidates_raw["documents"][0]
        raw_metas = dense_candidates_raw["metadatas"][0]
        raw_ids = dense_candidates_raw["ids"][0]
        raw_dists = dense_candidates_raw["distances"][0]

        for idx, doc_text in enumerate(raw_docs):
            meta = raw_metas[idx]
            if not _metadata_allowed(meta, user_company_unit, user_department) or scan_indirect_injection(doc_text):
                continue
            dist = raw_dists[idx]
            dense_docs.append({
                "doc_id": raw_ids[idx],
                "content": doc_text,
                "metadata": meta,
                "semantic_score": max(0.0, 1.0 - dist),
                "distance": dist,
            })

    dense_ranks = {d["doc_id"]: rank for rank, d in enumerate(dense_docs, 1)}

    # 2. BM25 retrieval
    bm25_index = get_bm25_index()
    bm25_results = bm25_index.search(
        norm_query,
        top_n=60,
        category_filter=category_filter,
        user_company_unit=user_company_unit,
        user_department=user_department,
    )
    bm25_ranks = {r["doc_id"]: r["lexical_rank"] for r in bm25_results}
    bm25_docs_by_id = {r["doc_id"]: r for r in bm25_results}

    # 3. Candidate pool & RRF Fusion
    all_doc_ids = set(dense_ranks.keys()) | set(bm25_ranks.keys())
    k_rrf = 60
    candidates = []

    for doc_id in all_doc_ids:
        dense_r = dense_ranks.get(doc_id)
        bm25_r = bm25_ranks.get(doc_id)

        dense_rrf = 1.0 / (k_rrf + dense_r) if dense_r is not None else 0.0
        bm25_rrf = 1.0 / (k_rrf + bm25_r) if bm25_r is not None else 0.0

        if doc_id in dense_ranks:
            d_info = next(d for d in dense_docs if d["doc_id"] == doc_id).copy()
        else:
            b_info = bm25_docs_by_id[doc_id]
            d_info = {
                "doc_id": doc_id,
                "content": b_info["content"],
                "metadata": b_info["metadata"],
                "semantic_score": 0.0,
                "distance": 1.0,
            }

        d_info["dense_rank"] = dense_r
        d_info["lexical_rank"] = bm25_r

        meta = d_info["metadata"]
        searchable_text = f"{meta.get('title', '')} {meta.get('tags', '')} {meta.get('solution', '')} {d_info.get('content', '')}".lower()
        exact_matches = sum(1 for token in exact_tokens if token in searchable_text)
        exact_boost = 0.005 * exact_matches

        source_type = meta.get("source", "NO_SOURCE_KEY")
        auth_factor = authority_map.get(source_type, 1.0)

        fusion_score = (dense_rrf * 1.0 + bm25_rrf * 1.2 + exact_boost) * auth_factor
        d_info["fusion_score"] = fusion_score

        lexical_overlap = _lexical_score(expanded_query, meta, d_info.get("content", ""))
        d_info["lexical_score"] = lexical_overlap
        candidates.append(d_info)

    # 4. Calibrate relevance_score
    candidates.sort(key=lambda x: (-x["fusion_score"], x["doc_id"]))
    max_fusion = candidates[0]["fusion_score"] if candidates else 1.0

    for item in candidates:
        confidence_base = max(
            item.get("semantic_score", 0.0),
            item.get("lexical_score", 0.0),
            0.75 if item.get("fusion_score", 0.0) == max_fusion else 0.50,
        )
        relative_rrf = (item["fusion_score"] / max_fusion) if max_fusion > 0 else 0.0
        item["relevance_score"] = min(1.0, confidence_base * relative_rrf)

    candidates.sort(key=lambda x: (-x["relevance_score"], -x["fusion_score"], x["doc_id"]))

    # 5. Canonical Source Deduplication
    if dedup:
        seen_canonical: set[str] = set()
        primary_candidates: list[dict] = []
        secondary_candidates: list[dict] = []

        for item in candidates:
            canon_id = get_canonical_source_id(item["doc_id"], item.get("metadata", {}))
            if canon_id not in seen_canonical:
                seen_canonical.add(canon_id)
                primary_candidates.append(item)
            else:
                secondary_candidates.append(item)

        final_docs = (primary_candidates + secondary_candidates)[:n_results]
    else:
        final_docs = candidates[:n_results]

    return final_docs


def main():
    golden_path = ROOT_DIR / "eval" / "retrieval_golden_v1.json"
    golden_cases = json.load(open(golden_path, encoding="utf-8"))["cases"]

    results = []
    for c in golden_cases:
        docs = search_authority(
            c["query"],
            n_results=5,
            user_company_unit=c.get("tenant"),
            user_department=c.get("department"),
            authority_map=SOURCE_AUTHORITY_FACTORS,
            dedup=True,
        )
        res = evaluate_single_case(c, docs, top_k=5)
        results.append(res)

    s = summarize_retrieval_evaluation(results)
    print("=== Step 4 Authority-Aware + Canonical Deduplication Full Metrics ===")
    print(f"HitRate@1:      {s['hit_rate_at_1']:.1%} (target 100%)")
    print(f"Recall@1:       {s['recall_at_1']:.1%}")
    print(f"HitRate@3:      {s['hit_rate_at_3']:.1%} (target 100%)")
    print(f"HitRate@5:      {s['hit_rate_at_5']:.1%} (target 100%)")
    print(f"MRR@5:          {s['mrr_at_5']:.4f}")
    print(f"nDCG@5:         {s['ndcg_at_5']:.4f}")
    print(f"Cross-Tenant:   {s['cross_tenant_leak_count']}")
    print(f"Forbidden:      {s['forbidden_doc_retrieval_count']}")
    print(f"Policy Violate: {s['policy_authority_violation_count']}")

    print("\nCategory HitRate@1:")
    for cat, data in s["category_summary"].items():
        print(f"  {cat}: {data['hit_at_1']:.1%}")

    b02 = [r for r in results if r.case_id == "RET-B02"][0]
    print(f"\nRET-B02 Rank: {b02.first_hit_rank} (Expected Rank 1)")


if __name__ == "__main__":
    main()
