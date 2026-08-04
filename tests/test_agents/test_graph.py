import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.agents.graph import process_ticket, agent


def _mock_rag_dependencies():
    rag_response = MagicMock()
    rag_response.content = "1. Restart Outlook.\n2. Clear add-in cache.\n3. Contact Software Support if it still fails."

    mock_rag_llm = AsyncMock()
    mock_rag_llm.ainvoke = AsyncMock(return_value=rag_response)

    mock_docs = [
        {
            "content": "Outlook attachment troubleshooting. Restart Outlook and clear add-in cache.",
            "metadata": {
                "title": "Outlook attachment troubleshooting",
                "category": "software",
                "solution": "Restart Outlook and clear add-in cache.",
            },
            "relevance_score": 0.91,
            "distance": 0.09,
        }
    ]
    return mock_rag_llm, mock_docs


@pytest.mark.asyncio
async def test_agent_basic_flow():
    """Test full agent workflow with mocked LLM."""
    mock_response = MagicMock()
    mock_response.content = '{"category": "software", "priority": "medium", "urgency": "medium", "confidence": 0.90, "reasoning": "Software issue", "is_production_impact": false, "suggested_routing_team": "Software Support"}'
    mock_rag_llm, mock_docs = _mock_rag_dependencies()

    with (
        patch("src.agents.nodes.classifier.get_classifier_llm") as mock_llm_fn,
        patch("src.agents.nodes.rag_node.search_similar", return_value=mock_docs),
        patch("src.agents.nodes.rag_node.get_rag_llm", return_value=mock_rag_llm),
    ):
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_llm_fn.return_value = mock_llm

        result = await process_ticket(
            ticket_id=100,
            ticket_number="INC-TEST-999",
            title="Lỗi phần mềm Outlook",
            description="Outlook không mở được file đính kèm",
            submitter_id=1,
            is_production_impact=False,
            submitter_is_vip=False,
        )

    assert result["ticket_number"] == "INC-TEST-999"
    assert result["category"] == "software"
    assert result["confidence_score"] == 0.90
    assert "action_taken" in result


@pytest.mark.asyncio
async def test_agent_state_structure():
    """Test LangGraph input state handling."""
    initial_state = {
        "ticket_id": 101,
        "ticket_number": "INC-TEST-888",
        "title": "Test VPN",
        "description": "Không kết nối được VPN",
        "submitter_id": 1,
        "is_production_impact": False,
        "submitter_is_vip": False,
        "company_unit": "corporate",
        "hitl_required": False,
        "auto_close_eligible": False,
        "error": None,
    }

    mock_response = MagicMock()
    mock_response.content = '{"category": "network", "priority": "high", "urgency": "high", "confidence": 0.95, "reasoning": "VPN issue", "is_production_impact": false, "suggested_routing_team": "Network Team"}'
    mock_rag_llm, mock_docs = _mock_rag_dependencies()

    with (
        patch("src.agents.nodes.classifier.get_classifier_llm") as mock_llm_fn,
        patch("src.agents.nodes.rag_node.search_similar", return_value=mock_docs),
        patch("src.agents.nodes.rag_node.get_rag_llm", return_value=mock_rag_llm),
    ):
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_llm_fn.return_value = mock_llm

        result = await agent.ainvoke(initial_state)

    assert isinstance(result, dict)
    assert result["ticket_number"] == "INC-TEST-888"
    assert result["category"] == "network"
