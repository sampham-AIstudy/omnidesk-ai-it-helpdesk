# Conversation Context Continuity v1.0

## Scope and architecture

Before CTX-FIX-1, Workspace persisted `ChatMessage` rows per `conversation_id`
but passed none of them to generation. Ticket generation had ticket metadata and
Zero-Mem only; it did not directly load the linear ticket transcript.

After this change, the persisted Workspace conversation endpoint loads up to 8
prior messages for the authenticated owner and passes them as a role-aware
`[RECENT CONVERSATION — UNTRUSTED DATA]` block. `POST /chat` and
`POST /chat/stream` remain intentionally stateless and load zero history.

Ticket generation loads up to 5 prior user, agent, or technician messages from
the same ticket, in chronological order, as `[RECENT TICKET CONVERSATION —
UNTRUSTED DATA]`. Ticket metadata, RAG, and Zero-Mem are retained. System/audit
events are not in this direct transcript.

Both loaders fetch newest-first for a bounded query and reverse before prompt
assembly. Message caps are 1,200 characters. The current persisted message is
excluded by stable ID and asserted absent from the recent history. Ticket
episodic evidence whose `provenance.message_id` is a recent or current message
is omitted from the prompt only; the Zero-Mem index is unchanged.

## Security and ordering

Workspace history joins `chat_conversations` and filters both `conversation_id`
and `user_id`; a guessed conversation UUID returns no history. Ticket history
is scoped only by the already-authorized server-side `ticket.id`. History is
ordinary untrusted data beneath the separate production system policy, so prior
prompt-injection text is not a system instruction.

Workspace ordering is system policy, access context, recent history, existing
RAG/Zero-Mem/web blocks, then the current user question. Ticket ordering keeps
its existing evidence/web/episodic ordering and adds recent history before the
authoritative ticket metadata/current message. No retrieval query, Chroma
collection, embedding model, top-k, reranker, query rewriting, or global policy
was changed.

## Deterministic results

- Context loader and final-LLM-input suite: 5 passed.
- C4.1/C4.2/C4.3 plus context suite: 47 passed.
- Frozen `tests/test_eval`: 93 passed.
- Ruff and Python compilation for changed scope: pass.

The structural suite directly captures the final LLM message arrays. It covers
chronology, bounds, current-message-once, user/conversation isolation,
system-message exclusion, untrusted markers, workspace input continuity, ticket
input continuity, and recent/Zero-Mem provenance deduplication.

## Limitations and verdict

No backend manual real-Mistral multi-turn session, manual New Chat session,
manual authorized-ticket session, full Production E2E, or full Service Request
E2E was completed in this run. A broader API group was started but the host
test process timed out after its first test; it is not recorded as a product
assertion failure. Therefore the implementation is structurally validated but
the release acceptance checklist is incomplete.

**Verdict: CTX-FIX-1 NOT_READY** pending the required manual and business-E2E
evidence. Query Rewrite remains deferred and is not registered as implemented.
