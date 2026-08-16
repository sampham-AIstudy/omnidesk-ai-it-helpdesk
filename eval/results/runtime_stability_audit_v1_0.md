# Runtime stability audit v1.0 — 2026-08-15

## Scope and verdict

C4 stopped feature work and exercised the current local application with its
real SQLite database, Chroma store, authentication, Mistral provider, and SSE
transport. No prompt, judge, retrieval policy, model choice, Service Request
workflow, or incident lifecycle was changed.

**Verdict: NOT_READY.** The backend, frontend, authentication, primary LLM,
and SSE path are stable in controlled local use after two small runtime
configuration fixes. Release remains blocked by a proven vector-index/backend
drift and two AI semantic/product-behavior gaps in frozen areas.

## Exact local startup path

From the repository root:

```powershell
.\.venv\Scripts\python.exe run.py
```

This starts `uvicorn src.main:app` with reload on port 8000. The startup log
confirmed the watcher root was this P-236 source tree and the venv interpreter
was used. The normal frontend command is:

```powershell
cd frontend
npm run dev
```

Its script is `next dev --webpack`; it served on port 3000. Turbopack was not
enabled. Node was 25.9.0, npm 11.12.1, and Python was 3.11.9.

Before startup there were old Python/Node processes, but no listener on 8000,
3000, or 3001. The audit used freshly started local backend/frontend instances.

## Configuration and startup

Backend `Settings` reads the root `.env` through Pydantic; values are not
implicitly exported into `os.environ`. Frontend Next reads `frontend/.env.local`;
its effective public API origin is `http://localhost:8000`, matching the axios
client's `/api/v1` base and backend CORS configuration.

The effective primary provider is Mistral `mistral-small-2506`; the fast
classifier is `ministral-3b-2512`. Chroma is configured as
`helpdesk_kb_multilingual_v1` at `./data/chroma`, and the configured embedding
model is `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`.
Redis/Upstash cache was reachable at startup (hostname only was logged).

The following non-secret configuration issues were found:

- `GROQ_API_KEY` was present in `.env` but was ignored by the fallback factory.
  This is fixed in C4 by adding the typed `groq_api_key` setting and using it.
- `OTEL_ENABLED=true` pointed to an unavailable `localhost:4317` collector.
  It produced continuous exporter errors and made a reload wait about 38
  seconds during exporter flush. C4 sets local `.env` to `OTEL_ENABLED=false`,
  preserving local trace correlation while disabling only unavailable OTLP
  export. This matches `.env.example` host-local guidance.
- `SLA_ESCALATION_EMAIL` remains present in `.env` but has no matching runtime
  setting or code reference. It is recorded as an ignored legacy variable, not
  changed as part of C4.

Startup after the configuration fixes completed in approximately 1.4 seconds:
database initialized, demo users seeded, 35 KB seed entries checked, Chroma
count reported, duplicate index synchronized, and application ready. There
were no import, SQLAlchemy, migration, enum, index, provider-initialization,
or background-task failures.

## Database and health

The actual `data/helpdesk.db` is compatible with the current SQLAlchemy model
requirements:

- `users.is_active` exists.
- Service Requests contain assignee, assignment/completion, approval/rejection,
  and `fulfillment_group` fields.
- `audit_logs.service_request_id` and its lookup index exist.
- `technician_fulfillment_groups` exists with its unique technician/group
  constraint and lookup indexes.
- `PRAGMA foreign_key_check` returned no violations.

`GET /health` returned 200 with `status=ok`, `env=development`, 432 KB
documents, and Redis cache status. It demonstrates application liveness and
vector-store availability; it does not separately expose DB or primary-provider
readiness, which remains an observability enhancement rather than a liveness
failure.

## Provider, fallback, embedding, and retrieval

Real generation requests reached Mistral's chat-completions endpoint with HTTP
200. Controlled RAG requests took about 4.0–7.6 s. The active factory after C4
contains:

1. `ChatMistralAI(mistral-small-2506)` primary;
2. `ChatGroq(llama-3.1-8b-instant)` fallback;
3. `ChatGoogleGenerativeAI(gemini-3.5-flash-lite)` fallback;
4. local Ollama `mistral` fallback.

Groq is now registered from `.env`. Ollama was not listening at 11434, so it
is an unavailable last-resort fallback rather than the selected runtime path.
A direct Gemini probe from the audit shell could not reach it because that
shell had a proxy pointed at `127.0.0.1:9`; this is an audit-shell environment
constraint, not evidence that the backend's working Mistral path is broken.

No reranker implementation or configured reranker was found; retrieval uses
the existing hybrid scoring path only.

The Chroma collection opens and contains 432 documents, 384-dimensional
vectors, and ACL filtering works: a corporate-restricted SAP source is not
visible to a real-estate requester. However its persisted metadata says
`embedding_backend=hashing`, while current settings request
`sentence_transformer`. Consequently runtime deliberately selects the hashing
embedder and never loads the configured transformer. This is proven stale/index
drift, not an empty store. C4 did not rebuild or delete the user's vector data;
a controlled re-embedding plan is required before release.

Complex-query decomposition reached the real fast Mistral model but logged
`JSONDecodeError` and safely fell back to the original query. This is degraded
but non-crashing retrieval behavior; no prompt/parser change was made because
the AI/RAG baseline is frozen.

## Chat, stream, guardrails, auth, and frontend contract

`POST /api/v1/chat` was exercised as active `employee1` after real login and
`/auth/me`. Greeting, ticket-status, ambiguity clarification, prompt-injection
blocking, supported KB, unsupported KB abstention, incident, and multi-intent
paths all returned controlled HTTP 200 responses. The primary LLM was actually
called for retrieval routes. Input injection was blocked before retrieval; a
normal ambiguity produced clarification rather than a fabricated diagnosis.

`POST /api/v1/chat/stream` returned `text/event-stream`, emitted `meta`, 102
token events, and exactly one `done` event for a real Mistral generation.
The final event matched the documented `ChatResponse` shape. The frontend does
not currently consume this standalone SSE endpoint; its workspace uses the
persisted conversation API. That API was verified to create exactly one user
message and one matching assistant message for one send.

The frontend axios client, route prefix, JSON content type, Authorization
header, 401 session clearing, and Next public origin all match backend routes.
There is no stale host/prefix/field mismatch. The client renders API failures
rather than claiming mutation success. The non-stream conversation UX is a
design choice, not an SSE parser mismatch.

## Real behavior matrix

| Case | Actual route | Result |
| --- | --- | --- |
| Greeting | direct response | GOOD |
| Supported VPN KB question | incident/RAG, real Mistral | ACCEPTABLE |
| Unsupported policy question | knowledge/RAG, explicit insufficient-evidence abstention | ACCEPTABLE |
| Ambiguous IT report | clarification | GOOD |
| Wi-Fi incident | incident/RAG | ACCEPTABLE, but no final cited source was exposed |
| Ticket-status request | ticket-status tool gate | GOOD |
| Service Request *process question* | action-request gate | **BAD** — replied that no change was made |
| Prompt injection | input guardrail block | GOOD |
| VPN + password multi-intent | incident/RAG | ACCEPTABLE |
| Human-escalation chat request | knowledge/RAG | **BAD** — answer claimed a ticket was automatically transferred although standalone chat has no action/ticket context |

The two BAD cases are classified as `ROUTING_ERROR` and
`PRODUCT_BEHAVIOR_GAP`/`ACTION_GROUNDING` respectively. They belong to areas
explicitly frozen by the current source of truth, so C4 records rather than
changes them.

## Controlled stability run

Three iterations each of health, auth/me, ticket list, employee Service Request
list, direct chat, and direct SSE chat completed: **18/18 2xx**, no expected
4xx, **0 unexpected 5xx**, **0 timeouts**, and **0 unhandled exceptions**.
Maximum latency was 19 ms because the repeated chat cases used the deterministic
greeting route.

## Runtime error registry

| ID | Classification | Severity | Status | Root cause / impact |
| --- | --- | --- | --- | --- |
| RTE-001 | RUNTIME_CONFIGURATION_ERROR | P1 | Fixed | Groq fallback key in `.env` was bypassed by direct `os.getenv`; fallback was absent. |
| RTE-002 | PROVIDER/OTEL CONFIGURATION_ERROR | P2 | Fixed locally | OTLP exporter enabled with no collector at 4317; noisy retries and slow reload shutdown. |
| RTE-003 | RETRIEVAL_ERROR | P1 | Open | Chroma metadata selects hashing although settings request SentenceTransformer; quality/config drift. |
| RTE-004 | RETRIEVAL_ERROR | P2 | Open | Fast decomposition response is not valid JSON; safe original-query fallback is used. |
| RTE-005 | ROUTING_ERROR | P1 | Open/frozen | Informational Service Request question is treated as an action request. |
| RTE-006 | PRODUCT_BEHAVIOR_GAP / ACTION_GROUNDING | P1 | Open/frozen | Standalone chat can claim a human handoff that was never persisted or executed. |
| RTE-007 | PROVIDER_ERROR | P3 | Audit-shell-only | Direct Gemini probe was blocked by the audit shell's invalid localhost proxy; backend Mistral path is independently proven healthy. |
| RTE-008 | TEST HARNESS GAP | P3 | Open | Several API test files can stall when aggregated, while relevant cases pass independently; no equivalent local HTTP failure reproduced. |

## Test-versus-runtime gaps

Tests correctly cover contracts, RBAC, SQLite state machines, mocked providers,
and deterministic guardrail routes. They did not detect RTE-001 because provider
construction did not assert `.env`-backed Groq registration. They did not detect
RTE-002 because test telemetry does not use a missing external collector. They
use isolated DB/vector fixtures rather than the persisted local Chroma metadata,
so they do not expose RTE-003. Mocked/evaluation paths also do not prove that a
real model will return valid decomposition JSON or avoid the two RTE-005/RTE-006
semantic claims.

## Validation

- Python compile: PASS.
- Ruff changed scope: PASS.
- `tests/test_eval`: **93 passed**.
- Full Service Request E2E: **23 passed**.
- C1 lifecycle + Production E2E + action grounding + new fallback config test:
  **27 passed**.
- Auth: **8 passed**; routing: **7 passed**; access guardrails: **3 passed**.
- Real SSE HTTP smoke: PASS; conversation persistence smoke: PASS.
- Frontend lint: **0 errors, 120 pre-existing warnings**.
- Frontend TypeScript: PASS.
- Product guards: PASS.
- `next build --webpack`: PASS.

The frozen golden dataset and evaluation expectations were not changed.
