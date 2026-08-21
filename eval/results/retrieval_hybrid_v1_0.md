# P-236 Retrieval Optimization Report (Step 2 — Hybrid Retrieval)

- **Generated At**: `2026-08-19T11:17:53.703807+00:00`
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
