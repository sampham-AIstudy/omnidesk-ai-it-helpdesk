"""Central, fail-safe OpenTelemetry setup for the Help Desk application.

The application deliberately exports only operational metadata.  Exporters are
optional: tracing still has a valid SDK provider locally so request correlation
does not depend on a Collector being reachable.
"""
from __future__ import annotations

import json
import logging
import re
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.sdk.trace.sampling import ALWAYS_OFF, ALWAYS_ON, ParentBased, TraceIdRatioBased

from src.config import Settings

logger = logging.getLogger(__name__)
_sdk_configured = False
_httpx_instrumented = False
_sqlalchemy_instrumented = False
_instrumented_apps: set[int] = set()
_request_id: ContextVar[str | None] = ContextVar("helpdesk_request_id", default=None)
_sensitive_value = re.compile(r"(?i)(bearer\s+|api[_-]?key|password|secret|token|jwt|cookie)")


def _sampler(settings: Settings):
    if settings.otel_traces_sampler == "always_off":
        return ALWAYS_OFF
    if settings.otel_traces_sampler == "always_on":
        return ALWAYS_ON
    return ParentBased(TraceIdRatioBased(settings.otel_traces_sampler_arg))


def _resource(settings: Settings) -> Resource:
    attributes: dict[str, str] = {
        SERVICE_NAME: settings.otel_service_name,
        SERVICE_VERSION: settings.otel_service_version,
        "deployment.environment.name": settings.app_env,
    }
    if settings.otel_service_namespace:
        attributes["service.namespace"] = settings.otel_service_namespace
    if settings.otel_service_instance_id:
        attributes["service.instance.id"] = settings.otel_service_instance_id
    return Resource.create(attributes)


def _configure_sdk(settings: Settings) -> None:
    """Configure a local SDK once, attaching OTLP only when explicitly enabled."""
    global _sdk_configured
    if _sdk_configured:
        return

    resource = _resource(settings)
    tracer_provider = TracerProvider(resource=resource, sampler=_sampler(settings))
    metric_readers = []
    if settings.otel_enabled:
        try:
            tracer_provider.add_span_processor(
                BatchSpanProcessor(
                    OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint, insecure=True)
                )
            )
            metric_readers.append(
                PeriodicExportingMetricReader(
                    OTLPMetricExporter(endpoint=settings.otel_exporter_otlp_endpoint, insecure=True),
                    export_interval_millis=settings.otel_metric_export_interval_ms,
                )
            )
        except Exception:  # Exporter setup is never allowed to break startup.
            logger.exception("Telemetry exporter setup failed; retaining local SDK only")

    try:
        trace.set_tracer_provider(tracer_provider)
        metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=metric_readers))
    except Exception:  # Another host/test harness may have installed global providers.
        logger.debug("OpenTelemetry global provider already configured", exc_info=True)
    _sdk_configured = True


class TraceCorrelationFilter(logging.Filter):
    """Attach correlation IDs and redact accidental credentials in log messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        context = trace.get_current_span().get_span_context()
        record.trace_id = format(context.trace_id, "032x") if context.is_valid else None
        record.span_id = format(context.span_id, "016x") if context.is_valid else None
        record.request_id = _request_id.get()
        message = record.getMessage()
        if _sensitive_value.search(message):
            record.msg, record.args = "[redacted sensitive log message]", ()
        return True


class StructuredJsonFormatter(logging.Formatter):
    """Compact structured log records; request content is never added as a field."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
            "trace_id": getattr(record, "trace_id", None),
            "span_id": getattr(record, "span_id", None),
            "request_id": getattr(record, "request_id", None),
        }
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_structured_logging() -> None:
    """Install one correlation filter/formatter without touching logger call sites."""
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(level=logging.INFO)
    for handler in root.handlers:
        if not any(isinstance(item, TraceCorrelationFilter) for item in handler.filters):
            handler.addFilter(TraceCorrelationFilter())
        if not isinstance(handler.formatter, StructuredJsonFormatter):
            handler.setFormatter(StructuredJsonFormatter())


def configure_telemetry(app: Any, settings: Settings) -> None:
    """Configure providers and supported auto-instrumentors exactly once per process/app."""
    global _httpx_instrumented
    _configure_sdk(settings)
    configure_structured_logging()
    app_id = id(app)
    if app_id not in _instrumented_apps:
        FastAPIInstrumentor.instrument_app(app, excluded_urls="health")
        _instrumented_apps.add(app_id)
    if not _httpx_instrumented:
        HTTPXClientInstrumentor().instrument()
        _httpx_instrumented = True
    if settings.otel_enabled:
        logger.info("OpenTelemetry OTLP export enabled")
    else:
        logger.info("OpenTelemetry local correlation enabled; OTLP export disabled")


def instrument_sqlalchemy(engine: Any) -> None:
    """Instrument the real SQLAlchemy engine once, without SQL parameter capture."""
    global _sqlalchemy_instrumented
    if _sqlalchemy_instrumented:
        return
    try:
        SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine, enable_commenter=False)
        _sqlalchemy_instrumented = True
    except Exception:
        logger.exception("SQLAlchemy telemetry instrumentation unavailable; database remains operational")


def set_request_id(request_id: str) -> object:
    return _request_id.set(request_id)


def reset_request_id(token: object) -> None:
    _request_id.reset(token)  # type: ignore[arg-type]


def install_in_memory_span_exporter() -> InMemorySpanExporter:
    """Attach a test-only exporter to the active SDK without network dependencies."""
    provider = trace.get_tracer_provider()
    if not isinstance(provider, TracerProvider):
        raise RuntimeError("An SDK TracerProvider is required for telemetry tests")
    exporter = InMemorySpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return exporter


def shutdown_telemetry() -> None:
    """Best-effort flush; never raise during application shutdown."""
    try:
        trace.get_tracer_provider().force_flush()  # type: ignore[attr-defined]
    except Exception:
        logger.debug("Telemetry trace flush failed", exc_info=True)
    try:
        metrics.get_meter_provider().force_flush()  # type: ignore[attr-defined]
    except Exception:
        logger.debug("Telemetry metric flush failed", exc_info=True)
