# Product current state v1.7 — 2026-08-16

This version supersedes v1.6 for the accepted C4.3 runtime-infrastructure
repair. Existing workflows and the frozen AI/RAG evaluation contract are
unchanged.

## C4.3 accepted

`RTE-003` is resolved. The active KB collection is
`helpdesk_kb_multilingual_v2_sentence_transformer`, with explicit
SentenceTransformer provenance and a compatible query/index path. The legacy
hashing collection and a filesystem backup remain for rollback; no collection
was destructively rebuilt.

Startup, authenticated RAG runtime, ACL, Admin KB synchronization, C4.1 and
C4.2 regressions, Service Request E2E, Production/C1 E2E, and the frozen eval
all passed. Detailed evidence is in `chroma_embedding_migration_c4_3.*`.

## Runtime release gate

All three former C4 release blockers are now resolved:

- `RTE-006`: fabricated standalone handoff claims — resolved by C4.1.
- `RTE-005`: Service Request process/action routing — resolved by C4.2.
- `RTE-003`: Chroma embedding provenance drift — resolved by C4.3.

The product is **RUNTIME_STABLE** for the verified local release gate. This is
not a deployment claim. P2/P3 non-blocking debt remains: graceful
query-decomposition fallback (`RTE-004`), audit-harness telemetry (`RTE-008`),
and two obsolete guardrail wording assertions whose block decisions still pass.

## Scoring contract

The frozen v1.2/v1.3 Service Request lifecycle denominator remains 100%:
direct fulfillment 50/50 and approval-gated fulfillment 50/50. No
portfolio-wide percentage is published.

## Next action

Do not begin feature work automatically. Any follow-up must be separately
scoped against the remaining documented non-blocking runtime/test debt.
