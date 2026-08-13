"""Small, privacy-safe helpers for application-level AI/RAG telemetry."""
from __future__ import annotations

from collections.abc import Awaitable, Callable, Generator, Mapping
from contextlib import contextmanager
from functools import wraps
from time import perf_counter
from typing import Any, ParamSpec, TypeVar

from opentelemetry import metrics, trace
from opentelemetry.trace import Status, StatusCode

_tracer = trace.get_tracer("helpdesk.ai")
_meter = metrics.get_meter("helpdesk.ai")
_operation_duration = _meter.create_histogram(
    "helpdesk.ai.operation.duration",
    unit="ms",
    description="Duration of AI, RAG, and guardrail operations.",
)
_operation_errors = _meter.create_counter(
    "helpdesk.ai.operation.errors",
    unit="{errors}",
    description="Count of failed AI, RAG, and guardrail operations.",
)
_business_events = _meter.create_counter(
    "helpdesk.business.events",
    unit="{events}",
    description="Low-cardinality Help Desk workflow events.",
)
P = ParamSpec("P")
T = TypeVar("T")


def _safe_attributes(attributes: Mapping[str, Any] | None) -> dict[str, str | bool | int | float]:
    """Keep telemetry attributes scalar and never add request content by default."""
    if not attributes:
        return {}
    return {
        key: value
        for key, value in attributes.items()
        if isinstance(value, (str, bool, int, float)) and value is not None
    }


@contextmanager
def operation(name: str, attributes: Mapping[str, Any] | None = None) -> Generator[trace.Span, None, None]:
    """Create a nested span and the paired latency/error metrics.

    Callers must only pass operational metadata (counts, model name, result), not
    prompts, completions, user IDs, emails, tokens, or retrieved document text.
    """
    safe_attributes = _safe_attributes(attributes)
    started = perf_counter()
    with _tracer.start_as_current_span(name) as span:
        span.set_attributes(safe_attributes)
        try:
            yield span
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            _operation_errors.add(1, {"operation": name})
            raise
        finally:
            _operation_duration.record(
                (perf_counter() - started) * 1000,
                {"operation": name},
            )


def record_business_event(event: str) -> None:
    """Record an allow-listed workflow outcome without replacing DB analytics."""
    _business_events.add(1, {"event": event})


def traced_async_operation(name: str) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """Decorate an async pipeline stage with a span and standard metrics."""
    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @wraps(func)
        async def wrapped(*args: P.args, **kwargs: P.kwargs) -> T:
            with operation(name):
                return await func(*args, **kwargs)
        return wrapped
    return decorator


def set_current_attributes(attributes: Mapping[str, Any]) -> None:
    """Attach allow-listed scalar operational attributes to the active span."""
    trace.get_current_span().set_attributes(_safe_attributes(attributes))


def current_trace_id() -> str | None:
    """Return the active W3C trace ID as 32 lowercase hexadecimal characters."""
    context = trace.get_current_span().get_span_context()
    if not context.is_valid:
        return None
    return format(context.trace_id, "032x")
