# P-236 Retrieval Evaluation Baseline & Release Gate Report (Step 1 Dense Baseline)

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
