# Observability (host-run)

The application records request traces, AI operation spans, business metrics,
and JSONL audit records without requiring Docker.

## What is instrumented

- HTTP requests: FastAPI, HTTPX, and SQLAlchemy spans.
- AI workflow spans: `ai.chat`, `ai.classify`, `guardrail.input`,
  `guardrail.output`, `rag.retrieve`, and `llm.generate`.
- Metrics: operation duration and errors, plus ticket-created, guardrail-block,
  handoff, and AI-resolved business events.
- Logs: `.ai-log` JSONL records include the same W3C `trace_id` returned in
  `X-Trace-ID` response headers.

Prompts, completions, user identifiers, email addresses, tokens, and retrieved
document text are intentionally not added to telemetry attributes.

## Enable export without Docker

Run the app normally. Keep `OTEL_ENABLED=false` until an OTLP-compatible
Collector or cloud observability endpoint is available. Then configure:

```env
OTEL_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=YOUR_HOST:4317
OTEL_SERVICE_NAME=helpdesk-ai-agent
OTEL_TRACES_SAMPLER=parentbased_traceidratio
OTEL_TRACES_SAMPLER_ARG=1.0
```

`OTEL_EXPORTER_OTLP_ENDPOINT` must point to a service managed outside this
repository (for example, the team's Collector or an OTLP-compatible provider).
Use the standard `host:port` form for the gRPC exporter.
