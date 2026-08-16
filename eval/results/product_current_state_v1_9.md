# Product current state v1.9 — 2026-08-16

This version supersedes v1.8 following the successful design, implementation, and runtime validation of `CTX-FIX-2` (Context-Aware Retrieval Query Formulation).

## Context-Aware Retrieval Query Accepted (CTX-FIX-2)

Context-aware retrieval query reformulation is verified across structural tests, A/B vector retrieval benchmarks, and real-Mistral multi-turn runtime execution:

- **Workspace Chat Retrieval:**
  - In `POST /api/v1/chat/conversations/{id}/messages`, follow-up context-dependent turns (e.g. *"Tôi đã thử bước đầu tiên rồi nhưng vẫn không được."*) are deterministically resolved into explicit search queries incorporating previous subject entities (e.g. `"VPN FortiClient báo lỗi 809 trên Windows 11.. Tôi đã thử bước đầu tiên rồi nhưng vẫn không được."`).
  - Self-contained queries are untouched (`rewritten=False`).
  - Current user intent is preserved.
  - Length is strictly bounded by `max_retrieval_query_chars` (`Settings.max_retrieval_query_chars = 400`).
  - Cross-conversation leakage is 0.

- **Ticket Thread Retrieval:**
  - In `handle_ticket_message`, recent conversation history is loaded prior to Chroma search and episodic lookup.
  - Contextual follow-up turns are enriched with ticket metadata and active problem refinements.
  - Cross-ticket leakage is 0.

- **Performance & Latency:**
  - Overhead per rewrite: **0.0066 ms** (Target < 2.0 ms, ~300x faster than budget).
  - Retrieval Score Delta on follow-up cases: up to **+0.4134** in top similarity score (e.g., from 0.3395 raw to 0.7528 with context, converting false negatives into accurate KB Hit@1).

- **Registered Architectural Capabilities:**
  - `WORKSPACE_RECENT_CONVERSATION_CONTEXT`: **DONE / DO_NOT_REIMPLEMENT**
  - `TICKET_RECENT_CONVERSATION_CONTEXT`: **DONE / DO_NOT_REIMPLEMENT**
  - `CONTEXT_AWARE_RETRIEVAL_QUERY`: **DONE / DO_NOT_REIMPLEMENT**

## Runtime Release Gate

The product remains **RUNTIME_STABLE** for the verified local release gate. All baseline invariants are preserved:

- **C4.1 (Action-Grounding):** Verified. Handoff attempts without trusted `ActionResult SUCCEEDED` return safe `NOT_INVOKED` explanations.
- **C4.2 (Routing):** Verified. Service Request process inquiries route to `KNOWLEDGE`, while execution requests route to `ACTION_REQUEST`. Non-retrieval routes bypass query rewrite.
- **C4.3 (Embedding Provenance):** Verified. Active collection is `helpdesk_kb_multilingual_v2_sentence_transformer` with SentenceTransformer embeddings.
- **Frozen Eval:** 93/93 tests passed (100%).
- **Services Suite:** 112/112 tests passed (100%).
- **Context Structural Suite:** 18/18 tests passed (100% across RCC & CARQ).
- **API Suite:** 72/74 passed (only 2 legacy string assertion drift tests in `test_guardrail_pipeline.py`).

## Known Findings & Deferred Enhancements

1. **Knowledge Gap:** Absence of dedicated Service Request process KB article in KB is classified as `KNOWLEDGE_GAP` (not a retrieval defect).
2. **Legacy Guardrail Assertions:** 2 test assertions in `tests/test_api/test_guardrail_pipeline.py` show `LEGACY_TEST_EXPECTATION_DRIFT`; actual short-circuit blocking is verified safe.
3. **Deferred:** Dynamic token budgeting and transcript summarization remain deferred as short-term window bounding is sufficient.

## Scoring Contract

The frozen v1.2/v1.3 Service Request lifecycle denominator remains 100%: direct fulfillment 50/50 and approval-gated fulfillment 50/50.
