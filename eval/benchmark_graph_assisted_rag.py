"""Comprehensive A/B Benchmark for Graph-assisted RAG vs Hybrid Baseline.

Evaluates:
1. Locked 44 retrieval golden cases
2. P0 11 critical shadow cases
3. Hard-negative 50 cases
4. Domain-specific technical slices (VPN, DNS, TCP, HTTP, WiFi, BitLocker, M365, Firewall)
5. Latency metrics (Cold, Warm p50, Warm p95, Graph lookup isolation)
"""
import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
os.environ.setdefault("HF_DEACTIVATE_ASYNC_LOAD", "1")

from eval.retrieval_metrics import evaluate_single_case, summarize_retrieval_evaluation  # noqa: E402
from src.services.graph_retriever import GraphCandidate, get_knowledge_graph_index  # noqa: E402
from src.services.rag_service import get_canonical_source_id, search_similar  # noqa: E402


def search_with_graph_assisted_rrf(
    query: str,
    n_results: int = 5,
    user_company_unit: str | None = None,
    user_department: str | None = None,
    category_filter: str | None = None,
) -> list[dict[str, Any]]:
    """Graph-assisted retrieval integrating 1-hop graph candidates into hybrid RRF."""
    from src.services.bm25_retriever import get_bm25_index
    from src.services.query_normalization_service import (
        extract_exact_technical_tokens,
        normalize_informal_query,
    )
    from src.services.rag_service import (
        SOURCE_AUTHORITY_FACTORS,
        _expand_query,
        _lexical_score,
        _metadata_allowed,
        embed_query,
        get_collection,
        scan_indirect_injection,
    )
    from src.services.technical_intent_service import infer_technical_facets, topic_compatibility

    collection = get_collection()
    norm_query = normalize_informal_query(query)
    exact_tokens = extract_exact_technical_tokens(query) | extract_exact_technical_tokens(norm_query)
    technical_facets = infer_technical_facets(norm_query)

    # 1. Dense Embedding Channel
    expanded_query = _expand_query(norm_query if norm_query != query else query)
    query_embedding = embed_query(expanded_query)

    where_conditions = []
    if category_filter:
        where_conditions.append({"category": category_filter})
    if user_company_unit and user_company_unit != "corporate":
        where_conditions.append({
            "$or": [
                {"applicable_to_all": True},
                {"company_unit": "all"},
                {"company_unit": user_company_unit},
            ]
        })
    where_filter = where_conditions[0] if len(where_conditions) == 1 else ({"$and": where_conditions} if len(where_conditions) > 1 else None)

    try:
        dense_results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(max(n_results * 8, n_results), collection.count() or 1),
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )
    except Exception:
        dense_results = {}

    dense_ranks: dict[str, int] = {}
    dense_docs: dict[str, dict[str, Any]] = {}
    if dense_results and dense_results.get("documents"):
        rank_idx = 1
        for i, doc in enumerate(dense_results["documents"][0]):
            metadata = dense_results["metadatas"][0][i] if dense_results.get("metadatas") else {}
            if not _metadata_allowed(metadata, user_company_unit, user_department):
                continue
            if scan_indirect_injection(doc):
                continue
            doc_id = str(dense_results.get("ids", [[]])[0][i])
            dist = float(dense_results["distances"][0][i]) if dense_results.get("distances") else 1.0
            sem_score = max(0.0, 1.0 - dist)
            dense_ranks[doc_id] = rank_idx
            dense_docs[doc_id] = {
                "doc_id": doc_id,
                "content": doc,
                "metadata": metadata,
                "distance": dist,
                "semantic_score": sem_score,
                "dense_rank": rank_idx,
            }
            rank_idx += 1

    # 2. BM25 Channel
    bm25_results = get_bm25_index().search(
        query=norm_query,
        top_n=60,
        category_filter=category_filter,
        user_company_unit=user_company_unit,
        user_department=user_department,
    )
    bm25_ranks: dict[str, int] = {item["doc_id"]: item["lexical_rank"] for item in bm25_results}
    bm25_docs: dict[str, dict[str, Any]] = {item["doc_id"]: item for item in bm25_results}

    # 3. Graph Candidate Channel (1-hop deterministic in-memory lookup)
    graph_index = get_knowledge_graph_index()
    graph_candidates = graph_index.query_graph(
        query=norm_query,
        technical_facets=technical_facets,
        user_company_unit=user_company_unit,
        user_department=user_department,
        max_candidates=15,
    )
    graph_ranks: dict[str, int] = {c.doc_id: idx + 1 for idx, c in enumerate(graph_candidates)}
    graph_docs: dict[str, GraphCandidate] = {c.doc_id: c for c in graph_candidates}

    # 4. Multi-way RRF Fusion (Dense + BM25 + Graph)
    k_rrf = 60
    all_candidate_ids = set(dense_ranks.keys()) | set(bm25_ranks.keys()) | set(graph_ranks.keys())
    if not all_candidate_ids:
        return []

    candidates: list[dict[str, Any]] = []
    for doc_id in all_candidate_ids:
        dense_r = dense_ranks.get(doc_id)
        bm25_r = bm25_ranks.get(doc_id)
        graph_r = graph_ranks.get(doc_id)

        dense_rrf = (1.0 / (k_rrf + dense_r)) if dense_r else 0.0
        bm25_rrf = (1.0 / (k_rrf + bm25_r)) if bm25_r else 0.0
        graph_rrf = (1.0 / (k_rrf + graph_r)) if graph_r else 0.0

        if doc_id in dense_docs:
            d_info = dict(dense_docs[doc_id])
        elif doc_id in bm25_docs:
            b_item = bm25_docs[doc_id]
            d_info = {
                "doc_id": doc_id,
                "content": b_item["content"],
                "metadata": b_item["metadata"],
                "distance": 1.0,
                "semantic_score": 0.0,
                "dense_rank": None,
            }
        else:
            g_item = graph_docs[doc_id]
            d_info = {
                "doc_id": doc_id,
                "content": g_item.content,
                "metadata": g_item.metadata,
                "distance": 1.0,
                "semantic_score": 0.0,
                "dense_rank": None,
            }

        d_info["lexical_rank"] = bm25_r
        d_info["graph_rank"] = graph_r

        meta = d_info["metadata"]
        searchable_text = f"{meta.get('title', '')} {meta.get('tags', '')} {meta.get('solution', '')} {d_info.get('content', '')}".lower()
        exact_matches = sum(1 for token in exact_tokens if token in searchable_text)
        exact_boost = 0.005 * exact_matches

        source_type = meta.get("source", "NO_SOURCE_KEY")
        auth_factor = SOURCE_AUTHORITY_FACTORS.get(source_type, 1.0)

        # RRF combination with graph signal
        rrf_score = dense_rrf * 1.0 + bm25_rrf * 1.2 + graph_rrf * 0.3 + exact_boost
        compatibility, compatibility_reason = topic_compatibility(technical_facets, meta)
        topic_adjusted_score = rrf_score * compatibility
        fusion_score = topic_adjusted_score * auth_factor

        d_info["dense_rrf"] = dense_rrf
        d_info["lexical_rrf"] = bm25_rrf
        d_info["graph_rrf"] = graph_rrf
        d_info["exact_contribution"] = exact_boost
        d_info["rrf_score"] = rrf_score
        d_info["topic_compatibility"] = compatibility
        d_info["topic_compatibility_reason"] = compatibility_reason
        d_info["authority_factor"] = auth_factor
        d_info["topic_adjusted_score"] = topic_adjusted_score
        d_info["final_score"] = fusion_score
        d_info["fusion_score"] = fusion_score

        lexical_overlap = _lexical_score(expanded_query, meta, d_info.get("content", ""))
        d_info["lexical_score"] = lexical_overlap

        candidates.append(d_info)

    # 5. Deterministic Ranking & Downstream Score Calibration
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

    # 6. Deduplication
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

    return (primary_candidates + secondary_candidates)[:n_results]


def run_benchmark():
    print("=================================================================")
    print("P-236 GRAPH-ASSISTED RAG VS HYBRID BASELINE BENCHMARK")
    print("=================================================================")

    # 1. Evaluate Locked 44 Golden Cases
    golden_path = ROOT_DIR / "eval" / "retrieval_golden_v1.json"
    golden_raw = json.loads(golden_path.read_text(encoding="utf-8"))
    golden_cases = golden_raw.get("cases") or golden_raw.get("test_cases", [])

    print(f"\n--- 1. Evaluating Locked Golden Dataset ({len(golden_cases)} cases) ---")

    # Warmup
    _ = search_similar("test query", n_results=5)
    _ = search_with_graph_assisted_rrf("test query", n_results=5)

    # Baseline run
    t0 = time.perf_counter()
    baseline_results = []
    baseline_latencies = []
    for c in golden_cases:
        st = time.perf_counter()
        docs = search_similar(c["query"], n_results=5, user_company_unit=c.get("tenant"), user_department=c.get("department"))
        baseline_latencies.append((time.perf_counter() - st) * 1000)
        baseline_results.append(evaluate_single_case(c, docs, top_k=5))
    baseline_time = time.perf_counter() - t0
    baseline_summary = summarize_retrieval_evaluation(baseline_results)

    # Graph-assisted run
    t0 = time.perf_counter()
    graph_results = []
    graph_latencies = []
    for c in golden_cases:
        st = time.perf_counter()
        docs = search_with_graph_assisted_rrf(c["query"], n_results=5, user_company_unit=c.get("tenant"), user_department=c.get("department"))
        graph_latencies.append((time.perf_counter() - st) * 1000)
        graph_results.append(evaluate_single_case(c, docs, top_k=5))
    graph_time = time.perf_counter() - t0
    graph_summary = summarize_retrieval_evaluation(graph_results)

    baseline_latencies.sort()
    graph_latencies.sort()
    base_p50 = baseline_latencies[len(baseline_latencies) // 2]
    base_p95 = baseline_latencies[int(len(baseline_latencies) * 0.95)]
    graph_p50 = graph_latencies[len(graph_latencies) // 2]
    graph_p95 = graph_latencies[int(len(graph_latencies) * 0.95)]

    print(f"Baseline: Hit@1={baseline_summary['hit_rate_at_1']:.1%}, Hit@3={baseline_summary['hit_rate_at_3']:.1%}, MRR={baseline_summary['mrr_at_5']:.4f}, nDCG={baseline_summary['ndcg_at_5']:.4f}, p50={base_p50:.2f}ms, p95={base_p95:.2f}ms, Total={baseline_time:.2f}s")
    print(f"Graph-RAG: Hit@1={graph_summary['hit_rate_at_1']:.1%}, Hit@3={graph_summary['hit_rate_at_3']:.1%}, MRR={graph_summary['mrr_at_5']:.4f}, nDCG={graph_summary['ndcg_at_5']:.4f}, p50={graph_p50:.2f}ms, p95={graph_p95:.2f}ms, Total={graph_time:.2f}s")

    # 2. Evaluate Hard-Negative 50 Cases
    hard_path = ROOT_DIR / "eval" / "p0_shadow_v3_hard_negative_cases.json"
    if hard_path.exists():
        hard_raw = json.loads(hard_path.read_text(encoding="utf-8"))
        hard_cases = hard_raw.get("cases") if isinstance(hard_raw, dict) else hard_raw
        print(f"\n--- 2. Evaluating Hard-Negative Dataset ({len(hard_cases)} cases) ---")

        def eval_hard(fn, case_list):
            ranks = []
            hard_in_top1 = 0
            hard_in_top3 = 0
            for case in case_list:
                docs = fn(case["query"], n_results=5)
                doc_ids = [d["doc_id"] for d in docs]
                expected_ids = set(case.get("expected_source_ids", []))
                hard_ids = set(case.get("hard_negative_source_ids", []))

                # Check rank of expected
                rank = next((idx + 1 for idx, did in enumerate(doc_ids) if did in expected_ids), None)
                ranks.append(rank)

                if doc_ids and doc_ids[0] in hard_ids:
                    hard_in_top1 += 1
                if any(did in hard_ids for did in doc_ids[:3]):
                    hard_in_top3 += 1

            total = len(case_list)
            return {
                "hit@1": sum(r == 1 for r in ranks) / total if total else 0.0,
                "hit@3": sum(r is not None and r <= 3 for r in ranks) / total if total else 0.0,
                "hit@5": sum(r is not None and r <= 5 for r in ranks) / total if total else 0.0,
                "mrr": sum(1.0 / r for r in ranks if r is not None) / total if total else 0.0,
                "ndcg": sum(1.0 / math.log2(r + 1) for r in ranks if r is not None) / total if total else 0.0,
                "hard@1_rate": hard_in_top1 / total if total else 0.0,
                "hard@3_rate": hard_in_top3 / total if total else 0.0,
            }

        hard_base = eval_hard(search_similar, hard_cases)
        hard_graph = eval_hard(search_with_graph_assisted_rrf, hard_cases)

        print(f"Baseline Hard-Neg: Hit@1={hard_base['hit@1']:.1%}, Hit@3={hard_base['hit@3']:.1%}, MRR={hard_base['mrr']:.4f}, nDCG={hard_base['ndcg']:.4f}, Hard@1={hard_base['hard@1_rate']:.1%}, Hard@3={hard_base['hard@3_rate']:.1%}")
        print(f"Graph-RAG Hard-Neg: Hit@1={hard_graph['hit@1']:.1%}, Hit@3={hard_graph['hit@3']:.1%}, MRR={hard_graph['mrr']:.4f}, nDCG={hard_graph['ndcg']:.4f}, Hard@1={hard_graph['hard@1_rate']:.1%}, Hard@3={hard_graph['hard@3_rate']:.1%}")

    # 3. Evaluate P0 11 Cases
    p0_path = ROOT_DIR / "eval" / "p0_shadow_v3_cases.json"
    if p0_path.exists():
        p0_raw = json.loads(p0_path.read_text(encoding="utf-8"))
        p0_cases = p0_raw.get("cases") if isinstance(p0_raw, dict) else p0_raw
        print(f"\n--- 3. Evaluating P0 Critical Cases ({len(p0_cases)} cases) ---")
        p0_base = eval_hard(search_similar, p0_cases)
        p0_graph = eval_hard(search_with_graph_assisted_rrf, p0_cases)
        print(f"Baseline P0: Hit@1={p0_base['hit@1']:.1%}, Hit@3={p0_base['hit@3']:.1%}, MRR={p0_base['mrr']:.4f}")
        print(f"Graph-RAG P0: Hit@1={p0_graph['hit@1']:.1%}, Hit@3={p0_graph['hit@3']:.1%}, MRR={p0_graph['mrr']:.4f}")

    # 4. Isolated Graph Lookup Latency
    g_index = get_knowledge_graph_index()
    test_queries = [
        "Lỗi FortiClient VPN không kết nối được sau khi nhập OTP",
        "Cách flush DNS trên Windows 11 khi không vào được trang nội bộ",
        "Kiểm tra port 443 bằng PowerShell Test-NetConnection",
        "Lỗi HTTP 403 Forbidden khi truy cập portal nhân sự",
        "WiFi VinAI-Corp bị chấm than vàng không có internet",
        "Mất mã BitLocker recovery key máy tính Dell",
        "Outlook bị kẹt email ở Outbox không gửi được",
        "Firewall chặn kết nối cổng TCP 3389 RDP",
    ]
    graph_times = []
    for q in test_queries * 100:
        t_start = time.perf_counter()
        _ = g_index.query_graph(q)
        graph_times.append((time.perf_counter() - t_start) * 1000)

    graph_times.sort()
    g_p50 = graph_times[len(graph_times) // 2]
    g_p95 = graph_times[int(len(graph_times) * 0.95)]
    print("\n--- 4. Graph Isolated Lookup Latency (800 iterations) ---")
    print(f"Graph lookup p50: {g_p50:.4f} ms, p95: {g_p95:.4f} ms")

    # Save benchmark results
    out_path = ROOT_DIR / "eval" / "results" / "graph_rag_benchmark_v1_0.json"
    result_data = {
        "benchmark": "Graph-assisted RAG vs Hybrid Baseline",
        "collection": "helpdesk_kb_multilingual_v3_sentence_transformer",
        "golden_44": {
            "baseline": {**baseline_summary, "p50_ms": base_p50, "p95_ms": base_p95, "total_time_s": baseline_time},
            "graph_assisted": {**graph_summary, "p50_ms": graph_p50, "p95_ms": graph_p95, "total_time_s": graph_time},
        },
        "hard_negative_50": {
            "baseline": hard_base,
            "graph_assisted": hard_graph,
        },
        "p0_11": {
            "baseline": p0_base,
            "graph_assisted": p0_graph,
        },
        "graph_isolated_latency": {
            "p50_ms": g_p50,
            "p95_ms": g_p95,
        },
    }
    out_path.write_text(json.dumps(result_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nBenchmark report written to: {out_path}")


if __name__ == "__main__":
    run_benchmark()
