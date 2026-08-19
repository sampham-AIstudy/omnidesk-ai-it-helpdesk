"""Benchmark experiments comparing Locked Hybrid with Cross-Encoder Reranker (N=8, 12, 20)."""
from __future__ import annotations

import json
import logging
import math
import sys
import time
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sentence_transformers import CrossEncoder

from eval.retrieval_metrics import evaluate_single_case, summarize_retrieval_evaluation
from src.services.rag_service import search_similar

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load CrossEncoder locally
try:
    cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2", local_files_only=True)
    logger.info("Loaded CrossEncoder locally: cross-encoder/ms-marco-MiniLM-L-6-v2")
except Exception as exc:
    logger.warning(f"Could not load CrossEncoder locally: {exc}")
    cross_encoder = None


def search_with_reranker(
    query: str,
    top_k: int = 5,
    top_n_candidates: int = 12,
    tenant: str | None = None,
    dept: str | None = None,
    enabled: bool = True,
) -> tuple[list[dict], float]:
    """Retrieve hybrid candidates and optionally apply CrossEncoder reranking."""
    t0 = time.perf_counter()
    # 1. First stage: Hybrid search to get candidate pool (all security filtered)
    candidate_count = max(top_n_candidates, top_k)
    candidates = search_similar(
        query=query,
        n_results=candidate_count,
        user_company_unit=tenant,
        user_department=dept,
    )
    t_hybrid = time.perf_counter() - t0

    if not enabled or not cross_encoder or not candidates:
        return candidates[:top_k], t_hybrid * 1000

    # 2. Second stage: CrossEncoder rerank top_n candidates
    t_rerank_start = time.perf_counter()
    rerank_pool = candidates[:top_n_candidates]
    remaining_pool = candidates[top_n_candidates:]

    pairs = []
    for c in rerank_pool:
        meta = c.get("metadata", {}) or {}
        title = meta.get("title", "")
        solution = meta.get("solution", "")
        content = c.get("content", "")
        doc_text = f"{title}. {solution} {content}"[:512]
        pairs.append((query, doc_text))

    try:
        ce_scores = cross_encoder.predict(pairs)
        for idx, item in enumerate(rerank_pool):
            raw_ce = float(ce_scores[idx])
            # Sigmoid normalization for stable positive score
            sig_ce = 1.0 / (1.0 + math.exp(-raw_ce))
            item["cross_encoder_score"] = raw_ce
            item["ce_norm_score"] = sig_ce

            # Preference for internal curated KB authority
            meta = item.get("metadata", {}) or {}
            source_type = meta.get("source", "")
            auth_boost = 1.05 if source_type == "internal_curated_kb" else 1.0
            item["rerank_score"] = sig_ce * auth_boost

        rerank_pool.sort(key=lambda x: (-x["rerank_score"], -x.get("fusion_score", 0.0), x["doc_id"]))
    except Exception as exc:
        logger.warning(f"CrossEncoder prediction failed, falling back to hybrid ranking: {exc}")
        rerank_pool = candidates[:top_n_candidates]

    t_total = time.perf_counter() - t0
    final_docs = (rerank_pool + remaining_pool)[:top_k]
    return final_docs, t_total * 1000


def run_benchmark():
    golden_path = ROOT_DIR / "eval" / "retrieval_golden_v1.json"
    golden_cases = json.load(open(golden_path, encoding="utf-8"))["cases"]

    configs = [
        ("A_locked_hybrid", False, 0),
        ("B_hybrid_rerank_top8", True, 8),
        ("C_hybrid_rerank_top12", True, 12),
        ("D_hybrid_rerank_top20", True, 20),
    ]

    all_summaries = {}
    latencies = {}

    for name, enabled, top_n in configs:
        results = []
        case_latencies = []
        for c in golden_cases:
            docs, lat = search_with_reranker(
                c["query"],
                top_k=5,
                top_n_candidates=top_n,
                tenant=c.get("tenant"),
                dept=c.get("department"),
                enabled=enabled,
            )
            case_latencies.append(lat)
            res = evaluate_single_case(c, docs, top_k=5)
            results.append(res)

        summary = summarize_retrieval_evaluation(results)
        all_summaries[name] = summary
        case_latencies.sort()
        med_lat = case_latencies[len(case_latencies) // 2]
        p95_lat = case_latencies[int(len(case_latencies) * 0.95)]
        max_lat = max(case_latencies)
        latencies[name] = {"median": med_lat, "p95": p95_lat, "max": max_lat}

    print("\n==========================================================================================")
    print(f"{'Metric':<20} | {'A. Locked Hybrid':<16} | {'B. Rerank Top-8':<16} | {'C. Rerank Top-12':<16} | {'D. Rerank Top-20':<16}")
    print("==========================================================================================")
    metrics_list = [
        ("HitRate@1", "hit_rate_at_1", True),
        ("Recall@1", "recall_at_1", True),
        ("HitRate@3", "hit_rate_at_3", True),
        ("Recall@3", "recall_at_3", True),
        ("HitRate@5", "hit_rate_at_5", True),
        ("Recall@5", "recall_at_5", True),
        ("MRR@5", "mrr_at_5", False),
        ("nDCG@5", "ndcg_at_5", False),
    ]
    for label, key, is_pct in metrics_list:
        v_a = f"{all_summaries['A_locked_hybrid'][key]:.1%}" if is_pct else f"{all_summaries['A_locked_hybrid'][key]:.4f}"
        v_b = f"{all_summaries['B_hybrid_rerank_top8'][key]:.1%}" if is_pct else f"{all_summaries['B_hybrid_rerank_top8'][key]:.4f}"
        v_c = f"{all_summaries['C_hybrid_rerank_top12'][key]:.1%}" if is_pct else f"{all_summaries['C_hybrid_rerank_top12'][key]:.4f}"
        v_d = f"{all_summaries['D_hybrid_rerank_top20'][key]:.1%}" if is_pct else f"{all_summaries['D_hybrid_rerank_top20'][key]:.4f}"
        print(f"{label:<20} | {v_a:<16} | {v_b:<16} | {v_c:<16} | {v_d:<16}")

    print("------------------------------------------------------------------------------------------")
    v_a_d = f"{all_summaries['A_locked_hybrid']['category_summary']['D_typo_informal']['hit_at_1']:.1%}"
    v_b_d = f"{all_summaries['B_hybrid_rerank_top8']['category_summary']['D_typo_informal']['hit_at_1']:.1%}"
    v_c_d = f"{all_summaries['C_hybrid_rerank_top12']['category_summary']['D_typo_informal']['hit_at_1']:.1%}"
    v_d_d = f"{all_summaries['D_hybrid_rerank_top20']['category_summary']['D_typo_informal']['hit_at_1']:.1%}"
    print(f"{'D_typo Hit@1':<20} | {v_a_d:<16} | {v_b_d:<16} | {v_c_d:<16} | {v_d_d:<16}")

    v_a_b = f"{all_summaries['A_locked_hybrid']['category_summary']['B_exact_token']['hit_at_1']:.1%}"
    v_b_b = f"{all_summaries['B_hybrid_rerank_top8']['category_summary']['B_exact_token']['hit_at_1']:.1%}"
    v_c_b = f"{all_summaries['C_hybrid_rerank_top12']['category_summary']['B_exact_token']['hit_at_1']:.1%}"
    v_d_b = f"{all_summaries['D_hybrid_rerank_top20']['category_summary']['B_exact_token']['hit_at_1']:.1%}"
    print(f"{'B_exact Hit@1':<20} | {v_a_b:<16} | {v_b_b:<16} | {v_c_b:<16} | {v_d_b:<16}")

    print("------------------------------------------------------------------------------------------")
    print(f"{'Cross-Tenant Leaks':<20} | {all_summaries['A_locked_hybrid']['cross_tenant_leak_count']:<16} | {all_summaries['B_hybrid_rerank_top8']['cross_tenant_leak_count']:<16} | {all_summaries['C_hybrid_rerank_top12']['cross_tenant_leak_count']:<16} | {all_summaries['D_hybrid_rerank_top20']['cross_tenant_leak_count']:<16}")
    print(f"{'Forbidden Leaks':<20} | {all_summaries['A_locked_hybrid']['forbidden_doc_retrieval_count']:<16} | {all_summaries['B_hybrid_rerank_top8']['forbidden_doc_retrieval_count']:<16} | {all_summaries['C_hybrid_rerank_top12']['forbidden_doc_retrieval_count']:<16} | {all_summaries['D_hybrid_rerank_top20']['forbidden_doc_retrieval_count']:<16}")
    print(f"{'Policy Violations':<20} | {all_summaries['A_locked_hybrid']['policy_authority_violation_count']:<16} | {all_summaries['B_hybrid_rerank_top8']['policy_authority_violation_count']:<16} | {all_summaries['C_hybrid_rerank_top12']['policy_authority_violation_count']:<16} | {all_summaries['D_hybrid_rerank_top20']['policy_authority_violation_count']:<16}")
    print("------------------------------------------------------------------------------------------")
    print(f"{'Median Latency (ms)':<20} | {latencies['A_locked_hybrid']['median']:<16.1f} | {latencies['B_hybrid_rerank_top8']['median']:<16.1f} | {latencies['C_hybrid_rerank_top12']['median']:<16.1f} | {latencies['D_hybrid_rerank_top20']['median']:<16.1f}")
    print(f"{'p95 Latency (ms)':<20} | {latencies['A_locked_hybrid']['p95']:<16.1f} | {latencies['B_hybrid_rerank_top8']['p95']:<16.1f} | {latencies['C_hybrid_rerank_top12']['p95']:<16.1f} | {latencies['D_hybrid_rerank_top20']['p95']:<16.1f}")
    print("==========================================================================================")


if __name__ == "__main__":
    run_benchmark()
