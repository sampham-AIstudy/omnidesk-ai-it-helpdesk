"""Deterministic contract tests for ticket KB/Zero-Mem acquisition overlap."""
from __future__ import annotations

import asyncio
from time import perf_counter
from types import SimpleNamespace

import pytest

from src.services import ticket_conversation_service as conversation
from src.services import zero_mem_service


def _ticket() -> SimpleNamespace:
    return SimpleNamespace(
        id=42,
        category=None,
        submitter=SimpleNamespace(
            company_unit=SimpleNamespace(value="corporate"), department="IT",
        ),
    )


@pytest.mark.asyncio
async def test_async_01_kb_and_memory_overlap_without_sharing_db_work(monkeypatch):
    starts: dict[str, float] = {}
    boundaries: list[dict[str, float]] = []
    db = object()

    async def kb_turn(queries, retrieve):
        starts["kb"] = perf_counter()
        await asyncio.sleep(0.10)
        return SimpleNamespace(results=[SimpleNamespace(documents=[], outcome="EMPTY")])

    async def memory_lookup(received_db, query, user, *, ticket_id):
        assert received_db is db
        assert ticket_id == 42
        starts["memory"] = perf_counter()
        await asyncio.sleep(0.10)
        return ["authorized-memory"], {"enabled": True, "evidence_final_count": 1}

    monkeypatch.setattr(conversation, "retrieve_turn_with_bounded_retry", kb_turn)
    monkeypatch.setattr(zero_mem_service, "retrieve_episodic_evidence", memory_lookup)
    monkeypatch.setattr(conversation, "record_ticket_stage_latency", lambda *_: None)
    monkeypatch.setattr(conversation, "record_ticket_evidence_overlap", lambda **kwargs: boundaries.append(kwargs))

    started = perf_counter()
    kb_turn_result, memory, _, kb_error, memory_error = await conversation._acquire_ticket_evidence(
        db, query="VPN error", ticket=_ticket(), user=object(),
    )
    elapsed = perf_counter() - started

    assert kb_turn_result is not None
    assert memory == ["authorized-memory"]
    assert kb_error is None and memory_error is None
    assert elapsed < 0.17  # materially below two serial 100-ms boundary calls
    assert abs(starts["kb"] - starts["memory"]) < 0.04
    assert boundaries and boundaries[0]["kb_completed_offset_ms"] > 0


@pytest.mark.asyncio
async def test_async_02_kb_failure_preserves_valid_memory(monkeypatch):
    async def kb_turn(queries, retrieve):
        raise RuntimeError("kb unavailable")

    async def memory_lookup(*args, **kwargs):
        return ["authorized-memory"], {"enabled": True, "evidence_final_count": 1}

    monkeypatch.setattr(conversation, "retrieve_turn_with_bounded_retry", kb_turn)
    monkeypatch.setattr(zero_mem_service, "retrieve_episodic_evidence", memory_lookup)

    kb_turn_result, memory, metrics, kb_error, memory_error = await conversation._acquire_ticket_evidence(
        object(), query="VPN error", ticket=_ticket(), user=object(),
    )

    assert kb_turn_result is None
    assert isinstance(kb_error, RuntimeError)
    assert memory == ["authorized-memory"]
    assert metrics["evidence_final_count"] == 1
    assert memory_error is None


@pytest.mark.asyncio
async def test_async_03_memory_failure_preserves_valid_kb(monkeypatch):
    result = SimpleNamespace(results=[SimpleNamespace(documents=[{"doc_id": "kb-1"}], outcome="ADEQUATE")])

    async def kb_turn(queries, retrieve):
        return result

    async def memory_lookup(*args, **kwargs):
        raise RuntimeError("memory unavailable")

    monkeypatch.setattr(conversation, "retrieve_turn_with_bounded_retry", kb_turn)
    monkeypatch.setattr(zero_mem_service, "retrieve_episodic_evidence", memory_lookup)

    kb_turn_result, memory, metrics, kb_error, memory_error = await conversation._acquire_ticket_evidence(
        object(), query="VPN error", ticket=_ticket(), user=object(),
    )

    assert kb_turn_result is result
    assert memory == []
    assert metrics["evidence_final_count"] == 0
    assert kb_error is None
    assert isinstance(memory_error, RuntimeError)


@pytest.mark.asyncio
async def test_async_04_both_fail_return_empty_evidence_without_llm_work(monkeypatch):
    async def kb_turn(queries, retrieve):
        raise RuntimeError("kb unavailable")

    async def memory_lookup(*args, **kwargs):
        raise RuntimeError("memory unavailable")

    monkeypatch.setattr(conversation, "retrieve_turn_with_bounded_retry", kb_turn)
    monkeypatch.setattr(zero_mem_service, "retrieve_episodic_evidence", memory_lookup)
    llm_factory_called = False

    def llm_factory():
        nonlocal llm_factory_called
        llm_factory_called = True
        raise AssertionError("evidence acquisition must not invoke an LLM")

    monkeypatch.setattr(conversation, "get_rag_llm", llm_factory)
    kb_turn_result, memory, metrics, kb_error, memory_error = await conversation._acquire_ticket_evidence(
        object(), query="VPN error", ticket=_ticket(), user=object(),
    )

    assert kb_turn_result is None and memory == []
    assert metrics["evidence_final_count"] == 0
    assert isinstance(kb_error, RuntimeError)
    assert isinstance(memory_error, RuntimeError)
    assert llm_factory_called is False
