# Observability stack

The Compose stack is deliberately limited to the operational signals needed by
this project:

```text
FastAPI + OpenTelemetry SDK -> Collector -> Tempo (traces)
                                      -> Prometheus (metrics) -> Grafana
```

Start it with the rest of the application:

```powershell
docker compose up --build
```

Grafana is available at `http://localhost:3001` (`admin` / `admin` for local
development); Prometheus is at `http://localhost:9090`; Tempo is at
`http://localhost:3200`. Grafana provisions both data sources automatically.

For a host-run backend, start the observability services first and set
`OTEL_ENABLED=true` plus `OTEL_EXPORTER_OTLP_ENDPOINT=localhost:4317` in your
local `.env`. The sample environment uses development sampling (`1.0`); set
`OTEL_TRACES_SAMPLER_ARG` to a benchmarked lower value in production.

Prompts, completions, user identity, credentials, authorization headers and
retrieved document bodies must not be added as span attributes. The application
only emits allow-listed operational metadata, and the Collector has a fail-closed
attribute allow-list as a second line of defence. Database analytics, audit logs,
and optional LangSmith tracing remain separate systems.
