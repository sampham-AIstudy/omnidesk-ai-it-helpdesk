from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.graph import agent, process_ticket


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


@pytest.mark.asyncio
async def test_vague_ticket_short_circuits_before_llm_and_rag():
    """A safe but non-diagnosable ticket asks for details without API spend."""
    with patch("src.agents.nodes.classifier.get_classifier_llm") as classifier, patch(
        "src.agents.nodes.rag_node.search_similar"
    ) as retrieval:
        result = await process_ticket(
            ticket_id=102,
            ticket_number="INC-TEST-CLARIFY",
            title="Tôi hỏng",
            description="Không biết lỗi gì",
            submitter_id=1,
        )

    assert result["needs_clarification"] is True
    assert result["action_taken"] == "ask_clarification"
    assert result["suggested_solution"]
    classifier.assert_not_called()
    retrieval.assert_not_called()


@pytest.mark.asyncio
async def test_low_relevance_rag_does_not_call_synthesis_model():
    """Weak retrieval must become a safe handoff, not an invented answer."""
    from src.agents.nodes.rag_node import rag_node

    weak_docs = [{"content": "Unrelated document", "metadata": {}, "relevance_score": 0.20}]
    with patch("src.agents.nodes.rag_node.search_similar", return_value=weak_docs), patch(
        "src.agents.nodes.rag_node.get_rag_llm"
    ) as llm_factory:
        result = await rag_node({"ticket_number": "INC-TEST-WEAK-RAG", "title": "VPN", "description": "Cannot connect", "category": "network"})

    assert result["rag_context"] == []
    assert result["groundedness_score"] == 0.20
    llm_factory.assert_not_called()


def test_incident_without_matching_kb_is_not_a_generic_insufficiency_refusal():
    from src.agents.nodes.rag_node import _safe_initial_triage

    reply = _safe_initial_triage(
        "Màn hình laptop đen",
        "Tôi vừa đấm vào màn hình, giờ thiết bị không hiển thị.",
    )

    assert "sự cố cần xử lý" in reply
    assert "không cần nhắc lại" in reply


@pytest.mark.asyncio
async def test_missing_kb_guidance_hands_off_to_a_technician():
    from src.agents.nodes.hitl_node import hitl_check_node

    result = await hitl_check_node({
        "ticket_number": "INC-TEST-NO-KB",
        "category": "network",
        "priority": "medium",
        "urgency": "medium",
        "confidence_score": 0.95,
        "is_production_impact": False,
        "submitter_is_vip": False,
        "rag_context": [],
    })

    assert result["hitl_required"] is False
    assert result["action_taken"] == "human_handoff"


@pytest.mark.asyncio
async def test_ai_admitting_missing_kb_guidance_forces_handoff():
    from src.agents.nodes.rag_node import rag_node

    response = MagicMock()
    response.content = "Knowledge Base không có thông tin phù hợp với sự cố này."
    llm = AsyncMock()
    llm.ainvoke = AsyncMock(return_value=response)
    docs = [{"content": "Generic VPN guide", "metadata": {"title": "VPN guide"}, "relevance_score": 0.95}]

    with patch("src.agents.nodes.rag_node.search_similar", return_value=docs), patch(
        "src.agents.nodes.rag_node.get_rag_llm", return_value=llm
    ):
        result = await rag_node({"ticket_number": "INC-TEST-DECLINED-KB", "title": "Màn hình đen", "description": "Máy bật lên rồi màn hình đen", "category": "network"})

    assert result["rag_context"] == []
    assert result["groundedness_score"] == 0.0
