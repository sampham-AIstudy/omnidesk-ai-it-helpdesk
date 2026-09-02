"""Boundary tests cho ba dải confidence chuẩn PRD FR-09."""

import pytest

from src.agents.nodes.policy_engine import evaluate_policy


def _state(confidence: float | None) -> dict:
    return {
        "confidence_score": confidence,
        "is_production_impact": False,
        "submitter_is_vip": False,
        "category": "software",
        "priority": "medium",
        "urgency": "medium",
        "title": "Cần hỗ trợ phần mềm",
        "description": "Khởi động lại ứng dụng.",
        "rag_context": [{"content": "KB"}],
    }


@pytest.mark.parametrize("score", [0.0, 0.44])
def test_confidence_below_45_escalates(score: float):
    res = evaluate_policy(_state(score), risk_score=0.3)
    assert res["decision"] == "ESCALATE"
    assert res["action_type"] == "HUMAN_HANDOFF"


@pytest.mark.parametrize("score", [0.45, 0.84])
def test_normal_band_auto_proceeds_when_low_risk(score: float):
    res = evaluate_policy(_state(score), risk_score=0.3)
    assert res["decision"] == "AUTO_PROCEED"


@pytest.mark.parametrize("score", [0.85, 1.0])
def test_high_confidence_auto_proceeds(score: float):
    res = evaluate_policy(_state(score), risk_score=0.3)
    assert res["decision"] == "AUTO_PROCEED"
    assert res["target_status"] == "resolved"


def test_safety_rules_remain_independent_from_confidence():
    state = _state(0.99)
    state["is_production_impact"] = True

    res = evaluate_policy(state, risk_score=0.9)
    assert res["decision"] == "ESCALATE"
    assert res["action_type"] == "HUMAN_HANDOFF"
    assert "Production" in res["reason"]

