from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src.guardrails.input_guardrails import needs_it_clarification
from src.services.web_research_service import ResearchResult


def test_retrieved_sources_are_not_rendered_without_a_final_citation() -> None:
    from src.api.chat import _sources_used_by_reply

    documents = [
        {
            "doc_id": "KB-42",
            "content": "VPN requires MFA.",
            "metadata": {"title": "VPN access"},
        }
    ]

    reply, sources = _sources_used_by_reply("VPN requires MFA.", documents, [])
    assert reply == "VPN requires MFA."
    assert sources == []

    _, sources = _sources_used_by_reply("VPN requires MFA. [KB-42]", documents, [])
    assert [source.source_id for source in sources] == ["KB-42"]


class Chunk:
    def __init__(self, content: str) -> None:
        self.content = content


class StreamingLLM:
    async def astream(self, _: str):
        yield Chunk("**Kiem tra** ")
        yield Chunk("WiFi truoc [1].")


@pytest.mark.asyncio
async def test_chat_streams_tokens_and_final_plain_text(client, auth_employee):
    with (
        patch("src.api.chat.search_similar_async", AsyncMock(return_value=[])),
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
    assert "event: token" in response.text
    assert "event: done" in response.text
    assert "**" not in response.text


def test_vague_report_requires_context_but_network_report_does_not():
    assert needs_it_clarification("tôi hỏng nhưng tôi bị ngu không biết là lỗi gì") is True
    assert needs_it_clarification("mất kết nối mạng ở tầng 3") is False


def test_authorized_ticket_context_prevents_reasking_already_provided_details():
    assert needs_it_clarification(
        "Tôi hỏng nhưng không biết là lỗi gì.",
        conversation_context="Laptop vừa bị đấm vào màn hình và màn hình đen xì.",
    ) is False


@pytest.mark.asyncio
async def test_vague_report_does_not_call_rag_or_web_search(client, auth_employee):
    rag_search = AsyncMock()
    with (
        patch("src.api.chat.search_similar_async", rag_search),
        patch("src.api.chat.maybe_research_web", AsyncMock()),
    ):
        response = await client.post(
            "/api/v1/chat/stream",
            json={"message": "tôi hỏng nhưng tôi bị ngu không biết là lỗi gì"},
            headers={"Authorization": f"Bearer {auth_employee}"},
        )

    assert response.status_code == 200
    assert "event: done" in response.text
    assert "bạn không cần biết tên lỗi" in response.text.lower()
    rag_search.assert_not_awaited()


@pytest.mark.asyncio
async def test_greeting_does_not_call_rag_web_or_memory(client, auth_employee):
    rag_search = AsyncMock()
    memory_search = AsyncMock()
    with (
        patch("src.api.chat.search_similar_async", rag_search),
        patch("src.services.zero_mem_service.retrieve_episodic_evidence", memory_search),
        patch("src.api.chat.maybe_research_web", AsyncMock()),
    ):
        response = await client.post(
            "/api/v1/chat/stream",
            json={"message": "Chào bạn nhé"},
            headers={"Authorization": f"Bearer {auth_employee}"},
        )

    assert response.status_code == 200
    assert "event: done" in response.text
    assert '"sources": []' in response.text
    assert '"classification_confidence": 1.0' in response.text
    assert '"retrieval_confidence": null' in response.text
    assert '"answer_groundedness": 1.0' in response.text
    assert '"answerability": "direct"' in response.text
    rag_search.assert_not_awaited()
    memory_search.assert_not_awaited()
