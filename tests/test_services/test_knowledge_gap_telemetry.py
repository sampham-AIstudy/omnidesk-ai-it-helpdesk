from __future__ import annotations

import sqlite3

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from scripts.report_knowledge_gaps import build_report_rows
from src.database import Base
from src.services.knowledge_gap_telemetry import normalize_knowledge_topic, record_retrieval_outcome
from src.services.web_research_service import ResearchResult


@pytest_asyncio.fixture
async def telemetry_session_factory(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'telemetry.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    try:
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()


def _internal_doc(score: float = 0.9) -> dict:
    return {
        "relevance_score": score,
        "metadata": {"source": "internal_curated_kb"},
    }


@pytest.mark.asyncio
async def test_gap_01_strong_kb_outcome_is_not_gap(telemetry_session_factory):
    async with telemetry_session_factory() as db:
        event = await record_retrieval_outcome(
            db, surface="workspace", transport="rest", tenant_scope="retail", department_scope="IT",
            query="FortiClient VPN", retrieval_required=True, retrieval_strategy="workspace_hybrid",
            rag_docs=[_internal_doc()], top_score=0.9, insufficient_evidence=False,
        )
        assert event is not None
        assert event.is_knowledge_gap is False
        assert event.no_evidence is False


@pytest.mark.asyncio
async def test_gap_02_and_03_zero_or_low_evidence_are_gap_signals(telemetry_session_factory):
    async with telemetry_session_factory() as db:
        zero = await record_retrieval_outcome(
            db, surface="workspace", transport="rest", tenant_scope="retail", department_scope=None,
            query="DHCP lease", retrieval_required=True, retrieval_strategy="workspace_hybrid",
            rag_docs=[], top_score=0.0, insufficient_evidence=True,
        )
        low = await record_retrieval_outcome(
            db, surface="ticket", transport="rest", tenant_scope="retail", department_scope=None,
            query="DNS proxy", retrieval_required=True, retrieval_strategy="ticket_hybrid_zero_mem",
            rag_docs=[_internal_doc(0.2)], top_score=0.2, insufficient_evidence=False,
        )
        assert zero is not None and zero.no_evidence and zero.is_knowledge_gap
        assert low is not None and not low.no_evidence and low.is_knowledge_gap


@pytest.mark.asyncio
async def test_gap_04_research_and_gap_07_surface_parity(telemetry_session_factory):
    research = ResearchResult(True, "low_rag_confidence", "sanitized", [{}])
    async with telemetry_session_factory() as db:
        workspace = await record_retrieval_outcome(
            db, surface="workspace", transport="sse", tenant_scope="retail", department_scope=None,
            query="VPN connected but internal resource unavailable", retrieval_required=True,
            retrieval_strategy="workspace_hybrid", rag_docs=[], top_score=0.1,
            insufficient_evidence=False, research=research, web_research_provenance_used=True,
        )
        ticket = await record_retrieval_outcome(
            db, surface="ticket", transport="rest", tenant_scope="retail", department_scope=None,
            query="VPN connected but internal resource unavailable", retrieval_required=True,
            retrieval_strategy="ticket_hybrid_zero_mem", rag_docs=[], top_score=0.1,
            insufficient_evidence=False, research=research, web_research_provenance_used=True,
        )
        assert workspace is not None and ticket is not None
        assert workspace.web_research_triggered and ticket.web_research_triggered
        assert workspace.web_research_result_count == ticket.web_research_result_count == 1
        assert workspace.web_research_provenance_used and ticket.web_research_provenance_used


@pytest.mark.asyncio
async def test_gap_05_social_turn_is_not_persisted(telemetry_session_factory):
    async with telemetry_session_factory() as db:
        event = await record_retrieval_outcome(
            db, surface="workspace", transport="rest", tenant_scope="retail", department_scope=None,
            query="hello chat", retrieval_required=False, retrieval_strategy="not_required",
            rag_docs=[], top_score=None, insufficient_evidence=False,
        )
        assert event is None


@pytest.mark.asyncio
async def test_gap_06_raw_pii_is_never_persisted(telemetry_session_factory):
    raw = "VPN for jane.doe@example.com phone +84901234567 password=top-secret"
    async with telemetry_session_factory() as db:
        event = await record_retrieval_outcome(
            db, surface="workspace", transport="rest", tenant_scope="retail", department_scope=None,
            query=raw, retrieval_required=True, retrieval_strategy="workspace_hybrid",
            rag_docs=[], top_score=0.0, insufficient_evidence=True,
        )
        assert event is not None
        assert event.normalized_topic == "general.it_support"
        assert "jane.doe" not in str(event.__dict__)
        assert "top-secret" not in str(event.__dict__)


def test_gap_08_report_keeps_tenants_separate(tmp_path):
    path = tmp_path / "report.db"
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("""
        CREATE TABLE knowledge_gap_events (
            tenant_scope TEXT, normalized_topic TEXT, retrieval_required INTEGER,
            no_evidence INTEGER, insufficient_evidence INTEGER, top_score REAL,
            web_research_triggered INTEGER, web_research_failure_category TEXT,
            hitl_or_escalation INTEGER, is_knowledge_gap INTEGER
        )
    """)
    connection.executemany(
        "INSERT INTO knowledge_gap_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            ("retail", "dns", 1, 1, 1, 0.1, 1, "provider_unavailable", 1, 1),
            ("logistics", "dns", 1, 0, 0, 0.9, 0, None, 0, 0),
        ],
    )
    rows = build_report_rows(connection)
    assert {(row["tenant_scope"], row["query_count"]) for row in rows} == {
        ("retail", 1), ("logistics", 1)
    }
    assert build_report_rows(connection, tenant_scope="retail")[0]["no_evidence_count"] == 1
    connection.close()


def test_gap_09_and_10_port_and_http_403_are_distinct_topics():
    assert normalize_knowledge_topic("Mở cổng 403 TCP trên firewall") == "network.tcp_connectivity"
    assert normalize_knowledge_topic("HTTP 403 Forbidden khi gọi API") == "http.status_403"
