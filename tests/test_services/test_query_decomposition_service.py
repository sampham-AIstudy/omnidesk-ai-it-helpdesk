from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.query_decomposition_service import decompose_knowledge_query


@pytest.mark.asyncio
async def test_action_only_request_is_not_converted_to_retrieval_query():
    with patch("src.services.query_decomposition_service.get_fast_classifier_llm") as llm:
        result = await decompose_knowledge_query("Tạo ticket để reset tài khoản của tôi")

    assert result.is_knowledge_question is False
    assert result.sub_queries == []
    llm.assert_not_called()


@pytest.mark.asyncio
async def test_complex_knowledge_question_preserves_identifiers_exactly():
    response = MagicMock()
    response.content = '{"is_complex": true, "sub_queries": ["Điều kiện VPN cho INC-2026-44", "SLA của INC-2026-44"]}'
    llm = MagicMock()
    llm.ainvoke = AsyncMock(return_value=response)

    with patch("src.services.query_decomposition_service.get_fast_classifier_llm", return_value=llm):
        result = await decompose_knowledge_query("Điều kiện VPN và SLA của INC-2026-44 là gì?")

    assert result.is_knowledge_question is True
    assert result.is_complex is True
    assert result.sub_queries == ["Điều kiện VPN cho INC-2026-44", "SLA của INC-2026-44"]


@pytest.mark.asyncio
async def test_simple_knowledge_question_does_not_spend_an_llm_call():
    with patch("src.services.query_decomposition_service.get_fast_classifier_llm") as llm:
        result = await decompose_knowledge_query("Chính sách VPN là gì")

    assert result.is_complex is False
    assert result.sub_queries == ["Chính sách VPN là gì"]
    llm.assert_not_called()
