"""Experiment with Authority-Aware Ranking & Canonical Source Deduplication."""
from __future__ import annotations

import json
import re
import sys
import time
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

# ---------------------------------------------------------------------------
# Source Authority Hierarchy
# ---------------------------------------------------------------------------
AUTHORITY_TIERS = {
    "internal_curated_kb": 1.25,        # Tier 1: Canonical Internal KB / Runbooks
    "approved_internal_source": 1.15,   # Tier 1.5: Internal source
    "historical_resolved_ticket": 0.95, # Tier 2: Episodic Ticket Resolutions
    "official_web_documentation": 1.00, # Tier 3: External Vendor Documentation
    "NO_SOURCE_KEY": 0.90,              # Tier 4: Uncategorized / Auto KB
}


def get_canonical_source_id(doc_id: str, metadata: dict[str, Any]) -> str:
    """Derive canonical logical document ID for deduplication."""
    meta = metadata or {}
    source_url = meta.get("source_url", "").strip()
    if source_url:
        return f"url:{source_url}"

    # For web chunks with format web-name-001
    if doc_id.startswith("web-"):
        # Match base name before chunk number
        base = re.sub(r"-\d+$", "", doc_id)
        return f"web_base:{base}"

    # For kb chunks
    if doc_id.startswith("kb-"):
        base = re.sub(r"-\d+$", "", doc_id)
        return f"kb_base:{base}"

    return doc_id


def search_custom(
    query: str,
    n_results: int = 5,
    category_filter: str | None = None,
    user_company_unit: str | None = None,
    user_department: str | None = None,
    *,
    authority_weight: float = 1.10,
    collapse_duplicates: bool = False,
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
        if authority_weight > 1.0 and source_type == "internal_curated_kb":
            auth_factor = authority_weight
        elif source_type in AUTHORITY_TIERS and authority_weight != 1.10:
            auth_factor = AUTHORITY_TIERS.get(source_type, 1.0)
        else:
            auth_factor = 1.10 if source_type == "internal_curated_kb" else 1.0

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

    # 5. Canonical deduplication / near-duplicate collapsing
    if collapse_duplicates:
        seen_canonical = set()
        deduped_candidates = []
        overflow_candidates = []
        for c in candidates:
            canon_id = get_canonical_source_id(c["doc_id"], c.get("metadata", {}))
            if canon_id not in seen_canonical:
                seen_canonical.add(canon_id)
                deduped_candidates.append(c)
            else:
                overflow_candidates.append(c)
        final_docs = (deduped_candidates + overflow_candidates)[:n_results]
    else:
        final_docs = candidates[:n_results]

    return final_docs


def run_experiment():
    golden_path = ROOT_DIR / "eval" / "retrieval_golden_v1.json"
    golden_cases = json.load(open(golden_path, encoding="utf-8"))["cases"]

    configs = [
        ("A. Locked Hybrid (Step 2)", 1.10, False),
        ("B. Authority Boost (1.25)", 1.25, False),
        ("C. Near-Doc Dedup Only", 1.10, True),
        ("D. Authority (1.25) + Dedup", 1.25, True),
    ]

    print("==========================================================================================")
    print(f"{'Metric':<22} | {'A. Locked Hybrid':<16} | {'B. Auth Boost 1.25':<18} | {'C. Dedup Only':<16} | {'D. Auth+Dedup':<16}")
    print("==========================================================================================")

    summaries = {}
    latencies = {}

    for name, auth_w, dedup in configs:
        results = []
        times = []
        for c in golden_cases:
            t0 = time.perf_counter()
            docs = search_custom(
                c["query"],
                n_results=5,
                category_filter=None,
                user_company_unit=c.get("tenant"),
                user_department=c.get("department"),
                authority_weight=auth_w,
                collapse_duplicates=dedup,
            )
            times.append((time.perf_counter() - t0) * 1000)
            res = evaluate_single_case(c, docs, top_k=5)
            results.append(res)

        s = summarize_retrieval_evaluation(results)
        summaries[name] = s
        times.sort()
        latencies[name] = {"med": times[len(times) // 2], "p95": times[int(len(times) * 0.95)]}

    for label, key, is_pct in [
        ("HitRate@1", "hit_rate_at_1", True),
        ("Recall@1", "recall_at_1", True),
        ("HitRate@3", "hit_rate_at_3", True),
        ("Recall@3", "recall_at_3", True),
        ("HitRate@5", "hit_rate_at_5", True),
        ("Recall@5", "recall_at_5", True),
        ("MRR@5", "mrr_at_5", False),
        ("nDCG@5", "ndcg_at_5", False),
    ]:
        v_a = f"{summaries['A. Locked Hybrid (Step 2)'][key]:.1%}" if is_pct else f"{summaries['A. Locked Hybrid (Step 2)'][key]:.4f}"
        v_b = f"{summaries['B. Authority Boost (1.25)'][key]:.1%}" if is_pct else f"{summaries['B. Authority Boost (1.25)'][key]:.4f}"
        v_c = f"{summaries['C. Near-Doc Dedup Only'][key]:.1%}" if is_pct else f"{summaries['C. Near-Doc Dedup Only'][key]:.4f}"
        v_d = f"{summaries['D. Authority (1.25) + Dedup'][key]:.1%}" if is_pct else f"{summaries['D. Authority (1.25) + Dedup'][key]:.4f}"
        print(f"{label:<22} | {v_a:<16} | {v_b:<18} | {v_c:<16} | {v_d:<16}")

    print("------------------------------------------------------------------------------------------")
    for cat in ["B_exact_token", "D_typo_informal", "A_semantic_paraphrase", "F_policy_authority", "I_hard_negative"]:
        v_a = f"{summaries['A. Locked Hybrid (Step 2)']['category_summary'][cat]['hit_at_1']:.1%}"
        v_b = f"{summaries['B. Authority Boost (1.25)']['category_summary'][cat]['hit_at_1']:.1%}"
        v_c = f"{summaries['C. Near-Doc Dedup Only']['category_summary'][cat]['hit_at_1']:.1%}"
        v_d = f"{summaries['D. Authority (1.25) + Dedup']['category_summary'][cat]['hit_at_1']:.1%}"
        print(f"{cat + ' Hit@1':<22} | {v_a:<16} | {v_b:<18} | {v_c:<16} | {v_d:<16}")

    print("------------------------------------------------------------------------------------------")
    print(f"{'Cross-Tenant Leaks':<22} | {summaries['A. Locked Hybrid (Step 2)']['cross_tenant_leak_count']:<16} | {summaries['B. Authority Boost (1.25)']['cross_tenant_leak_count']:<18} | {summaries['C. Near-Doc Dedup Only']['cross_tenant_leak_count']:<16} | {summaries['D. Authority (1.25) + Dedup']['cross_tenant_leak_count']:<16}")
    print(f"{'Forbidden Leaks':<22} | {summaries['A. Locked Hybrid (Step 2)']['forbidden_doc_retrieval_count']:<16} | {summaries['B. Authority Boost (1.25)']['forbidden_doc_retrieval_count']:<18} | {summaries['C. Near-Doc Dedup Only']['forbidden_doc_retrieval_count']:<16} | {summaries['D. Authority (1.25) + Dedup']['forbidden_doc_retrieval_count']:<16}")
    print(f"{'Policy Violations':<22} | {summaries['A. Locked Hybrid (Step 2)']['policy_authority_violation_count']:<16} | {summaries['B. Authority Boost (1.25)']['policy_authority_violation_count']:<18} | {summaries['C. Near-Doc Dedup Only']['policy_authority_violation_count']:<16} | {summaries['D. Authority (1.25) + Dedup']['policy_authority_violation_count']:<16}")
    print("------------------------------------------------------------------------------------------")
    print(f"{'Median Latency (ms)':<22} | {latencies['A. Locked Hybrid (Step 2)']['med']:<16.1f} | {latencies['B. Authority Boost (1.25)']['med']:<18.1f} | {latencies['C. Near-Doc Dedup Only']['med']:<16.1f} | {latencies['D. Authority (1.25) + Dedup']['med']:<16.1f}")
    print("==========================================================================================")


if __name__ == "__main__":
    run_experiment()
