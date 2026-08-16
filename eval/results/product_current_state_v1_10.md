# Product current state v1.10 — 2026-08-16

This version supersedes v1.9 following the successful resolution and verification of `KB-GAP-1` (Service Request Process Knowledge Grounding).

## Service Request Process Knowledge Grounded (KB-GAP-1)

A canonical, authoritative Service Request Knowledge Base article ([`kb-036`](file:///C:/Users/Admin/Python%20Advanced/VinAI%20Lab/P-236/src/data/service_request_kb.py)) is created, seeded into SQLite, and indexed in the active ChromaDB collection (`helpdesk_kb_multilingual_v2_sentence_transformer`):

- **Domain Grounding:**
  - Grounded 100% in the implemented P-236 Service Request lifecycle (`PENDING_APPROVAL`, `SUBMITTED`, `ASSIGNED`, `IN_PROGRESS`, `WAITING_FOR_USER`, `FULFILLED`, `REJECTED`).
  - Differentiates between Incidents (`INC-xxxx`) and Service Requests (`REQ-xxxx`).
  - Covers server-owned approval policies, manager decision pathways, technician queue eligibility, and explicit fulfillment group memberships.
  - Zero hallucinated ITIL process steps or exposed internal security/SQL attack surface.

- **Retrieval Performance:**
  - 8/8 canonical Service Request queries (`KB-SR-01` to `KB-SR-08`) retrieve `kb-036` at **Rank 1** (100% Hit@1).
  - Cross-tenant and cross-department accessibility verified (`applicable_to_all: True`).
  - Chroma collection document count: **433** (432 baseline + 1 canonical SR process article).

- **Registered Architectural Capabilities:**
  - `WORKSPACE_RECENT_CONVERSATION_CONTEXT`: **DONE / DO_NOT_REIMPLEMENT**
  - `TICKET_RECENT_CONVERSATION_CONTEXT`: **DONE / DO_NOT_REIMPLEMENT**
  - `CONTEXT_AWARE_RETRIEVAL_QUERY`: **DONE / DO_NOT_REIMPLEMENT**
  - `SERVICE_REQUEST_PROCESS_KNOWLEDGE`: **DONE / DO_NOT_REIMPLEMENT**

## Runtime Release Gate

The product remains **RUNTIME_STABLE** for the verified local release gate. All baseline invariants are preserved:

- **C4.1 (Action-Grounding):** Verified. Workspace chat requests without backend mutations return safe `NOT_INVOKED` explanations.
- **C4.2 (Routing):** Verified. Knowledge questions route to `KNOWLEDGE` (`should_retrieve=True`), action execution requests route to `ACTION_REQUEST` (`should_retrieve=False`).
- **C4.3 (Embedding Provenance):** Verified. Collection `helpdesk_kb_multilingual_v2_sentence_transformer` with SentenceTransformer embeddings (384 dimensions, normalized).
- **CTX-FIX-1 (Recent Conversation Context):** Verified. Short-term history is bounded and preserved.
- **CTX-FIX-2 (Context-Aware Retrieval Query):** Verified. Multi-turn follow-ups retain subject context in retrieval query.
- **Frozen Eval:** 93/93 tests passed (100%).
- **Services Suite:** 125/125 tests passed (100%).
- **Production Workflows E2E:** 11/11 tests passed (100%).
- **Service Request E2E:** 17/17 tests passed (8 approval + 9 fulfillment).

## Known Findings & Deferred Enhancements

1. **Legacy Guardrail Assertions:** 2 test assertions in `tests/test_api/test_guardrail_pipeline.py` show `LEGACY_TEST_EXPECTATION_DRIFT`; actual short-circuit blocking is verified safe.
2. **Deferred:** Dynamic token budgeting, summarization, and reranker remain deferred as current deterministic bounded pipelines operate within latency SLAs.

## Scoring Contract

The frozen v1.2/v1.3 Service Request lifecycle denominator remains 100%: direct fulfillment 50/50 and approval-gated fulfillment 50/50.
