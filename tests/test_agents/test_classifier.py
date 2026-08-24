"""Tests cho classifier node."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_classify_node_network():
    """Test phân loại ticket mạng."""
    from src.agents.nodes.classifier import classify_node

    state = {
        "ticket_id": 1,
        "ticket_number": "INC-TEST-001",
        "title": "Không kết nối được VPN",
        "description": "Tôi không đăng nhập được VPN FortiClient, báo authentication failed",
        "company_unit": "corporate",
        "is_production_impact": False,
        "submitter_is_vip": False,
    }

    mock_response = MagicMock()
    mock_response.content = '{"category": "network", "priority": "medium", "urgency": "high", "confidence": 0.92, "reasoning": "Ticket về VPN", "is_production_impact": false, "suggested_routing_team": "Network Team"}'

    with patch("src.agents.nodes.classifier.get_classifier_llm") as mock_llm_fn:
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_llm.model = "mistral-large-latest"
        mock_llm_fn.return_value = mock_llm

        result = await classify_node(state)

    assert result["category"] == "network"
    assert result["priority"] == "medium"
    assert result["confidence_score"] >= 0.85
    assert result["error"] is None


@pytest.mark.asyncio
async def test_classify_node_security_hitl():
    """Security ticket phải luôn yêu cầu HITL."""
    from src.agents.nodes.classifier import classify_node
    from src.agents.nodes.hitl_node import hitl_check_node

    state = {
        "ticket_id": 2,
        "ticket_number": "INC-TEST-002",
        "title": "Nghi ngờ máy tính bị virus",
        "description": "Máy tính tự mở nhiều tab lạ, antivirus báo threat",
        "company_unit": "corporate",
        "is_production_impact": False,
        "submitter_is_vip": False,
    }

    mock_response = MagicMock()
    mock_response.content = '{"category": "security", "priority": "high", "urgency": "high", "confidence": 0.95, "reasoning": "Security incident", "is_production_impact": false, "suggested_routing_team": "IT Security Team"}'

    with patch("src.agents.nodes.classifier.get_classifier_llm") as mock_llm_fn:
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_llm.model = "mistral-large-latest"
        mock_llm_fn.return_value = mock_llm

        classified = await classify_node(state)

    # Security category luôn HITL
    hitl_state = await hitl_check_node(classified)
    assert hitl_state["hitl_required"] is True
    assert "security" in hitl_state["hitl_reason"].lower() or "nhạy cảm" in hitl_state["hitl_reason"].lower() or "phê duyệt" in hitl_state["hitl_reason"].lower()


@pytest.mark.asyncio
async def test_classify_node_vip_upgrades_priority():
    """VIP submitter phải nâng priority lên high."""
    from src.agents.nodes.classifier import classify_node

    state = {
        "ticket_id": 3,
        "ticket_number": "INC-TEST-003",
        "title": "Máy tính chạy chậm",
        "description": "Máy tính của tôi hơi chậm",
        "company_unit": "corporate",
        "is_production_impact": False,
        "submitter_is_vip": True,  # VIP!
    }

    mock_response = MagicMock()
    mock_response.content = '{"category": "hardware", "priority": "low", "urgency": "low", "confidence": 0.88, "reasoning": "Performance issue", "is_production_impact": false, "suggested_routing_team": "Hardware Team"}'

    with patch("src.agents.nodes.classifier.get_classifier_llm") as mock_llm_fn:
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_llm.model = "mistral-large-latest"
        mock_llm_fn.return_value = mock_llm

        result = await classify_node(state)

    # VIP → priority phải được upgrade lên high
    assert result["priority"] in ("high", "critical")


@pytest.mark.asyncio
async def test_ai_never_auto_closes_high_confidence_ticket():
    """A high-confidence AI answer still requires a user or technician to close."""
    from src.agents.nodes.auto_close_node import auto_close_check_node

    state = {
        "confidence_score": 0.92,
        "is_production_impact": False,
        "submitter_is_vip": False,
        "category": "software",
        "priority": "low",
        "urgency": "low",
        "suggested_solution": "Restart Office và thử lại",
        "rag_context": [{"content": "...", "relevance_score": 0.85}],
        "ticket_number": "INC-TEST-004",
    }

    result = await auto_close_check_node(state)
    assert result["auto_close_eligible"] is False


@pytest.mark.asyncio
async def test_auto_close_blocked_for_security():
    """Security ticket không được auto-close dù confidence cao."""
    from src.agents.nodes.auto_close_node import auto_close_check_node

    state = {
        "confidence_score": 0.95,
        "is_production_impact": False,
        "submitter_is_vip": False,
        "category": "security",
        "priority": "high",
        "urgency": "high",
        "suggested_solution": "Ngắt kết nối mạng ngay",
        "rag_context": [{"content": "...", "relevance_score": 0.9}],
        "ticket_number": "INC-TEST-005",
    }

    result = await auto_close_check_node(state)
    assert result["auto_close_eligible"] is False
