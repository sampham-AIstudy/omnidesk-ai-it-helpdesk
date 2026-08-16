# Product current state v1.6 — 2026-08-15

This version supersedes v1.5 only for the accepted C4.2 routing repair.
Completed Service Request workflows, C4.1 action-grounding protection, and the
frozen AI/RAG evaluation baseline are unchanged.

## C4.2 accepted

Workspace Chat now distinguishes information about the Service Request process
from a request to execute that process. Process, policy, approval, and
explanation questions route to the existing `knowledge`/retrieval pipeline.
Actual create/send/register requests route to `action_request`, where the
existing C4.1 action-grounding contract still returns `NOT_INVOKED` unless a
trusted workflow result exists.

`RTE-005` is resolved. No Service Request API/state-machine semantics, prompt,
retrieval configuration, golden data, or judge behavior changed. Evidence is in
`runtime_routing_fix_c4_2.*`.

## Release-gate status

**NOT_READY** remains correct because `RTE-003` is still open: the persisted
Chroma collection uses hashing while runtime configuration requests
SentenceTransformer embeddings. No re-embedding was performed.

## Scoring contract

The v1.2/v1.3 Service Request lifecycle scoring contract remains 100% for its
defined denominator: direct fulfillment 50/50 and approval-gated fulfillment
50/50. No portfolio-wide percentage is published.

## Next required action

Remain in runtime-stabilization mode. C4.3 requires an explicitly approved,
backward-compatible Chroma re-embedding/validation plan. Do not start feature
development.
