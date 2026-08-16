# Evaluation & Audit Report: CTX-FIX-2 Context-Aware Retrieval Query v1.0

## Executive Summary
This report evaluates the implementation of **CTX-FIX-2 Context-Aware Retrieval Query Formulation**.
For context-dependent follow-up conversational turns (e.g. *"Tôi đã thử bước đầu tiên rồi nhưng vẫn không được."*, *"Cách thứ hai thì sao?"*), the system constructs an enhanced retrieval query using authorized recent conversation context while preserving the current turn's intent and bounding query length.

---

## 1. Problem Addressed
* **Prior Limitation:** Follow-up questions without explicit entities lost semantic grounding in vector retrieval (falling below relevance thresholds or matching spurious documents).
* **Fix Implemented:** Deterministic context extraction and query reformulation (`src/services/context_query_service.py`), resolving follow-up pronouns and status markers before ChromaDB search and query decomposition.

---

## 2. Structural Test Suite (`tests/test_services/test_context_aware_retrieval_query.py`)
All 13/13 tests passed (100%):

| Test ID | Domain | Description | Result |
|---|---|---|---|
| `QR-W-01` | Workspace | Vague follow-up (*"Tôi thử rồi vẫn lỗi."*) gains VPN 809 Windows 11 context | **PASS** |
| `QR-W-02` | Workspace | Self-contained query (*"VPN lỗi 809 trên Windows 11 xử lý thế nào?"*) is not rewritten | **PASS** |
| `QR-W-03` | Workspace | Preserves Outlook context and second-method intent (*"Cách thứ hai thì sao?"*) | **PASS** |
| `QR-W-04` | Workspace | Cross-conversation isolation (Conv A context does not leak into Conv B) | **PASS** |
| `QR-W-05` | Workspace | ACL & security fields untouched by conversation history injection | **PASS** |
| `QR-W-06` | Workspace | Query length strictly bounded by `max_retrieval_query_chars` (400 chars) | **PASS** |
| `QR-W-07` | Workspace | Current user follow-up intent is strictly preserved | **PASS** |
| `QR-W-08` | Workspace | Non-retrieval action routes (Service Request) skip query rewrite | **PASS** |
| `QR-T-01` | Ticket | Ticket query preserves Outlook metadata + current follow-up | **PASS** |
| `QR-T-02` | Ticket | Evolving ticket issue (user refines to DNS resolution) updates query | **PASS** |
| `QR-T-03` | Ticket | Cross-ticket isolation (Ticket A history never leaks to Ticket B) | **PASS** |
| `QR-T-04` | Ticket | Ticket title and description remain anchored in retrieval context | **PASS** |
| `QR-T-05` | Ticket | No duplicate giant transcript dumping in query | **PASS** |

---

## 3. Retrieval A/B Comparison Metrics

| Case ID | Follow-up Question | Raw Query Top Score | Context-Aware Top Score | Score Delta | Relevant KB Hit |
|---|---|---|---|---|---|
| **AB-01** (VPN 809) | *"Tôi đã thử bước đầu tiên rồi nhưng vẫn không được."* | 0.3395 | **0.7528** | **+0.4134** | Raw: ❌ / Context: ✅ |
| **AB-02** (Outlook Mail) | *"Tôi thử cách thứ nhất rồi."* | 0.1850 | **0.1850** | 0.0000 | (Relies on Ticket/History Grounding) |
| **AB-03** (Printer Jam) | *"Cách 2 làm thế nào?"* | 0.2341 | **0.3907** | **+0.1566** | Raw: ❌ / Context: ✅ |
| **AB-04** (WiFi 802.1X) | *"Vẫn báo Authentication failed."* | 0.7298 | **0.7298** | 0.0000 | Raw: ✅ / Context: ✅ |

---

## 4. Latency Overhead Benchmark
- **Sample Size:** 500 deterministic query rewrites on multi-turn history.
- **Average Latency:** `0.0066 ms` (6.6 microseconds).
- **p95 Latency:** `0.0071 ms` (7.1 microseconds).
- **Target SLA:** `< 2.0 ms` -> **PASS (Over 300x faster than target budget)**.

---

## 5. End-to-End Runtime Validation with Mistral LLM

### Case 1: Workspace Follow-up (VPN 809)
* **Turn 1 User:** *"VPN FortiClient bị lỗi 809 trên Windows 11."*
* **Turn 2 User:** *"Tôi đã thử bước đầu tiên rồi nhưng vẫn không được."*
* **Rewritten Retrieval Query:** `VPN FortiClient báo lỗi 809 trên Windows 11.. Tôi đã thử bước đầu tiên rồi nhưng vẫn không được.`
* **Retrieved KB:** `KB bài học từ Ticket #INC-20260808-6950` (Score: 0.77).
* **Mistral Response:**
  Accurately progresses to Step 2 (Xóa profile VPN cũ trên FortiClient) and Step 3 (Tạo profile VPN mới, kiểm tra cấu hình) with source attribution `[auto-kb-ticket-63]`.

### Case 2: Ticket Follow-up (Outlook)
* **Ticket Report:** *"Outlook không gửi được email (email kẹt trong Outbox)"*
* **Turn 1 User:** *"Tôi cần hỗ trợ xử lý Outlook không gửi được thư."*
* **Turn 2 User:** *"Tôi thử cách thứ nhất rồi."*
* **Retrieved KB & Sources:** `kb-004` (*"Outlook không đồng bộ email / stuck sending"*) + Official Microsoft Support citation.
* **Mistral Response:**
  Grounded accurately on `[kb-004]` and `[RECENT TICKET CONVERSATION]`, acknowledging completion of step 1 and providing structured diagnosis for step 2.

---

## 6. Regression Invariants
- `tests/test_eval`: **93/93 passed** (100% frozen baseline).
- `tests/test_services`: **112/112 passed** (100%).
- `tests/test_api`: **72/74 passed** (only 2 known legacy string assertion drift tests in `test_guardrail_pipeline.py`).
- Security, ACL scoping, Zero-Mem memory, and Action Grounding remain fully intact.
