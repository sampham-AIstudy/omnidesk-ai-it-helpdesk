# C4.3 Chroma embedding migration — 2026-08-16

## Verdict

**PASS.** `RTE-003` is resolved. The live KB collection is now
`helpdesk_kb_multilingual_v2_sentence_transformer`; the legacy hashing
collection remains intact and a filesystem snapshot is retained.

## Reproduction and root cause

Before migration, Settings requested
`sentence_transformers/paraphrase-multilingual-MiniLM-L12-v2`, but
`helpdesk_kb_multilingual_v1` recorded `embedding_backend=hashing`. Both
spaces happen to be 384-dimensional, which did not establish compatibility.
The former RAG implementation selected the query embedder from legacy
collection metadata, silently concealing the contradictory configured state.

The intended local SentenceTransformer package/model loaded successfully from
cache, produced finite, normalized 384-dimensional vectors, and no download is
now attempted at runtime.

## Safe migration

- Source: `helpdesk_kb_multilingual_v1` (432 documents).
- Backup: `data/chroma_backups/c4_3_20260816_0001` (18,314,538 bytes).
- Target: `helpdesk_kb_multilingual_v2_sentence_transformer` (432 documents).
- Migration was a separate collection re-embedding operation; nothing was
  deleted or rebuilt in place.
- Stable IDs, documents, and metadata have exact inventory parity:
  `abc9e7e570cdabd81537ec9092873df159ddf0e9b5719542747bae5d78eb85b9`;
  there are no missing or extra IDs.

The target records explicit provider/model/dimension/normalization/cosine and
migration provenance. The old KB collection stays available exclusively for
the documented compatible rollback.

## Runtime controls

The KB query/index path now uses the configured canonical embedder and validates
persisted collection provenance at initialization. A missing model fails with a
controlled initialization error; it cannot silently become hashing. A metadata
mismatch is detected before vector query/indexing and RAG returns no evidence
rather than searching an incompatible space.

Ticket-duplicate and episodic-memory collections are distinct, legacy hashing
indexes. Their metadata was made explicit and their calls now embed/query using
their own recorded hashing backend, so they are not mixed with KB vectors.

## Retrieval and security checks

The deterministic old/new comparison covers VPN, Outlook/email, password,
Service Request process, hardware, access/VPN, Microsoft 365/license, and an
unsupported question. Expected-class Hit@5 is unchanged at 6/7. VPN,
Outlook/email, and password rank direct sources higher on the new index. The
remaining Service Request process miss occurs in both old and new collections:
the KB lacks a dedicated process article; it is not a migration regression.
Full rows are in `chroma_embedding_retrieval_comparison_c4_3.json`.

ACL remained intact: `real_estate` does not retrieve corporate SAP records
`kb-019`/`kb-020`; `corporate` retrieves `kb-019` for the SAP query.

## Admin KB and local runtime

An authenticated Admin created, updated, and deleted one temporary KB article
through the real API. Chroma counts were 432 → 433 → 433 → 432; cleanup
completed. Startup loaded the canonical SentenceTransformer model and reported
432 KB documents. Health and seven controlled authenticated chat requests all
returned 2xx, with zero unexpected 5xx. The Service Request process request
used retrieval; C4.1 standalone handoff stayed non-authoritative.

## Validation

- Python compile and Ruff on changed scope: pass.
- C4.3 provenance tests: 8 passed.
- Action/access regression: 17 passed.
- C4.1/C4.2 routing regression: 41 passed.
- Full business E2E: 41 passed (Production/C1 18, SR 23).
- Frozen `tests/test_eval`: 93 passed.
- Guardrail suite: 21 passed plus two known legacy wording assertion drifts;
  both requests still blocked safely.

## Rollback

Set `CHROMA_COLLECTION_NAME=helpdesk_kb_multilingual_v1` and
`EMBEDDING_BACKEND=hashing`, then restart the backend. The old collection and
backup remain; no re-ingestion is needed.

## Non-blocking follow-ups

`RTE-004` (graceful query-decomposition fallback), `RTE-008` (audit harness
telemetry), the two legacy guardrail wording assertions, and the LangChain
embedding-class deprecation warning remain outside C4.3 scope.
