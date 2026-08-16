# Production Observability v1.0

## Result

- Status: **COMPLETE_WITH_CONFIGURED_BACKENDS**
- W3C propagation: `traceparent`; `X-Trace-ID` is derived from the active span.
- Request IDs remain separate application correlation IDs.
- OTLP exporter failure is best-effort and cannot fail ticket/chat requests.

## Coverage

| Boundary | Instrumentation |
| --- | --- |
| HTTP | FastAPI spans; route-template count/duration metrics |
| Database | SQLAlchemy spans; no SQL parameters or SQL echo |
| Outbound HTTP | HTTPX automatic instrumentation |
| AI | `ai.guardrail`, `ai.route`, `ai.retrieval`, `ai.memory`, `ai.generation`, `ai.tool` |
| Workflow | ticket create and bounded workflow event counters |
| SSE | One request/generation lifecycle; no token-level spans |

## Safety and operations

- Application attributes use a strict scalar allow-list; Collector repeats this as a fail-closed allow-list.
- Structured logs include `trace_id`, `span_id`, and `request_id`; sensitive-looking values are redacted.
- Tempo, Prometheus, and Grafana are configured through Docker Compose. Grafana provisions the **P-236 Production Observability v1.0** dashboard.
- Sampling is controlled by `OTEL_TRACES_SAMPLER` and `OTEL_TRACES_SAMPLER_ARG`; development defaults to full sampling, while production must choose a measured ratio.

## Validation

| Suite | Result |
| --- | --- |
| Observability in-memory tests | 7 passed |
| Production E2E | 11 passed |
| Evaluation | 93 passed |
| Ruff, observability change scope | PASS |
| Python compile | PASS |
| `docker compose config --quiet` | PASS |

## Known limitations

- The local Collector/Tempo/Grafana stack was not started, so the trace-backend smoke is configured but not live-verified.
- LLM token usage is exported only when a provider supplies trusted usage fields.
- Repository-wide Ruff currently reports unrelated legacy violations outside this change scope.
- A separate guardrail test currently expects an older `block_reason`; it now receives the safe deterministic `DUAL_USE_SECURITY_REQUEST` classification. This unrelated assertion was not changed for telemetry.
