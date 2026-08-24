"""Boundary tests cho ba dải confidence chuẩn PRD FR-09."""

import pytest

from src.agents.nodes.auto_close_node import _is_auto_close_eligible
from src.agents.nodes.hitl_node import _determine_hitl


def _state(confidence: float) -> dict:
    return {
        "confidence_score": confidence,
        "is_production_impact": False,
        "submitter_is_vip": False,
        "category": "software",
        "priority": "medium",
        "urgency": "medium",
        "suggested_solution": "Khởi động lại ứng dụng.",
        "rag_context": [{"content": "KB"}],
    }


@pytest.mark.parametrize("score", [0.0, 0.59])
def test_confidence_below_sixty_requires_hitl(score: float):
    required, reason = _determine_hitl(_state(score))
    assert required is True
    assert "dưới 60%" in reason
    assert _is_auto_close_eligible(_state(score)) is False


@pytest.mark.parametrize("score", [0.60, 0.74])
def test_warning_band_does_not_force_hitl_or_auto_close(score: float):
    required, _ = _determine_hitl(_state(score))
    assert required is False
    assert _is_auto_close_eligible(_state(score)) is False


@pytest.mark.parametrize("score", [0.75, 1.0])
def test_high_confidence_still_cannot_auto_close(score: float):
    required, _ = _determine_hitl(_state(score))
    assert required is False
    assert _is_auto_close_eligible(_state(score)) is False


def test_safety_rules_remain_independent_from_confidence():
    state = _state(0.99)
    state["is_production_impact"] = True

    required, reason = _determine_hitl(state)

    assert required is True
    assert "production" in reason
    assert _is_auto_close_eligible(state) is False
