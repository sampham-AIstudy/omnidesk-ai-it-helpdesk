"""Privacy-safe custom spans and bounded operational metrics."""
from __future__ import annotations

from collections.abc import Awaitable, Callable, Generator, Mapping
from contextlib import contextmanager
from functools import wraps
from time import perf_counter
from typing import Any, ParamSpec, TypeVar

from opentelemetry import metrics, trace
from opentelemetry.trace import Status, StatusCode

_tracer = trace.get_tracer("helpdesk.application")
_meter = metrics.get_meter("helpdesk.application")
_operation_duration = _meter.create_histogram("helpdesk.operation.duration", unit="ms", description="Bounded operation latency.")
_operation_errors = _meter.create_counter("helpdesk.operation.errors", unit="{errors}", description="Bounded operation errors.")
_business_events = _meter.create_counter("helpdesk.workflow.events", unit="{events}", description="Workflow outcomes.")
_http_requests = _meter.create_counter("helpdesk.http.server.requests", unit="{requests}", description="HTTP requests by route and status.")
_http_duration = _meter.create_histogram("helpdesk.http.server.duration", unit="ms", description="HTTP duration by route and status.")
_ai_requests = _meter.create_counter("helpdesk.ai.requests", unit="{requests}", description="Generation requests by model.")
_retrieval_requests = _meter.create_counter("helpdesk.ai.retrieval.requests", unit="{requests}", description="Retrieval stage invocations.")
_memory_requests = _meter.create_counter("helpdesk.ai.memory.requests", unit="{requests}", description="Memory stage invocations.")
_web_requests = _meter.create_counter("helpdesk.ai.web.requests", unit="{requests}", description="Web research stage invocations.")
_generation_errors = _meter.create_counter("helpdesk.ai.generation.errors", unit="{errors}", description="Generation-stage failures.")
_tool_calls = _meter.create_counter("helpdesk.ai.tool.calls", unit="{calls}", description="Trusted tool/action render calls.")
_tool_failures = _meter.create_counter("helpdesk.ai.tool.failures", unit="{failures}", description="Trusted tool/action failures.")
_ticket_stage_duration = _meter.create_histogram(
    "helpdesk.ticket.stage.duration", unit="ms",
    description="Bounded ticket-turn stage latency without request content.",
)
P = ParamSpec("P")
T = TypeVar("T")

_ALLOWED_KEYS = {
    "ai.route", "ai.retrieval.required", "ai.retrieval.used", "ai.memory.used", "ai.web.used",
    "ai.tool.name", "ai.tool.success", "ai.provider", "ai.model", "ai.stage", "ai.streaming",
    "helpdesk.guardrail.result", "helpdesk.chat.route", "helpdesk.chat.retrieval_required",
    "helpdesk.chat.retrieval_decision", "helpdesk.chat.memory_required", "helpdesk.rag.documents_retrieved",
    "helpdesk.rag.top_score", "helpdesk.rag.query_decomposed", "helpdesk.rag.sub_query_count",
    "helpdesk.memory.enabled", "helpdesk.memory.route", "helpdesk.memory.ticket_context_authorized",
    "helpdesk.gap.detected", "helpdesk.gap.topic",
    "helpdesk.expansion.anchor_count", "helpdesk.expansion.neighbor_count",
    "helpdesk.expansion.parent_count", "helpdesk.expansion.dropped_neighbor_count",
    "helpdesk.expansion.token_cost", "helpdesk.expansion.used",
    "gen_ai.request.model", "gen_ai.response.model", "gen_ai.usage.input_tokens", "gen_ai.usage.output_tokens",
    "helpdesk.ticket.context_resolution_ms", "helpdesk.ticket.routing_ms",
    "helpdesk.ticket.kb_retrieval_ms", "helpdesk.ticket.memory_retrieval_ms",
    "helpdesk.ticket.evidence_acquisition_wall_ms", "helpdesk.ticket.web_research_ms",
    "helpdesk.ticket.llm_generation_ms", "helpdesk.ticket.citation_validation_ms",
    "helpdesk.ticket.total_request_ms", "helpdesk.ticket.model_first_token_ms",
    "helpdesk.ticket.client_first_token_ms", "helpdesk.ticket.time_to_first_token_ms",
    "helpdesk.ticket.kb_started_offset_ms",
    "helpdesk.ticket.kb_completed_offset_ms", "helpdesk.ticket.memory_started_offset_ms",
    "helpdesk.ticket.memory_completed_offset_ms",
}
_SENSITIVE_MARKERS = ("password", "secret", "token", "authorization", "cookie", "email", "prompt", "message", "content", "document", "query")


def _safe_attributes(attributes: Mapping[str, Any] | None) -> dict[str, str | bool | int | float]:
    """Allow only bounded, scalar operational metadata without user content."""
    if not attributes:
        return {}
    safe: dict[str, str | bool | int | float] = {}
    for key, value in attributes.items():
        if key not in _ALLOWED_KEYS or any(marker in key.lower() for marker in _SENSITIVE_MARKERS):
            continue
        if not isinstance(value, (str, bool, int, float)) or value is None:
            continue
        if isinstance(value, str) and len(value) > 128:
            continue
        safe[key] = value
    return safe


@contextmanager
def operation(name: str, attributes: Mapping[str, Any] | None = None) -> Generator[trace.Span, None, None]:
    """Create one meaningful operational span plus bounded latency/error metrics."""
    safe_attributes = _safe_attributes(attributes)
    started = perf_counter()
    if name == "ai.generation":
        _ai_requests.add(1, {"ai.model": str(safe_attributes.get("gen_ai.request.model", "unknown"))})
    elif name == "ai.retrieval":
        _retrieval_requests.add(1)
    elif name == "ai.memory":
        _memory_requests.add(1)
    elif name == "ai.web":
        _web_requests.add(1)
    with _tracer.start_as_current_span(name) as span:
        span.set_attributes(safe_attributes)
        try:
            yield span
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, type(exc).__name__))
            _operation_errors.add(1, {"operation": name})
            if name == "ai.generation":
                _generation_errors.add(1)
            raise
        finally:
            _operation_duration.record((perf_counter() - started) * 1000, {"operation": name})


def record_business_event(event: str) -> None:
    """Record a low-cardinality workflow outcome."""
    _business_events.add(1, {"event": event})


def record_http_request(route: str, method: str, status_code: int, duration_ms: float) -> None:
    """Record API metrics against route templates, never literal IDs or query text."""
    attributes: dict[str, str | int | float | bool] = {"http.route": route, "http.request.method": method, "http.response.status_code": status_code}
    _http_requests.add(1, attributes)
    _http_duration.record(duration_ms, attributes)


def record_tool_result(tool_name: str, success: bool) -> None:
    """Record tool state only; resource IDs and error bodies are deliberately excluded."""
    attributes: dict[str, str | int | float | bool] = {"ai.tool.name": tool_name, "ai.tool.success": success}
    _tool_calls.add(1, attributes)
    if not success:
        _tool_failures.add(1, {"ai.tool.name": tool_name})


_TICKET_TIMING_STAGES = frozenset({
    "context_resolution", "routing", "kb_retrieval", "memory_retrieval",
    "evidence_acquisition_wall", "web_research", "llm_generation",
    "citation_validation", "total_request", "model_first_token", "client_first_token",
    "time_to_first_token",
})


def record_ticket_stage_latency(stage: str, duration_ms: float) -> None:
    """Record one bounded ticket-turn timing without attaching user data.

    ``stage`` is allow-listed so callers cannot turn telemetry labels into a
    content channel.  The same value is placed on the current trace span for
    per-turn diagnosis and emitted as a low-cardinality histogram datapoint.
    """
    if stage not in _TICKET_TIMING_STAGES or duration_ms < 0:
        return
    bounded = round(min(float(duration_ms), 3_600_000.0), 2)
    _ticket_stage_duration.record(bounded, {"ai.stage": stage})
    set_current_attributes({f"helpdesk.ticket.{stage}_ms": bounded})


def record_ticket_evidence_overlap(
    *, kb_started_offset_ms: float, kb_completed_offset_ms: float,
    memory_started_offset_ms: float, memory_completed_offset_ms: float,
) -> None:
    """Expose relative evidence-worker boundaries, never wall-clock timestamps."""
    values = {
        "helpdesk.ticket.kb_started_offset_ms": kb_started_offset_ms,
        "helpdesk.ticket.kb_completed_offset_ms": kb_completed_offset_ms,
        "helpdesk.ticket.memory_started_offset_ms": memory_started_offset_ms,
        "helpdesk.ticket.memory_completed_offset_ms": memory_completed_offset_ms,
    }
    set_current_attributes({key: round(max(0.0, value), 2) for key, value in values.items()})


def traced_async_operation(name: str) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @wraps(func)
        async def wrapped(*args: P.args, **kwargs: P.kwargs) -> T:
            with operation(name):
                return await func(*args, **kwargs)
        return wrapped
    return decorator


def set_current_attributes(attributes: Mapping[str, Any]) -> None:
    trace.get_current_span().set_attributes(_safe_attributes(attributes))


def current_trace_id() -> str | None:
    context = trace.get_current_span().get_span_context()
    return format(context.trace_id, "032x") if context.is_valid else None
