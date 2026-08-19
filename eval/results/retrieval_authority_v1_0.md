# P-236 Step 4 Source-Authority-Aware Ranking & Canonical Deduplication Report

- **Generated At**: `2026-08-19T13:09:12.298941+00:00`
- **ChromaDB Collection**: `helpdesk_kb_multilingual_v2_sentence_transformer` (433 physical documents, 281 unique canonical sources)
- **Embedding Model**: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- **Golden Dataset**: 44 cases (39 scorable), SHA-256: `ca55989f841372f7...`
- **Promotion Decision**: **`PROMOTE_AUTHORITY_RANKING`**

---

## 1. Executive Summary & Promotion Decision

**Decision**: **`PROMOTE_AUTHORITY_RANKING`**

- **Target Achievement**: Reached **100.0% HitRate@1 (39/39)**, **100.0% HitRate@3**, **100.0% HitRate@5**, **MRR@5 = 1.0000**, and **nDCG@5 = 0.9579**.
- **RET-B02 Resolved**: `kb-015` (Laptop hỏng / BitLocker) successfully promoted from **Rank 3 to Rank 1**.
- **Category `B_exact_token`**: Improved from **85.7% (6/7) $ightarrow$ 100.0% (7/7)**.
- **Safety Invariants**: **Zero** cross-tenant leaks, **zero** forbidden doc leaks, **zero** policy authority violations.
- **Latency**: Negligible latency delta (+0.8ms), no external model or network dependencies.

---

## 2. Source Authority Model Taxonomy

| Tier | Source Type | Multiplier | Role / Description | Document Count |
|---|---|---:|---|---:|
| **Tier 1** | `internal_curated_kb` | **1.40** | Canonical internal Help Desk articles, IT runbooks, enterprise policies | 35 |
| **Tier 1.5** | `approved_internal_source` | **1.20** | Approved internal departmental guidelines | 0 |
| **Tier 2** | `official_web_documentation` | **1.00** | Crawled vendor documentation (Microsoft Support) | 192 |
| **Tier 3** | `historical_resolved_ticket` | **0.95** | Episodic ticket memory | 200 |
| **Tier 4** | `NO_SOURCE_KEY` | **0.90** | Uncategorized / auto-generated | 6 |

---

## 3. Canonical Source Identity & Deduplication

- **Canonical ID Resolution**: Normalizes URLs using `urllib.parse` (lowercased scheme, host, path without trailing slash).
  - `web-bitlocker-recovery-001` and `web-bitlocker-recovery-002` share: `url:https://support.microsoft.com/en-us/windows/finding-your-bitlocker-recovery-key-in-windows-6b71ad27-0b89-ea08-f143-056f5ab347d6`.
- **Distinct Article Preservation**: Every distinct internal KB article (`kb-001` .. `kb-036`) retains its unique identity (`kb:kb-NNN`).
- **Source Diversity**: Primary representative of each canonical source occupies the top rank; secondary chunks from the same source are placed in overflow after unique sources, preventing cluster monopolization.

---

## 4. Benchmark Comparison Matrix

| Metric | A. Locked Hybrid | B. Auth Boost 1.25 | C. Dedup Only | D. Auth (1.40) + Dedup (PROMOTED) |
|---|---:|---:|---:|---:|
| **HitRate@1** | 97.4% (38/39) | 97.4% (38/39) | 97.4% (38/39) | **100.0% (39/39)** |
| **Recall@1** | 94.9% (37/39) | 94.9% (37/39) | 94.9% (37/39) | **97.4% (38/39)** |
| **HitRate@3** | 100.0% (39/39) | 100.0% (39/39) | 100.0% (39/39) | **100.0% (39/39)** |
| **Recall@3** | 97.4% (38/39) | 97.4% (38/39) | 97.4% (38/39) | **97.4% (38/39)** |
| **HitRate@5** | 100.0% (39/39) | 100.0% (39/39) | 100.0% (39/39) | **100.0% (39/39)** |
| **Recall@5** | 97.4% (38/39) | 97.4% (38/39) | 97.4% (38/39) | **97.4% (38/39)** |
| **MRR@5** | 0.9829 | 0.9829 | 0.9872 | **1.0000** |
| **nDCG@5** | 0.9374 | 0.9425 | 0.9520 | **0.9579** |
| **B_exact Hit@1** | 85.7% (6/7) | 85.7% (6/7) | 85.7% (6/7) | **100.0% (7/7)** |
| **D_typo Hit@1** | 100.0% (5/5) | 100.0% (5/5) | 100.0% (5/5) | **100.0% (5/5)** |
| **A_semantic Hit@1** | 100.0% (7/7) | 100.0% (7/7) | 100.0% (7/7) | **100.0% (7/7)** |
| **F_policy Hit@1** | 100.0% (4/4) | 100.0% (4/4) | 100.0% (4/4) | **100.0% (4/4)** |
| **I_hard_neg Hit@1** | 100.0% (6/6) | 100.0% (6/6) | 100.0% (6/6) | **100.0% (6/6)** |
| **RET-B02 Rank** | Rank 3 | Rank 3 | Rank 2 | **Rank 1 (kb-015)** |
| **Cross-Tenant Leaks** | **0** | **0** | **0** | **0** |
| **Forbidden Doc Leaks** | **0** | **0** | **0** | **0** |
| **Policy Violations** | **0** | **0** | **0** | **0** |
| **Median Latency (ms)** | 34.0 | 34.5 | 34.6 | **34.8** |
| **p95 Latency (ms)** | 65.0 | 66.0 | 66.2 | **66.5** |

---

## 5. Case RET-B02 Specific Analysis

- **Query**: `BitLocker yêu cầu recovery key khi khởi động laptop`
- **Expected Doc**: `kb-015` (Laptop hỏng / không khởi động được)
- **Before**: `web-bitlocker-recovery-001` (Rank 1), `web-bitlocker-recovery-002` (Rank 2), `kb-015` (Rank 3).
- **After**: `kb-015` promoted to **Rank 1**; `web-bitlocker-recovery-001` is at **Rank 2**; `web-bitlocker-recovery-002` collapsed into canonical overflow.
- **Bounded Authority Verification**: In synthetic queries where only vendor docs are relevant (e.g. Windows activation error codes), `official_web_documentation` retains 100% of top-5 positions without intrusion from irrelevant internal KBs.
