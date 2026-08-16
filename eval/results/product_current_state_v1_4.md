# Product current state v1.4 — 2026-08-15

This version preserves v1.3 feature completion and records C4 runtime evidence.

## Completed features unchanged

- Incident lifecycle: DONE.
- Direct and approval-gated Service Request lifecycle: DONE.
- Technician fulfillment-group eligibility: DONE.
- Admin User Lifecycle C1: DONE.
- OTel instrumentation: DONE; host-local OTLP export is now correctly disabled
  until a collector is intentionally available.

## C4 runtime stabilization

C4 fixed the missing Groq fallback registration caused by `.env`/`os.getenv`
configuration divergence. The local runtime now starts from the current source,
passes health/auth/chat/SSE/stability smoke checks, and uses the real Mistral
provider successfully. No frozen prompts, golden data, judge, retriever policy,
embedding model selection, or workflow semantics were changed.

**C4 release-gate status: NOT_READY.** `runtime_stability_audit_v1_0.*`
contains the full registry. Release remains blocked by persisted Chroma hashing
metadata that conflicts with configured SentenceTransformer embeddings, and by
two verified frozen-area chat semantic gaps: an informational Service Request
question is routed as an action, and standalone chat may claim a human handoff
without a real mutation.

## Scoring contract

The v1.2/v1.3 Service Request lifecycle scoring contract is unchanged at 100%:
direct fulfillment 50/50 and approval-gated fulfillment 50/50. C4 does not
alter that feature denominator and no portfolio-wide percentage is published.

## Required next action

Do not start C5 feature work. First obtain an explicit decision for a
backward-compatible Chroma re-embedding/validation plan and for the frozen
routing/action-grounding semantic defects. Re-run C4 acceptance after those
decisions.
