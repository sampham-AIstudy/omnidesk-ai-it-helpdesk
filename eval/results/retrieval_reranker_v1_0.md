# P-236 Step 3 Cross-Encoder Reranker Benchmark Report

- **Generated At**: `2026-08-19T12:51:26.760199+00:00`
- **Collection**: `helpdesk_kb_multilingual_v2_sentence_transformer` (433 documents)
- **Embedding Model**: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- **CrossEncoder Model Tested**: `cross-encoder/ms-marco-MiniLM-L-6-v2`
- **Golden Test Cases**: 44 total (39 scorable)
- **Golden Dataset SHA-256**: `ca55989f841372f7...`
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
