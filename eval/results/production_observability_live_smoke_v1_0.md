# Production Observability Live Smoke v1.0

## Status: BLOCKED_EXTERNAL_INFRASTRUCTURE

The live smoke was not fabricated. Docker Compose configuration is valid, but the Docker Desktop Linux-engine named pipe was unavailable and no Docker Desktop installation/service could be found in this environment.

| Service | Port | Live health |
| --- | ---: | --- |
| OpenTelemetry Collector | 4317 | UNAVAILABLE |
| Tempo | 3200 | UNAVAILABLE |
| Prometheus | 9090 | UNAVAILABLE |
| Grafana | 3001 | UNAVAILABLE |
| Backend API | 8000 | UNAVAILABLE |

Consequently, no representative request, `X-Trace-ID`, Tempo lookup, Prometheus metric inspection, Grafana dashboard inspection, SSE lifecycle trace, or live exporter-failure request was run.

## Configuration verified

- `docker compose config --quiet`: PASS
- `OTEL_TRACES_SAMPLER`: `parentbased_traceidratio`
- `OTEL_TRACES_SAMPLER_ARG`: `1.0`
- Current host `OTEL_ENABLED`: `false`

## Deterministic regression after smoke attempt

| Suite | Result |
| --- | --- |
| Observability in-memory suite | 7 passed |
| Production E2E | 11 passed |
| `tests/test_eval` | 93 passed |
| Ruff, changed scope | PASS |
| Python compile | PASS |

## Required follow-up when Docker is available

```powershell
docker compose up -d tempo otel-collector prometheus grafana backend
```

Then run the five representative requests, capture `X-Trace-ID` and request ID, query Tempo by each trace ID, inspect Collector/Prometheus metrics, and verify the Grafana dashboard. This report intentionally leaves those acceptance checks **BLOCKED**, not passed.
