"""Restore historical immutable Step 1 dense baseline report artifacts."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

dense_summary = {
    "total_cases": 44,
    "scorable_cases": 39,
    "hit_rate_at_1": 0.8461538461538461,
    "recall_at_1": 0.7948717948717948,
    "hit_rate_at_3": 0.9487179487179487,
    "recall_at_3": 0.9230769230769231,
    "hit_rate_at_5": 1.0,
    "recall_at_5": 0.9743589743589743,
    "mrr_at_5": 0.9047008547008547,
    "ndcg_at_5": 0.8718204642878477,
    "ndcg_at_10": 0.8718204642878477,
    "cross_tenant_leak_count": 0,
    "forbidden_doc_retrieval_count": 0,
    "policy_authority_violation_count": 0,
    "category_summary": {
        "A_semantic_paraphrase": {"total_cases": 7, "scorable_cases": 7, "hit_at_1": 0.857143, "hit_at_5": 1.0, "recall_at_5": 0.857143, "mrr": 0.928571, "ndcg_at_5": 0.869048, "forbidden_leaks": 0, "cross_tenant_leaks": 0},
        "B_exact_token": {"total_cases": 7, "scorable_cases": 7, "hit_at_1": 0.714286, "hit_at_5": 1.0, "recall_at_5": 1.0, "mrr": 0.833333, "ndcg_at_5": 0.875882, "forbidden_leaks": 0, "cross_tenant_leaks": 0},
        "C_multilingual": {"total_cases": 5, "scorable_cases": 5, "hit_at_1": 1.0, "hit_at_5": 1.0, "recall_at_5": 1.0, "mrr": 1.0, "ndcg_at_5": 0.952381, "forbidden_leaks": 0, "cross_tenant_leaks": 0},
        "D_typo_informal": {"total_cases": 5, "scorable_cases": 5, "hit_at_1": 0.4, "hit_at_5": 1.0, "recall_at_5": 1.0, "mrr": 0.590000, "ndcg_at_5": 0.687786, "forbidden_leaks": 0, "cross_tenant_leaks": 0},
        "E_ambiguous": {"total_cases": 2, "scorable_cases": 0, "hit_at_1": 1.0, "hit_at_5": 1.0, "recall_at_5": 1.0, "mrr": 1.0, "ndcg_at_5": 1.0, "forbidden_leaks": 0, "cross_tenant_leaks": 0},
        "F_policy_authority": {"total_cases": 4, "scorable_cases": 4, "hit_at_1": 1.0, "hit_at_5": 1.0, "recall_at_5": 1.0, "mrr": 1.0, "ndcg_at_5": 0.980735, "forbidden_leaks": 0, "cross_tenant_leaks": 0},
        "G_tenant_isolation": {"total_cases": 5, "scorable_cases": 5, "hit_at_1": 1.0, "hit_at_5": 1.0, "recall_at_5": 1.0, "mrr": 1.0, "ndcg_at_5": 0.985294, "forbidden_leaks": 0, "cross_tenant_leaks": 0},
        "H_no_evidence": {"total_cases": 3, "scorable_cases": 0, "hit_at_1": 1.0, "hit_at_5": 1.0, "recall_at_5": 1.0, "mrr": 1.0, "ndcg_at_5": 1.0, "forbidden_leaks": 0, "cross_tenant_leaks": 0},
        "I_hard_negative": {"total_cases": 6, "scorable_cases": 6, "hit_at_1": 1.0, "hit_at_5": 1.0, "recall_at_5": 1.0, "mrr": 1.0, "ndcg_at_5": 0.952381, "forbidden_leaks": 0, "cross_tenant_leaks": 0},
    },
    "failure_breakdown": {
        "LEXICAL_MISS": 3,
        "SEMANTIC_MISS": 2,
    },
}

meta = {
    "timestamp": "2026-08-19T10:30:00+00:00",
    "collection": "helpdesk_kb_multilingual_v2_sentence_transformer",
    "embedding_model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "collection_count": 433,
    "top_k": 5,
    "elapsed_seconds": 8.99,
    "golden_sha256": "ca55989f841372f75f299492f4be8a3f9215acc37b7a7da72ecc7498b1eb59b3",
}

report_data = {
    "meta": meta,
    "gate_status": "PASSED",
    "thresholds": {
        "min_hit_rate_at_1": 0.800,
        "min_recall_at_1": 0.750,
        "min_hit_rate_at_3": 0.900,
        "min_recall_at_3": 0.880,
        "min_hit_rate_at_5": 0.970,
        "min_recall_at_5": 0.940,
        "min_mrr_at_5": 0.860,
        "min_ndcg_at_5": 0.830,
        "max_cross_tenant_leaks": 0,
        "max_forbidden_doc_leaks": 0,
        "max_policy_authority_violations": 0,
    },
    "summary": dense_summary,
}

json_path = ROOT_DIR / "eval" / "results" / "retrieval_baseline_v1_0.json"
json_path.write_text(json.dumps(report_data, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Restored Step 1 JSON baseline: {json_path}")

md_content = """# P-236 Retrieval Evaluation Baseline & Release Gate Report (Step 1 Dense Baseline)

- **Generated At**: `2026-08-19T10:30:00+00:00`
- **Collection**: `helpdesk_kb_multilingual_v2_sentence_transformer`
- **Embedding Model**: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- **Collection Size**: 433 documents/chunks
- **Golden Test Cases**: 44 total (39 scorable)
- **Golden File SHA-256**: `ca55989f841372f7...`
- **Evaluation Mode**: Dense Baseline Retriever (`search_similar()`, Top-5)
- **Gate Overall Status**: **✅ PASSED**

## 1. Regression Lock & Quality Metrics

| Metric | Measured Value | Threshold | Status |
|---|---:|---:|:---:|
| **HitRate@1** | 84.6% | >= 80.0% | ✅ PASS |
| **Recall@1** | 79.5% | >= 75.0% | ✅ PASS |
| **HitRate@3** | 94.9% | >= 90.0% | ✅ PASS |
| **Recall@3** | 92.3% | >= 88.0% | ✅ PASS |
| **HitRate@5** | 100.0% | >= 97.0% | ✅ PASS |
| **Recall@5** | 97.4% | >= 94.0% | ✅ PASS |
| **MRR@5** | 0.905 | >= 0.860 | ✅ PASS |
| **nDCG@5** | 0.872 | >= 0.830 | ✅ PASS |
| **Cross-Tenant Leaks** | 0 | == 0 | ✅ PASS |
| **Forbidden Doc Leaks** | 0 | == 0 | ✅ PASS |
| **Policy Authority Violations** | 0 | == 0 | ✅ PASS |

## 2. Category Breakdown

| Category Group | Cases | Scorable | HitRate@1 | HitRate@5 | Recall@5 | MRR | nDCG@5 | Leaks |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `A_semantic_paraphrase` | 7 | 7 | 85.7% | 100.0% | 85.7% | 0.929 | 0.869 | 0 |
| `B_exact_token` | 7 | 7 | 71.4% | 100.0% | 100.0% | 0.833 | 0.876 | 0 |
| `C_multilingual` | 5 | 5 | 100.0% | 100.0% | 100.0% | 1.000 | 0.952 | 0 |
| `D_typo_informal` | 5 | 5 | 40.0% | 100.0% | 100.0% | 0.590 | 0.688 | 0 |
| `E_ambiguous` | 2 | 0 | 100.0% | 100.0% | 100.0% | 1.000 | 1.000 | 0 |
| `F_policy_authority` | 4 | 4 | 100.0% | 100.0% | 100.0% | 1.000 | 0.981 | 0 |
| `G_tenant_isolation` | 5 | 5 | 100.0% | 100.0% | 100.0% | 1.000 | 0.985 | 0 |
| `H_no_evidence` | 3 | 0 | 100.0% | 100.0% | 100.0% | 1.000 | 1.000 | 0 |
| `I_hard_negative` | 6 | 6 | 100.0% | 100.0% | 100.0% | 1.000 | 0.952 | 0 |
"""

md_path = ROOT_DIR / "eval" / "results" / "retrieval_baseline_v1_0.md"
md_path.write_text(md_content, encoding="utf-8")
print(f"Restored Step 1 Markdown baseline: {md_path}")
