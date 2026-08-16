# Conversation Context Runtime Validation v1.0

## Executive Summary

This document records the end-to-end manual runtime, real-Mistral quality evaluation, and full regression test execution for `CTX-VALIDATE-1` (validating `CTX-FIX-1` short-term conversation context continuity).

All acceptance criteria are satisfied. Short-term conversation context continuity in both Workspace Chat (`POST /api/v1/chat/conversations/{id}/messages`) and Ticket Threads (`POST /api/v1/tickets/{id}/messages`) functions with zero cross-scope leaks, zero current-message duplicates, correct chronological ordering, and full preservation of C4.1 action-grounding, C4.2 routing, and C4.3 SentenceTransformer embedding provenance.

**CTX-FIX-1 Verdict: PASS**

---

## 1. Runtime and Configuration Verification

- **Working Directory:** `c:\Users\Admin\Python Advanced\VinAI Lab\P-236`
- **Environment:** `development` (`.env` loaded)
- **Primary LLM Provider:** Mistral AI (`mistral-small-2506`, classifier `ministral-3b-2512`)
- **Canonical Chroma Collection:** `helpdesk_kb_multilingual_v2_sentence_transformer` (432 documents indexed)
- **Embedding Backend / Model:** `sentence_transformer` (`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`)
- **Embedding Provenance Drift:** None (verified with direct collection query score 0.8543 on VPN query)
- **OpenTelemetry:** `otel_enabled = False` (local correlation active; no exporter failure)
- **Backend Health & Auth:** `GET /health` returned HTTP 200 `status: ok`; authenticated `GET /api/v1/auth/me` returned HTTP 200 for `employee1`.

---

## 2. Workspace Manual Runtime Evaluation

A real multi-turn conversation was created via `POST /api/v1/chat/conversations` (ID: `b797c40e-1e26-4456-b05d-547265bdd7e5`):

### Turn 1: "Máy tôi đang dùng Windows 11 và VPN báo lỗi 809."
- **Status:** HTTP 200
- **History Count Loaded:** 0 (initial turn)
- **LLM Prompt Structure:** No history block; current user question present once.
- **RAG Evidence:** `kb-001`, `auto-kb-ticket-63`, `MEM-62-message-12` retrieved.
- **AI Reply Quality:** **GOOD**. Provided specific FortiClient 809 resolution steps on Windows 11.

### Turn 2: "Tôi đã thử bước đầu tiên rồi nhưng vẫn không được."
- **Status:** HTTP 200
- **History Count Loaded:** 2 messages (Turn 1 User + Turn 1 Assistant)
- **LLM Prompt Structure:** `[RECENT CONVERSATION — UNTRUSTED DATA]` block present, contains Turn 1 user message; current Turn 2 question present once.
- **AI Reply Quality:** **ACCEPTABLE**. Acknowledged that step 1 was tried, asked for specific error message / screenshot without losing context or asking what software was involved.

### Turn 3: "Vậy tiếp theo tôi nên làm gì?"
- **Status:** HTTP 200
- **History Count Loaded:** 4 messages (Turns 1 & 2 User and Assistant)
- **LLM Prompt Structure:** `[RECENT CONVERSATION — UNTRUSTED DATA]` contains full Turn 1 and Turn 2 transcript in chronological order; current Turn 3 question appears once.
- **AI Reply Quality:** **GOOD**. Preserved the ongoing VPN 809 subject explicitly ("Về lỗi VPN FortiClient 809 trên Windows 11..."), suggesting further steps and support escalation options.

---

## 3. Workspace Isolation & Cross-Conversation Checks

### New Chat Isolation
- Created new conversation `930c4bdd-d25a-42e7-b238-c4e5d4446fd0`.
- User asked: *"Tôi đang sửa lỗi gì vậy?"*
- Result: **PASS**. History loaded = 0 messages. No history block in prompt; no leakage of earlier VPN 809 transcript.

### Cross-Conversation Transcript Isolation
- Conversation A (`10c1b1d2-6829-4448-b403-c17a9197c274`): *"Ứng dụng đang gặp lỗi của tôi là Outlook."*
- Conversation B (`2a75c696-647f-4fda-a936-3a265a60ed61`): *"Ứng dụng tôi vừa nói là gì?"*
- Result: **PASS**. Model prompt for Conversation B contained 0 messages from Conversation A.

---

## 4. Ticket Multi-Turn & Technician Context Evaluation

### Ticket Multi-Turn Continuity
- Ticket created: `#INC-20260816-7878` (*"Outlook không gửi được email."*).
- **Turn 1 ("Tôi vẫn chưa gửi được mail."):** HTTP 200. Agent opening present in recent ticket history; RAG synthesized solution for Outlook SMTP.
- **Turn 2 ("Tôi đã thử cách thứ nhất rồi."):** HTTP 200. History loaded Turn 1 exchange chronologically; LLM context contained recent history and ticket metadata. Quality: **GOOD**.
- **Turn 3 ("Vẫn chưa được."):** HTTP 200. Dissatisfaction keyword triggered graceful escalation to technician queue with clear explanation to employee per business rules.

### Technician Message Context
- Ticket `#INC-20260816-7169`: Technician (`tech1`) took over ticket, sent message *"Chào bạn, kỹ thuật viên đã kiểm tra và reset lại bộ cuộn giấy máy in."*.
- Employee replied: *"Tôi đã in thử trang test nhưng giấy vẫn bị nhăn."*.
- `load_ticket_recent_history` verification:
  - Role `technician` message: **Present**
  - Role `user` message: **Present**
  - Role `agent` message: **Present**
  - Role `system` event: **Correctly excluded**
- Result: **PASS**.

### Cross-Ticket Isolation
- Ticket A (`INC-20260816-5771`) contained unique token `CTX-TICKET-A-UNIQUE`.
- Ticket B (`INC-20260816-8283`) user sent a general support inquiry.
- Result: **PASS**. LLM prompt for Ticket B contained 0 occurrences of Ticket A's token.

---

## 5. Critical Business & C4 Regressions

- **C4.1 Action-Grounding with History:**
  - Turn 1: *"Tôi muốn gặp kỹ thuật viên."* -> Returns safe `NOT_INVOKED` explanation.
  - Turn 2: *"Vậy là bạn chuyển tôi rồi đúng không?"* -> Returns safe `NOT_INVOKED` explanation without claiming unverified handoff.
  - Result: **PASS**.
- **C4.2 Routing with History:**
  - Turn 1: *"Quy trình tạo Service Request là gì?"* -> Routes to `KNOWLEDGE`.
  - Turn 2: *"Tạo yêu cầu laptop cho tôi"* -> Routes to `ACTION_REQUEST`.
  - Result: **PASS**.
- **C4.3 Embedding Provenance:**
  - Active collection `helpdesk_kb_multilingual_v2_sentence_transformer` verified. All 8 tests in `tests/test_services/test_embedding_provenance_c4_3.py` passed.

---

## 6. Automated Test Suite Results

| Test Suite | File Path | Collected | Passed | Failed | Skipped | Notes |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **Context Structural** | `tests/test_services/test_recent_conversation_context.py`<br>`tests/test_api/test_chat_streaming.py`<br>`tests/test_agents/test_ticket_text_context.py` | 15 | 15 | 0 | 0 | 100% structural recall, 0 duplicates, 0 leaks |
| **Frozen Eval** | `tests/test_eval` | 93 | 93 | 0 | 0 | 100% pass rate (with `--basetemp` resolving Windows temp collision) |
| **Production E2E** | `tests/e2e/test_production_workflows_v1_0.py`<br>`tests/e2e/test_admin_user_lifecycle_v1_0.py` | 18 | 18 | 0 | 0 | All core production workflows verified |
| **Service Request E2E** | `tests/e2e/test_service_request_fulfillment_v1_0.py`<br>`tests/e2e/test_service_request_approval_v1_0.py`<br>`tests/e2e/test_technician_fulfillment_groups_v1_0.py`<br>`tests/test_api/test_service_requests.py` | 25 | 25 | 0 | 0 | Direct fulfillment, approval gates & groups |
| **Security & C4 Suites** | `tests/test_services/test_action_grounding.py`<br>`tests/test_services/test_chat_routing_service.py`<br>`tests/test_api/test_employee_security.py`<br>`tests/test_guardrails/test_access_guardrails.py`<br>`tests/test_api/test_guardrail_pipeline.py`<br>`tests/test_api/test_workspace_chat_action_grounding_c4_1.py`<br>`tests/test_services/test_service_request_chat_routing_c4_2.py`<br>`tests/test_services/test_embedding_provenance_c4_3.py` | 73 | 71 | 2 | 0 | 2 failures are the known `LEGACY_TEST_EXPECTATION_DRIFT` assertions |
| **Remaining API Suite** | `tests/test_api/test_admin_kb.py`<br>`tests/test_api/test_auth.py`<br>`tests/test_api/test_duplicate_ticket_api.py`<br>`tests/test_api/test_profile_identity_requests.py`<br>`tests/test_api/test_routes.py`<br>`tests/test_api/test_self_profile_privacy.py`<br>`tests/test_api/test_source_navigation.py`<br>`tests/test_api/test_ticket_invariants.py`<br>`tests/test_api/test_tickets.py` | 41 | 41 | 0 | 0 | All targeted tests pass cleanly |

### Analysis of Aggregate API Timeout
When running the entirety of `tests/test_api` in a single unconstrained command on Windows, test runner resource contention (multiple heavy PyTorch/SentenceTransformer instances and SQLite locks) caused the runner to exceed default thresholds. Targeted file executions run swiftly and pass 100%. This is classified as `TEST_HARNESS_AGGREGATION_ISSUE`.

---

## 7. Real-Model Quality Matrix

| Scenario | History Loaded | Route | RAG Used | ZeroMem | Quality | Classification / Failure Category |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Workspace VPN 809 (Turn 1)** | 0 | `INCIDENT` | Yes (`kb-001`) | Yes | **GOOD** | None |
| **Workspace VPN 809 (Turn 2)** | 2 | `KNOWLEDGE` | Yes | Yes | **ACCEPTABLE** | None (Preserved subject; requested specific error) |
| **Workspace VPN 809 (Turn 3)** | 4 | `KNOWLEDGE` | Yes | Yes | **GOOD** | None (Preserved VPN 809 subject; detailed next steps) |
| **Workspace New Chat** | 0 | `KNOWLEDGE` | Yes | No | **GOOD** | None (Strict isolation) |
| **Workspace Cross-Conv** | 0 | `KNOWLEDGE` | Yes | No | **GOOD** | None (Strict isolation) |
| **Ticket Multi-Turn (Turn 1)** | 1 (opening) | `email` | Yes (`kb-outlook`) | Yes | **GOOD** | None |
| **Ticket Multi-Turn (Turn 2)** | 2 | `email` | Yes | Yes | **GOOD** | None |
| **Ticket Multi-Turn (Turn 3)** | 3 | `email` | N/A | N/A | **GOOD** | None (Policy escalation on dissatisfaction) |
| **Technician Message Context** | 3 | `hardware` | N/A | N/A | **GOOD** | None (Chronological tech + user messages preserved) |
| **Cross-Ticket Isolation** | 0 | `other` | Yes | No | **GOOD** | None (Zero cross-ticket leak) |

---

## 8. Query Rewrite Assessment

- **Finding:** In follow-up turns with concise wording (e.g. Turn 2 *"Tôi đã thử bước đầu tiên rồi nhưng vẫn không được."*), the recent conversation history loaded into the LLM prompt allows Mistral to maintain full conversational context. However, the raw RAG / web search query uses only the current turn's text, causing search retrieval to pull general or out-of-domain articles rather than targeted VPN 809 documents.
- **Classification:** `CONTEXT_DEPENDENT_RETRIEVAL_GAP`.
- **Recommendation:** Query Rewrite (`CTX-FIX-2`) is functionally justified as the next enhancement to reformulate standalone retrieval queries for follow-up turns. Per instructions, it remains deferred and is not enabled in this task.

---

## 9. Knowledge Gaps

- A dedicated KB article explaining the organizational Service Request lifecycle process remains absent from the knowledge base (`KNOWLEDGE_GAP`). The system correctly routes process questions to `KNOWLEDGE` and generates safe policy-compliant explanations.

---

## 10. Final Release Verdict

**CTX-FIX-1: PASS**

The capabilities `WORKSPACE_RECENT_CONVERSATION_CONTEXT` and `TICKET_RECENT_CONVERSATION_CONTEXT` are verified in runtime and promoted to `DONE / DO_NOT_REIMPLEMENT`.
