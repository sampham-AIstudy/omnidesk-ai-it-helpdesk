# Product current state v1.5 — 2026-08-15

This version supersedes v1.4 only for the accepted C4.1 runtime repair.
Completed product workflows and the frozen AI/RAG evaluation baseline are
unchanged.

## C4.1 accepted

Standalone Workspace Chat now enforces the existing canonical action-grounding
contract before RAG generation or SSE emission for human-handoff intent. With
no authoritative workflow invocation, it responds as `NOT_INVOKED` and directs
the employee to the real Ticket/Request Technician workflow. `/chat`,
`/chat/stream`, and Workspace conversation messages have parity. No ticket
mutation, fake tool, prompt, retrieval, judge, or golden artifact was changed.

The prior fabricated-handoff blocker `RTE-006` is resolved. See
`runtime_action_grounding_fix_c4_1.*` for reproduction and evidence.

## Release-gate status

**NOT_READY** remains correct. The remaining independent P1 blockers are:

- `RTE-005`: a Service Request process question can route to `ACTION_REQUEST`.
- `RTE-003`: persisted Chroma collection metadata uses hashing while current
  runtime configuration requests SentenceTransformer embeddings.

## Scoring contract

The v1.2/v1.3 Service Request lifecycle scoring contract remains 100% for its
defined denominator: direct fulfillment 50/50 and approval-gated fulfillment
50/50. No portfolio-wide percentage is published.

## Next required action

Remain in runtime-stabilization mode. Obtain explicit approval for either
C4.2 routing repair or C4.3 Chroma re-embedding; do not start feature work.
