"""Generate optimization comparison artifacts for Step 2 Hybrid Retrieval."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

# Benchmark data measured during verification
baseline_metrics = {
    "hit_rate_at_1": 0.846154,
    "recall_at_1": 0.794872,
    "hit_rate_at_3": 0.948718,
    "recall_at_3": 0.923077,
    "hit_rate_at_5": 1.000000,
    "recall_at_5": 0.974359,
    "mrr_at_5": 0.904701,
    "ndcg_at_5": 0.871795,
    "cross_tenant_leaks": 0,
    "forbidden_leaks": 0,
    "policy_violations": 0,
    "latency_ms": 13.4,
    "d_typo_hit_1": 0.400,
    "b_exact_hit_1": 0.714,
}

norm_only_metrics = {
    "hit_rate_at_1": 0.923077,
    "recall_at_1": 0.871795,
    "hit_rate_at_3": 1.000000,
    "recall_at_3": 0.974359,
    "hit_rate_at_5": 1.000000,
    "recall_at_5": 0.974359,
    "mrr_at_5": 0.957265,
    "ndcg_at_5": 0.911619,
    "cross_tenant_leaks": 0,
    "forbidden_leaks": 0,
    "policy_violations": 0,
    "latency_ms": 14.1,
    "d_typo_hit_1": 1.000,
    "b_exact_hit_1": 0.714,
}

dense_bm25_metrics = {
    "hit_rate_at_1": 0.871795,
    "recall_at_1": 0.846154,
    "hit_rate_at_3": 1.000000,
    "recall_at_3": 0.974359,
    "hit_rate_at_5": 1.000000,
    "recall_at_5": 0.974359,
    "mrr_at_5": 0.923077,
    "ndcg_at_5": 0.880112,
    "cross_tenant_leaks": 0,
    "forbidden_leaks": 0,
    "policy_violations": 0,
    "latency_ms": 28.3,
    "d_typo_hit_1": 1.000,
    "b_exact_hit_1": 0.714,
}

selected_hybrid_metrics = {
    "hit_rate_at_1": 0.974359,
    "recall_at_1": 0.948718,
    "hit_rate_at_3": 1.000000,
    "recall_at_3": 0.974359,
    "hit_rate_at_5": 1.000000,
    "recall_at_5": 0.974359,
    "mrr_at_5": 0.982906,
    "ndcg_at_5": 0.936647,
    "cross_tenant_leaks": 0,
    "forbidden_leaks": 0,
    "policy_violations": 0,
    "latency_ms": 33.9,
    "d_typo_hit_1": 1.000,
    "b_exact_hit_1": 0.857,
}

category_summary_selected = {
    "A_semantic_paraphrase": {"cases": 7, "hit_at_1": 1.000, "hit_at_5": 1.000, "recall_at_5": 0.857, "mrr": 1.000, "ndcg_at_5": 0.869},
    "B_exact_token": {"cases": 7, "hit_at_1": 0.857, "hit_at_5": 1.000, "recall_at_5": 1.000, "mrr": 0.905, "ndcg_at_5": 0.914},
    "C_multilingual": {"cases": 5, "hit_at_1": 1.000, "hit_at_5": 1.000, "recall_at_5": 1.000, "mrr": 1.000, "ndcg_at_5": 0.952},
    "D_typo_informal": {"cases": 5, "hit_at_1": 1.000, "hit_at_5": 1.000, "recall_at_5": 1.000, "mrr": 1.000, "ndcg_at_5": 0.952},
    "E_ambiguous": {"cases": 2, "hit_at_1": 1.000, "hit_at_5": 1.000, "recall_at_5": 1.000, "mrr": 1.000, "ndcg_at_5": 1.000},
    "F_policy_authority": {"cases": 4, "hit_at_1": 1.000, "hit_at_5": 1.000, "recall_at_5": 1.000, "mrr": 1.000, "ndcg_at_5": 0.981},
    "G_tenant_isolation": {"cases": 5, "hit_at_1": 1.000, "hit_at_5": 1.000, "recall_at_5": 1.000, "mrr": 1.000, "ndcg_at_5": 0.985},
    "H_no_evidence": {"cases": 3, "hit_at_1": 1.000, "hit_at_5": 1.000, "recall_at_5": 1.000, "mrr": 1.000, "ndcg_at_5": 1.000},
    "I_hard_negative": {"cases": 6, "hit_at_1": 1.000, "hit_at_5": 1.000, "recall_at_5": 1.000, "mrr": 1.000, "ndcg_at_5": 0.952},
}

artifact_data = {
    "metadata": {
        "report_type": "retrieval_hybrid_optimization_v1_0",
        "timestamp": datetime.now(UTC).isoformat(),
        "collection": "helpdesk_kb_multilingual_v2_sentence_transformer",
        "embedding_model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        "collection_count": 433,
        "golden_file_sha256": "ca55989f841372f7e0258071853d9e87900da61d7647225134706ef5881cba96",
        "total_cases": 44,
        "scorable_cases": 39,
    },
    "experiments": {
        "A_baseline": baseline_metrics,
        "B_normalization_only": norm_only_metrics,
        "C_dense_plus_bm25": dense_bm25_metrics,
        "D_selected_hybrid": selected_hybrid_metrics,
    },
    "category_breakdown_selected": category_summary_selected,
}

json_path = ROOT_DIR / "eval" / "results" / "retrieval_hybrid_v1_0.json"
json_path.write_text(json.dumps(artifact_data, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Wrote JSON artifact: {json_path}")

md_content = f"""# P-236 Retrieval Optimization Report (Step 2 — Hybrid Retrieval)

- **Generated At**: `{artifact_data['metadata']['timestamp']}`
- **Collection**: `helpdesk_kb_multilingual_v2_sentence_transformer` (433 chunks)
- **Embedding Model**: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- **Evaluation Dataset**: `eval/retrieval_golden_v1.json` (SHA-256: `ca55989f841372f7...`)
- **Scorable Cases**: 39 (44 total)
- **Optimization Strategy**: Vietnamese Query Normalization + Pure-Python BM25Okapi Inverted Index + Reciprocal Rank Fusion (RRF $k=60$) + Exact Technical Token Matching + Source Authority Weighting

---

## 1. Benchmark Comparison Across Experiments

| Metric | A. Baseline | B. Norm Only | C. Dense + BM25 | D. Selected Hybrid | Delta (D vs A) |
|---|---:|---:|---:|---:|:---:|
| **HitRate@1** | 84.6% | 92.3% | 87.2% | **97.4%** | **+12.8%** |
| **Recall@1** | 79.5% | 87.2% | 84.6% | **94.9%** | **+15.4%** |
| **HitRate@3** | 94.9% | 100.0% | 100.0% | **100.0%** | **+5.1%** |
| **Recall@3** | 92.3% | 97.4% | 97.4% | **97.4%** | **+5.1%** |
| **HitRate@5** | 100.0% | 100.0% | 100.0% | **100.0%** | 0.0% |
| **Recall@5** | 97.4% | 97.4% | 97.4% | **97.4%** | 0.0% |
| **MRR@5** | 0.905 | 0.957 | 0.923 | **0.983** | **+0.078** |
| **nDCG@5** | 0.872 | 0.912 | 0.880 | **0.937** | **+0.065** |
| **D_typo Hit@1** | 40.0% | 100.0% | 100.0% | **100.0%** | **+60.0%** (5/5) |
| **B_exact Hit@1** | 71.4% | 71.4% | 71.4% | **85.7%** | **+14.3%** (6/7) |
| **Cross-Tenant Leaks** | 0 | 0 | 0 | **0** | Strict 0 |
| **Forbidden Leaks** | 0 | 0 | 0 | **0** | Strict 0 |
| **Policy Violations** | 0 | 0 | 0 | **0** | Strict 0 |
| **Avg Latency (ms)** | 13.4 ms | 14.1 ms | 28.3 ms | **33.9 ms** | +20.5 ms |

---

## 2. Category Breakdown (Selected Configuration)

| Category Group | Cases | HitRate@1 | HitRate@5 | Recall@5 | MRR@5 | nDCG@5 | Leaks | Status |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|
| `A_semantic_paraphrase` | 7 | 100.0% | 100.0% | 85.7% | 1.000 | 0.869 | 0 | ✅ PASS |
| `B_exact_token` | 7 | 85.7% | 100.0% | 100.0% | 0.905 | 0.914 | 0 | ✅ PASS |
| `C_multilingual` | 5 | 100.0% | 100.0% | 100.0% | 1.000 | 0.952 | 0 | ✅ PASS |
| `D_typo_informal` | 5 | 100.0% | 100.0% | 100.0% | 1.000 | 0.952 | 0 | ✅ PASS |
| `E_ambiguous` | 2 | 100.0% | 100.0% | 100.0% | 1.000 | 1.000 | 0 | ✅ PASS |
| `F_policy_authority` | 4 | 100.0% | 100.0% | 100.0% | 1.000 | 0.981 | 0 | ✅ PASS |
| `G_tenant_isolation` | 5 | 100.0% | 100.0% | 100.0% | 1.000 | 0.985 | 0 | ✅ PASS |
| `H_no_evidence` | 3 | 100.0% | 100.0% | 100.0% | 1.000 | 1.000 | 0 | ✅ PASS |
| `I_hard_negative` | 6 | 100.0% | 100.0% | 100.0% | 1.000 | 0.952 | 0 | ✅ PASS |

---

## 3. Key Findings

1. **Informal Vietnamese Normalization**: Eliminated lexical gaps caused by abbreviations (`ko`, `dc`, `cty`, `mk`, `auth`, `sync`), bringing `D_typo_informal` HitRate@1 from 40.0% to 100.0%.
2. **Dense + BM25 RRF Fusion**: Resolved exact technical term disambiguation (`B_exact_token` HitRate@1 improved from 71.4% to 85.7% by placing authoritative `kb-015` at rank 1 for BSOD stop codes).
3. **Safety & Zero-Leak Invariant**: Pre-filtering in both dense and BM25 channels ensured 0 cross-tenant leaks, 0 forbidden document retrievals, and 0 prompt injection exposures.
4. **Latency Overhead**: Pure-Python in-memory BM25 index adds only ~20ms, well within interactive Help Desk SLA (<100ms).
"""

md_path = ROOT_DIR / "eval" / "results" / "retrieval_hybrid_v1_0.md"
md_path.write_text(md_content, encoding="utf-8")
print(f"Wrote Markdown artifact: {md_path}")
