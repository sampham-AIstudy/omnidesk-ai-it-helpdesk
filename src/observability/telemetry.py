"""Configure OpenTelemetry SDK and supported automatic instrumentation."""
from __future__ import annotations

import logging

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from src.config import Settings

logger = logging.getLogger(__name__)
_configured = False
_sqlalchemy_instrumented = False


def configure_telemetry(app, settings: Settings) -> None:
    """Install tracing/metrics exporters once; no-op when telemetry is disabled."""
    global _configured
    if _configured or not settings.otel_enabled:
        return

    resource = Resource.create(
        {
            SERVICE_NAME: settings.otel_service_name,
            SERVICE_VERSION: "1.0.0",
            "deployment.environment.name": settings.app_env,
        }
    )
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint, insecure=True)
        )
    )
    trace.set_tracer_provider(tracer_provider)

    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=settings.otel_exporter_otlp_endpoint, insecure=True),
        export_interval_millis=settings.otel_metric_export_interval_ms,
    )
    from opentelemetry import metrics

    metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[metric_reader]))
    FastAPIInstrumentor.instrument_app(app, excluded_urls="health")
    HTTPXClientInstrumentor().instrument()
    _configured = True
    logger.info("OpenTelemetry enabled; exporting to %s", settings.otel_exporter_otlp_endpoint)


def instrument_sqlalchemy(engine) -> None:
    """Add SQL spans once the application's async engine has been created."""
    global _sqlalchemy_instrumented
    if _configured and not _sqlalchemy_instrumented:
        SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)
        _sqlalchemy_instrumented = True
