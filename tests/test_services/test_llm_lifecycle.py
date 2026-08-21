"""Hermetic unit tests for LLM event-loop lifecycle management and query decomposition fallback."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import HumanMessage

from src.services.llm import (
    clear_llm_cache,
    get_classifier_llm,
    get_fast_classifier_llm,
    get_rag_llm,
    get_runbook_llm,
)
from src.services.query_decomposition_service import decompose_knowledge_query


class LoopBoundDummyClient:
    """Mock client simulating an async transport tied to an event loop."""

    def __init__(self, loop: asyncio.AbstractEventLoop, identifier: str = "default"):
        self._loop = loop
        self._identifier = identifier

    async def ainvoke(self, messages):
        current_loop = asyncio.get_running_loop()
        if self._loop.is_closed() or current_loop is not self._loop:
            raise RuntimeError("Event loop is closed")
        return MagicMock(content='{"is_complex": false, "sub_queries": []}')


def test_cross_loop_reused_client_raises_event_loop_closed():
    """Prove that reusing an async client bound to closed loop A inside loop B raises RuntimeError."""
    # Loop 1
    loop1 = asyncio.new_event_loop()
    asyncio.set_event_loop(loop1)
    client1 = LoopBoundDummyClient(loop1)
    res1 = loop1.run_until_complete(client1.ainvoke([HumanMessage(content="hi")]))
    assert res1.content is not None
    loop1.close()

    # Loop 2: Attempting to call client1 in loop 2 when loop 1 is closed
    loop2 = asyncio.new_event_loop()
    asyncio.set_event_loop(loop2)
    with pytest.raises(RuntimeError, match="Event loop is closed"):
        loop2.run_until_complete(client1.ainvoke([HumanMessage(content="hi")]))
    loop2.close()


def test_llm_factory_provides_distinct_instances_across_loops():
    """Verify that get_fast_classifier_llm returns distinct instances for distinct loops."""
    clear_llm_cache()

    with patch("src.services.llm.get_provider_llm", side_effect=lambda **kw: MagicMock()):
        # Loop 1
        loop1 = asyncio.new_event_loop()
        asyncio.set_event_loop(loop1)
        llm1 = loop1.run_until_complete(asyncio.sleep(0, result=get_fast_classifier_llm()))
        loop1.close()

        # Loop 2
        loop2 = asyncio.new_event_loop()
        asyncio.set_event_loop(loop2)
        llm2 = loop2.run_until_complete(asyncio.sleep(0, result=get_fast_classifier_llm()))
        loop2.close()

        assert llm1 is not llm2, "LLM instance from closed loop 1 was reused in loop 2!"


def test_llm_factory_reuses_instance_within_same_loop():
    """Verify that repeated calls within the SAME event loop reuse the cached instance."""
    clear_llm_cache()

    with patch("src.services.llm.get_provider_llm", side_effect=lambda **kw: MagicMock()):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def _test():
            a1 = get_fast_classifier_llm()
            a2 = get_fast_classifier_llm()
            r1 = get_rag_llm()
            r2 = get_rag_llm()
            return a1, a2, r1, r2

        a1, a2, r1, r2 = loop.run_until_complete(_test())
        loop.close()

        assert a1 is a2, "Same-loop fast classifier instances should be identical"
        assert r1 is r2, "Same-loop rag instances should be identical"
        assert a1 is not r1, "Different model types should have different instances"


def test_clear_llm_cache_invalidates_entries():
    """Verify that clear_llm_cache resets the cache within the same loop."""
    with patch("src.services.llm.get_provider_llm", side_effect=lambda **kw: MagicMock()):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def _test():
            a1 = get_fast_classifier_llm()
            clear_llm_cache()
            a2 = get_fast_classifier_llm()
            return a1, a2

        a1, a2 = loop.run_until_complete(_test())
        loop.close()

        assert a1 is not a2, "clear_llm_cache() should invalidate cached instances"


def test_sync_context_returns_instance_without_crashing():
    """Verify that get_*_llm can be called outside any running asyncio loop."""
    clear_llm_cache()
    with patch("src.services.llm.get_provider_llm", side_effect=lambda **kw: MagicMock()):
        c = get_classifier_llm()
        f = get_fast_classifier_llm()
        r = get_rag_llm()
        b = get_runbook_llm()
        assert c is not None and f is not None and r is not None and b is not None


@pytest.mark.asyncio
async def test_decompose_knowledge_query_graceful_fallback_on_runtime_error():
    """Verify that if the classifier LLM raises RuntimeError (closed loop), it gracefully degrades."""
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(side_effect=RuntimeError("Event loop is closed"))

    with patch("src.services.query_decomposition_service.get_fast_classifier_llm", return_value=mock_llm):
        result = await decompose_knowledge_query("VPN bị lỗi sau khi đổi mật khẩu và làm sao để reset?")
        assert result.is_knowledge_question is True
        assert result.sub_queries == ["VPN bị lỗi sau khi đổi mật khẩu và làm sao để reset?"]


@pytest.mark.asyncio
async def test_decompose_knowledge_query_graceful_fallback_on_timeout():
    """Verify that if the classifier LLM times out or throws ConnectionError, it gracefully degrades."""
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(side_effect=TimeoutError("Request timed out"))

    with patch("src.services.query_decomposition_service.get_fast_classifier_llm", return_value=mock_llm):
        result = await decompose_knowledge_query("Quy trình cài đặt BitLocker như thế nào?")
        assert result.is_knowledge_question is True
        assert result.sub_queries == ["Quy trình cài đặt BitLocker như thế nào?"]
