"""Deterministic coverage for production observability boundaries.

These tests intentionally use the SDK in-memory exporter.  They never require
Collector, Tempo, Prometheus, or an external LLM provider.
"""
from __future__ import annotations

import logging
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import text

from src.config import get_settings
from src.database import AsyncSessionLocal, engine
from src.main import app
from src.observability.telemetry import (
    TraceCorrelationFilter,
    configure_telemetry,
    install_in_memory_span_exporter,
    instrument_sqlalchemy,
    shutdown_telemetry,
)
from src.observability.tracing import operation
from src.services.action_grounding import ActionResult, action_state_reply
from src.services.web_research_service import ResearchResult


@pytest.fixture
def span_exporter():
    exporter = install_in_memory_span_exporter()
    yield exporter
    exporter.clear()


def _span_names(exporter) -> set[str]:
    return {span.name for span in exporter.get_finished_spans()}


@pytest.mark.asyncio
async def test_http_request_has_w3c_trace_and_matching_safe_header(client, span_exporter):
    response = await client.get("/")

    assert response.status_code == 200
    trace_id = response.headers["X-Trace-ID"]
    assert len(trace_id) == 32
    assert int(trace_id, 16) >= 0
    assert any(format(span.context.trace_id, "032x") == trace_id for span in span_exporter.get_finished_spans())


@pytest.mark.asyncio
async def test_direct_stream_has_route_span_but_no_fake_retrieval_span(client, auth_employee, span_exporter):
    with (
        patch("src.api.chat.search_similar_async", AsyncMock()),
        patch("src.services.zero_mem_service.retrieve_episodic_evidence", AsyncMock()),
        patch("src.api.chat.maybe_research_web", AsyncMock()),
    ):
        response = await client.post(
            "/api/v1/chat/stream",
            json={"message": "Chào bạn nhé"},
            headers={"Authorization": f"Bearer {auth_employee}"},
        )

    assert response.status_code == 200
    assert "ai.route" in _span_names(span_exporter)
    assert "ai.retrieval" not in _span_names(span_exporter)


@pytest.mark.asyncio
async def test_retrieval_route_creates_retrieval_and_memory_spans(client, auth_employee, span_exporter):
    class StreamingLLM:
        async def astream(self, _):
            return
            yield  # pragma: no cover - establishes async-generator shape

    with (
        patch("src.api.chat.search_similar_async", AsyncMock(return_value=[])),
        patch("src.services.zero_mem_service.retrieve_episodic_evidence", AsyncMock(return_value=([], {"route": "none"}))),
        patch("src.api.chat.maybe_research_web", AsyncMock(return_value=ResearchResult(False, "internal_kb_sufficient", None, []))),
        patch("src.api.chat.get_rag_llm", return_value=StreamingLLM()),
        patch("src.services.ai_logger.log_web_app_ai_event"),
    ):
        response = await client.post(
            "/api/v1/chat/stream",
            json={"message": "Lỗi WiFi cần hỗ trợ"},
            headers={"Authorization": f"Bearer {auth_employee}"},
        )

    assert response.status_code == 200
    names = _span_names(span_exporter)
    assert {"ai.route", "ai.retrieval", "ai.memory", "ai.generation"} <= names


@pytest.mark.asyncio
async def test_db_span_is_child_of_application_operation(span_exporter):
    instrument_sqlalchemy(engine)
    with operation("workflow.db_check") as parent:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))

    spans = span_exporter.get_finished_spans()
    assert any(span.parent and span.parent.span_id == parent.get_span_context().span_id for span in spans)


def test_action_tool_span_does_not_export_internal_error_or_resource_id(span_exporter):
    reply = action_state_reply(ActionResult(success=False, error_code="DATABASE_TIMEOUT"))

    assert reply == "Thao tác chưa hoàn tất."
    tool_span = next(span for span in span_exporter.get_finished_spans() if span.name == "ai.tool")
    assert tool_span.attributes["ai.tool.name"] == "action_state_renderer"
    assert "DATABASE_TIMEOUT" not in str(tool_span.attributes)
    assert "resource_id" not in tool_span.attributes


def test_attribute_and_log_redaction_are_fail_closed():
    with operation("ai.generation", {"ai.model": "safe-model", "message": "Bearer secret-value"}) as span:
        pass
    assert span.attributes == {"ai.model": "safe-model"}

    record = logging.LogRecord("test", logging.INFO, __file__, 1, "token=secret", (), None)
    assert TraceCorrelationFilter().filter(record) is True
    assert record.getMessage() == "[redacted sensitive log message]"


def test_telemetry_setup_is_idempotent_and_export_failure_is_nonfatal(span_exporter):
    instrumented_before = set(__import__("src.observability.telemetry", fromlist=["_instrumented_apps"])._instrumented_apps)
    configure_telemetry(app, get_settings())
    configure_telemetry(app, get_settings())
    instrumented_after = set(__import__("src.observability.telemetry", fromlist=["_instrumented_apps"])._instrumented_apps)

    assert instrumented_after == instrumented_before
    shutdown_telemetry()  # No Collector is configured for tests; this must not raise.
