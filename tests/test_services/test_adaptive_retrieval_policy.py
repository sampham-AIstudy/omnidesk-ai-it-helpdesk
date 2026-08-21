from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.services.adaptive_retrieval_policy import (
    MAX_INTERNAL_RETRIES_PER_USER_TURN,
    MAX_RETRY_EXPANSION_TERMS,
    AdaptiveRetrievalResult,
    build_bounded_retry_query,
    merge_retry_documents,
    retrieve_turn_with_bounded_retry,
    retrieve_with_bounded_retry,
)


@pytest.fixture(autouse=True)
def retrieval_floor(monkeypatch):
    monkeypatch.setattr(
        "src.services.adaptive_retrieval_policy.get_settings",
        lambda: SimpleNamespace(rag_min_relevance_score=0.55),
    )


def _doc(doc_id: str, score: float = 0.8, *, dense: int | None = 1, lexical: int | None = 1, exact: float = 0.0, topic: float = 1.0, semantic: float = 0.8, canonical: str | None = None):
    return {
        "doc_id": doc_id,
        "relevance_score": score,
        "dense_rank": dense,
        "lexical_rank": lexical,
        "exact_contribution": exact,
        "topic_compatibility": topic,
        "semantic_score": semantic,
        "metadata": {"canonical_source_id": canonical or doc_id},
    }


@pytest.mark.asyncio
async def test_adapt_01_strong_result_uses_one_pass_and_one_anchor():
    result = await retrieve_with_bounded_retry("HTTP 403 Forbidden", lambda _: _async([_doc("http", exact=0.01), _doc("other")]))
    assert result.outcome == "STRONG"
    assert result.retrieval_passes == 1
    assert [doc["doc_id"] for doc in result.documents] == ["http"]


@pytest.mark.asyncio
async def test_adapt_02_adequate_result_has_no_retry():
    result = await retrieve_with_bounded_retry("general IT question", lambda _: _async([_doc("adequate")]))
    assert result.outcome == "ADEQUATE"
    assert result.retry_triggered is False


@pytest.mark.asyncio
async def test_adapt_03_weak_result_retries_once_and_recovers():
    calls: list[str] = []

    async def retrieve(query: str):
        calls.append(query)
        return [_doc("weak", dense=1, lexical=None, semantic=0.2)] if len(calls) == 1 else [_doc("recovered", exact=0.01)]

    result = await retrieve_with_bounded_retry("port timeout", retrieve)
    assert result.outcome == "STRONG"
    assert result.retrieval_passes == 2
    assert result.retry_improved is True
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_adapt_04_empty_retries_once_then_remains_empty():
    calls: list[str] = []

    async def retrieve(query: str):
        calls.append(query)
        return []

    result = await retrieve_with_bounded_retry("unknown product failure", retrieve)
    assert result.outcome == "EMPTY"
    assert result.retrieval_passes == 2
    assert result.retry_reason == "empty_internal_evidence"
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_adapt_05_never_exceeds_one_retry():
    calls = 0

    async def retrieve(_: str):
        nonlocal calls
        calls += 1
        return [_doc("weak", dense=1, lexical=None, semantic=0.2)]

    result = await retrieve_with_bounded_retry("weak", retrieve)
    assert result.retrieval_passes == 2
    assert calls == 2


@pytest.mark.asyncio
async def test_decomposed_all_weak_turn_spends_one_retry_budget_globally():
    calls: list[str] = []

    async def retrieve(query: str):
        calls.append(query)
        return [_doc(f"weak-{len(calls)}", dense=1, lexical=None, semantic=0.2)]

    result = await retrieve_turn_with_bounded_retry(["part one", "part two", "part three"], retrieve)

    assert MAX_INTERNAL_RETRIES_PER_USER_TURN == 1
    assert result.subquery_count == 3
    assert result.initial_search_count == 3
    assert result.retry_search_count == 1
    assert len(calls) == 4
    assert [item.retrieval_passes for item in result.results] == [2, 1, 1]
    assert result.telemetry()["retry_budget_consumed"] == 1


def test_adapt_06_retry_dedup_by_canonical_source():
    merged = merge_retry_documents([_doc("first", 0.6, canonical="source-a")], [_doc("second", 0.9, canonical="source-a")])
    assert [doc["doc_id"] for doc in merged] == ["second"]


def test_adapt_07_tcp_port_never_expands_to_http_status():
    retry = build_bounded_retry_query("ping được nhưng TCP port 403 không vào")
    assert "HTTP authorization" not in retry
    assert "TCP connectivity" in retry
    assert "firewall" not in retry
    assert MAX_RETRY_EXPANSION_TERMS == 2


def test_adapt_08_vpn_post_connection_never_expands_to_authentication():
    retry = build_bounded_retry_query("VPN connected but internal server unreachable")
    assert "routing" in retry
    assert "certificate" not in retry


def test_adapt_13_telemetry_excludes_raw_query():
    telemetry = AdaptiveRetrievalResult([], "EMPTY", 2, True, "empty_internal_evidence", False).telemetry()
    assert all("query" not in key for key in telemetry)
    assert telemetry["final_evidence_count"] == 0


async def _async(value):
    return value
