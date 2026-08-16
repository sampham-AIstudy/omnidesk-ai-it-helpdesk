# C4.2 Service Request Knowledge-vs-Action Routing Repair — 2026-08-15

## Scope

Only `RTE-005` was repaired. Chroma, embeddings, retrieval configuration,
prompts, golden/evaluation artifacts, Service Request APIs/workflow, and C4.1
action-grounding code were not changed.

## Reproduction before the fix

The exact overlapping informational request was:

`Quy trình tạo Service Request là gì?`

The deterministic trace before the fix was:

- normalized input: `quy trinh tao service request la gi?`
- `_ACTION` matched `tao … request`
- route: `action_request`; confidence: `0.92`
- tool intent: true; retrieval: false
- real authenticated `POST /api/v1/chat` returned HTTP 200 with `Chưa có thay
  đổi nào được thực hiện.`

`Service Request` by itself was already a domain noun and did not force the
route. The first wrong decision was the broad legacy action regex taking
precedence over the informational/process semantics whenever the question also
included an operation verb such as `tạo`.

## Repair and precedence

The existing deterministic router keeps its canonical route names. It now
evaluates, after ticket status:

1. explicit process/policy/explanation questions → `knowledge`;
2. execution intent with an imperative/requester semantic → `action_request`;
3. the existing legacy action matcher → `action_request`;
4. incident signals → `incident`; otherwise → `knowledge`.

The new knowledge signal is deliberately small: process, how-to, policy,
conditions, and question cues such as `là gì`, `ai duyệt`, `cần những thông
tin gì`, `gồm những bước nào`, and `hoạt động thế nào`. It has precedence only
when a sentence is framed as information seeking. Execution matching requires
signals such as create/send/register, requester desire, or `cho/giúp tôi`.

The unrelated short vague report `Không được` is now correctly handled by the
existing clarification rule, rather than falling through to `knowledge`.

## Runtime verification after the fix

The backend was stopped and restarted from the current source with
`.\\.venv\\Scripts\\python.exe run.py` before this check.

| Request | Route/pipeline | Result |
| --- | --- | --- |
| `Quy trình tạo Service Request là gì?` | `knowledge`, retrieval required | HTTP 200; evidence pipeline executed; no mutation claim |
| `Sau khi gửi Service Request thì ai duyệt?` | `knowledge`, retrieval required | HTTP 200; evidence pipeline executed |
| `Tạo Service Request xin laptop cho tôi` | `action_request`, no retrieval | HTTP 200; canonical `NOT_INVOKED` reply |
| `Tôi cần gặp chuyên viên IT` | route telemetry unchanged; C4.1 gate | HTTP 200; no fabricated handoff |

The two knowledge requests returned `retrieval_required=true` and
`retrieval_decision=required`. Retrieval quality was not evaluated because
the separate persisted-Chroma drift remains open.

## Tests

Added `tests/test_services/test_service_request_chat_routing_c4_2.py` with:

- all twelve required Service Request/VPN/Git knowledge-vs-action cases;
- four Vietnamese paraphrase/accent/case controls;
- greeting, incident, ticket-status, clarification, and human-handoff negative
  controls.

No frozen routing-contract conflict was found: `tests/test_eval` remains
93 passing without changing evaluation inputs or expectations.

## Validation

- Python compile: PASS.
- Ruff changed scope: PASS.
- C4.2 routing + existing routing + C4.1 action-grounding + access controls:
  **50 passed**.
- Auth: **8 passed**.
- `tests/test_eval`: **93 passed**.
- Full Service Request E2E: **23 passed**.
- Production workflow + C1 E2E: **18 passed**.
- Full E2E collection: **41 passed**.

### Legacy guardrail expectation drift

The two known `test_guardrail_pipeline.py` assertions still fail without a
security regression and were not changed:

- expected old reason `Matched local injection patterns`; actual safe block
  reason `DUAL_USE_SECURITY_REQUEST`;
- expected body text containing `blocked`; actual API behavior is still HTTP
  400 with a more specific safe Vietnamese refusal.

Both inputs are blocked before workflow/retrieval. This is
`LEGACY_TEST_EXPECTATION_DRIFT`; reconcile that test contract separately,
without weakening guardrails.

## Status

`RTE-005` is resolved. The remaining release blocker is `RTE-003`: persisted
Chroma embedding backend drift. Overall release verdict remains **NOT_READY**.
