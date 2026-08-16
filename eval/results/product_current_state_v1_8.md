# Product current state v1.8 — 2026-08-16

This version supersedes v1.7 following the successful runtime validation of `CTX-FIX-1` (Short-Term Conversation Context Continuity for Workspace Chat and Ticket Threads).

## Context Continuity Accepted (CTX-FIX-1)

Short-term conversation context continuity is verified in both structural and manual real-Mistral runtime execution:

- **Workspace Chat:**
  - Persisted endpoint (`POST /api/v1/chat/conversations/{id}/messages`) loads up to 8 chronological messages scoped to the authenticated owner.
  - Current user question is deduplicated by stable ID (appears exactly once).
  - New chat isolation verified (0 previous messages leaked).
  - Cross-conversation leak = 0.
  - Stateless endpoints (`POST /api/v1/chat`, `POST /api/v1/chat/stream`) intentionally remain stateless.

- **Ticket Threads:**
  - Ticket message endpoint (`POST /api/v1/tickets/{id}/messages`) loads up to 5 chronological messages (user, agent, technician) scoped to the ticket.
  - System/audit messages are filtered from the LLM prompt.
  - Ticket metadata, RAG, and Zero-Mem episodic retrieval are retained.
  - Recent/current message IDs are deduplicated from Zero-Mem evidence.
  - Cross-ticket leak = 0.

- **Registered Architectural Capabilities:**
  - `WORKSPACE_RECENT_CONVERSATION_CONTEXT`: **DONE / DO_NOT_REIMPLEMENT**
  - `TICKET_RECENT_CONVERSATION_CONTEXT`: **DONE / DO_NOT_REIMPLEMENT**

## Runtime Release Gate

The product remains **RUNTIME_STABLE** for the verified local release gate. All baseline invariants are preserved:

- **C4.1 (Action-Grounding):** Verified. Handoff attempts without trusted `ActionResult SUCCEEDED` return safe `NOT_INVOKED` explanations.
- **C4.2 (Routing):** Verified. Service Request process inquiries route to `KNOWLEDGE`, while execution requests route to `ACTION_REQUEST`.
- **C4.3 (Embedding Provenance):** Verified. Active collection is `helpdesk_kb_multilingual_v2_sentence_transformer` with SentenceTransformer embeddings.
- **Frozen Eval:** 93/93 tests passed (100%).
- **Production & Service Request E2E:** 18/18 Production workflows and 25/25 Service Request tests passed.
- **Aggregate API Runner Timeout:** Classified as `TEST_HARNESS_AGGREGATION_ISSUE` (all 41 constituent API tests pass individually).

## Known Findings & Deferred Enhancements

1. **Query Rewrite (`CTX-FIX-2`):** Measurable `CONTEXT_DEPENDENT_RETRIEVAL_GAP` observed during follow-up turns when retrieval query lacks conversational context. Reformulation is functionally justified and remains deferred.
2. **Knowledge Gap:** Absence of dedicated Service Request process KB article in KB is classified as `KNOWLEDGE_GAP` (not a retrieval defect).
3. **Legacy Guardrail Assertions:** 2 test assertions in `tests/test_api/test_guardrail_pipeline.py` show `LEGACY_TEST_EXPECTATION_DRIFT`; actual short-circuit blocking is verified safe.

## Scoring Contract

The frozen v1.2/v1.3 Service Request lifecycle denominator remains 100%: direct fulfillment 50/50 and approval-gated fulfillment 50/50.

## Next Action

Do not modify production code or enable Query Rewrite automatically. Any follow-up must be separately planned and approved.
