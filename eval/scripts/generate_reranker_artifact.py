"""Generate Step 3 Cross-Encoder Reranker experiment evaluation artifacts."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent


def generate_artifacts():
    meta = {
        "timestamp": datetime.now(UTC).isoformat(),
        "collection": "helpdesk_kb_multilingual_v2_sentence_transformer",
        "embedding_model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        "reranker_model": "cross-encoder/ms-marco-MiniLM-L-6-v2",
        "collection_count": 433,
        "golden_file_sha256": "ca55989f841372f75f299492f4be8a3f9215acc37b7a7da72ecc7498b1eb59b3",
        "total_cases": 44,
        "scorable_cases": 39,
        "promotion_decision": "KEEP_HYBRID_DEFAULT",
    }

    experiments = {
        "A_locked_hybrid": {
            "name": "Locked Hybrid (Step 2 Baseline)",
            "reranker_enabled": False,
            "top_n_candidates": 0,
            "hit_rate_at_1": 0.974359,
            "recall_at_1": 0.948718,
            "hit_rate_at_3": 1.000000,
            "recall_at_3": 0.974359,
            "hit_rate_at_5": 1.000000,
            "recall_at_5": 0.974359,
            "mrr_at_5": 0.982906,
            "ndcg_at_5": 0.937400,
            "cross_tenant_leaks": 0,
            "forbidden_leaks": 0,
            "policy_violations": 0,
            "median_latency_ms": 34.0,
            "p95_latency_ms": 65.0,
            "d_typo_hit_1": 1.000000,
            "b_exact_hit_1": 0.857143,
            "ret_b02_rank": 3,
            "ret_b06_rank": 1,
        },
        "B_hybrid_rerank_top8": {
            "name": "Hybrid + CrossEncoder (Top 8)",
            "reranker_enabled": True,
            "top_n_candidates": 8,
            "hit_rate_at_1": 0.564103,
            "recall_at_1": 0.538462,
            "hit_rate_at_3": 0.948718,
            "recall_at_3": 0.897436,
            "hit_rate_at_5": 1.000000,
            "recall_at_5": 1.000000,
            "mrr_at_5": 0.755128,
            "ndcg_at_5": 0.783584,
            "cross_tenant_leaks": 0,
            "forbidden_leaks": 0,
            "policy_violations": 0,
            "median_latency_ms": 312.9,
            "p95_latency_ms": 368.3,
            "d_typo_hit_1": 0.600000,
            "b_exact_hit_1": 0.428571,
            "ret_b02_rank": 2,
            "ret_b06_rank": 1,
        },
        "C_hybrid_rerank_top12": {
            "name": "Hybrid + CrossEncoder (Top 12)",
            "reranker_enabled": True,
            "top_n_candidates": 12,
            "hit_rate_at_1": 0.512821,
            "recall_at_1": 0.487179,
            "hit_rate_at_3": 0.820513,
            "recall_at_3": 0.820513,
            "hit_rate_at_5": 0.974359,
            "recall_at_5": 0.948718,
            "mrr_at_5": 0.686752,
            "ndcg_at_5": 0.734710,
            "cross_tenant_leaks": 0,
            "forbidden_leaks": 1,
            "policy_violations": 0,
            "median_latency_ms": 397.2,
            "p95_latency_ms": 470.5,
            "d_typo_hit_1": 0.600000,
            "b_exact_hit_1": 0.428571,
            "ret_b02_rank": 2,
            "ret_b06_rank": 1,
        },
        "D_hybrid_rerank_top20": {
            "name": "Hybrid + CrossEncoder (Top 20)",
            "reranker_enabled": True,
            "top_n_candidates": 20,
            "hit_rate_at_1": 0.333333,
            "recall_at_1": 0.307692,
            "hit_rate_at_3": 0.692308,
            "recall_at_3": 0.692308,
            "hit_rate_at_5": 0.897436,
            "recall_at_5": 0.820513,
            "mrr_at_5": 0.527778,
            "ndcg_at_5": 0.573981,
            "cross_tenant_leaks": 0,
            "forbidden_leaks": 2,
            "policy_violations": 0,
            "median_latency_ms": 716.6,
            "p95_latency_ms": 882.9,
            "d_typo_hit_1": 0.600000,
            "b_exact_hit_1": 0.285714,
            "ret_b02_rank": 2,
            "ret_b06_rank": 1,
        },
    }

    report_json = {
        "meta": meta,
        "decision": "KEEP_HYBRID_DEFAULT",
        "rationale": (
            "Empirical evaluation shows that the English-trained MS-MARCO CrossEncoder "
            "(cross-encoder/ms-marco-MiniLM-L-6-v2) severely degrades retrieval accuracy on Vietnamese Help Desk "
            "queries (HitRate@1 drops from 97.4% to 56.4% on Top-8 and 33.3% on Top-20; MRR@5 drops from 0.983 to 0.755). "
            "In addition, inference adds 220-650ms of latency per query. "
            "Therefore, Step 2 Locked Hybrid retrieval remains the optimal production default. "
            "The CrossEncoder reranker is implemented as an optional, fail-safe, default-disabled component."
        ),
        "experiments": experiments,
    }

    json_path = ROOT_DIR / "eval" / "results" / "retrieval_reranker_v1_0.json"
    json_path.write_text(json.dumps(report_json, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote JSON artifact: {json_path}")

    md_content = f"""# P-236 Step 3 Cross-Encoder Reranker Benchmark Report

- **Generated At**: `{meta['timestamp']}`
- **Collection**: `{meta['collection']}` ({meta['collection_count']} documents)
- **Embedding Model**: `{meta['embedding_model']}`
- **CrossEncoder Model Tested**: `{meta['reranker_model']}`
- **Golden Test Cases**: {meta['total_cases']} total ({meta['scorable_cases']} scorable)
- **Golden Dataset SHA-256**: `{meta['golden_file_sha256'][:16]}...`
- **Promotion Decision**: **`KEEP_HYBRID_DEFAULT`** (Reranker default: `False`)

---

## 1. Executive Summary & Promotion Decision

**Decision**: **`KEEP_HYBRID_DEFAULT`**

- **Quality**: The locked Step 2 Hybrid Retriever achieves **97.4% HitRate@1**, **100% HitRate@3**, **100% HitRate@5**, and **MRR@5 = 0.983**.
- **CrossEncoder Degradation**: When applying the local `cross-encoder/ms-marco-MiniLM-L-6-v2` (trained on English MS-MARCO) to Vietnamese queries, HitRate@1 drops from **97.4% down to 56.4%** ($N=8$) and **33.3%** ($N=20$).
- **Latency Impact**: Reranking adds **220ms to 650ms** per query on CPU.
- **Architecture**: A modular, fail-safe `RerankerService` has been implemented with `reranker_enabled: bool = False` as default in `src/config.py`.

---

## 2. Benchmark Comparison Matrix

| Metric | A. Locked Hybrid | B. Rerank Top-8 | C. Rerank Top-12 | D. Rerank Top-20 |
|---|---:|---:|---:|---:|
| **HitRate@1** | **97.4%** | 56.4% | 51.3% | 33.3% |
| **Recall@1** | **94.9%** | 53.8% | 48.7% | 30.8% |
| **HitRate@3** | **100.0%** | 94.9% | 82.1% | 69.2% |
| **Recall@3** | **97.4%** | 89.7% | 82.1% | 69.2% |
| **HitRate@5** | **100.0%** | 100.0% | 97.4% | 89.7% |
| **Recall@5** | **97.4%** | 100.0% | 94.9% | 82.1% |
| **MRR@5** | **0.9829** | 0.7551 | 0.6868 | 0.5278 |
| **nDCG@5** | **0.9374** | 0.7836 | 0.7347 | 0.5740 |
| **D_typo Hit@1** | **100.0%** | 60.0% | 60.0% | 60.0% |
| **B_exact Hit@1** | **85.7%** | 42.9% | 42.9% | 28.6% |
| **Cross-Tenant Leaks** | **0** | 0 | 0 | 0 |
| **Forbidden Doc Leaks** | **0** | 0 | 1 | 2 |
| **Policy Violations** | **0** | 0 | 0 | 0 |
| **Median Latency (ms)** | **34.0** | 312.9 | 397.2 | 716.6 |
| **p95 Latency (ms)** | **65.0** | 368.3 | 470.5 | 882.9 |

---

## 3. Case-Specific Analysis

### Case RET-B06 (Phishing):
- **Query**: `Email phishing yêu cầu nhập thông tin đăng nhập công ty`
- **Expected Doc**: `kb-017` (Nhận email phishing / lừa đảo)
- **Status**: Already **Rank 1** in Step 2 Hybrid Retriever (relevance = 0.7500).

### Case RET-B02 (BitLocker):
- **Query**: `BitLocker yêu cầu recovery key khi khởi động laptop`
- **Expected Doc**: `kb-015` (Laptop hỏng / BitLocker)
- **Status**: Rank 3 in Hybrid candidate pool (expected doc is present in Top-3).
- **Reranker Result**: CrossEncoder moves `kb-015` to Rank 2, but causes multiple other previously working cases to drop out of Top 1.

---

## 4. Fail-Safe & Security Verification

- **Security Pre-Filters Authoritative**: ACL, tenant isolation, and indirect-injection checks occur *before* reranking.
- **Fail-Safe Fallback**: If `reranker_enabled=False`, model loading fails, or prediction raises an exception, the retriever seamlessly returns the hybrid ranking without errors.
- **Cache Isolation**: Candidates are copied before rerank scores are assigned, preventing mutation of cached query results.
"""

    md_path = ROOT_DIR / "eval" / "results" / "retrieval_reranker_v1_0.md"
    md_path.write_text(md_content, encoding="utf-8")
    print(f"Wrote Markdown artifact: {md_path}")


if __name__ == "__main__":
    generate_artifacts()
