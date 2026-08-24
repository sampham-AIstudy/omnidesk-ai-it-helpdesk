"""
Deterministic Safety Policy Engine.
Executes deterministic business & security rules AFTER AI Risk Score calculation.
Hard policy rules have absolute power to OVERRIDE LLM Risk Scores.
"""
from __future__ import annotations

import logging
from typing import Any

from src.agents.state import TicketAgentState

logger = logging.getLogger(__name__)


def evaluate_policy(state: TicketAgentState, risk_score: float) -> dict[str, Any]:
    """
    Deterministic Safety Policy Engine Matrix:
    1. Security Category -> REQUIRE_HITL
    2. Sensitive Actions (Password Reset Admin / Permission / DB) -> REQUIRE_HITL
    3. Production System Impact -> REQUIRE_HITL
    4. Groundedness < 0.50 -> ESCALATE (HUMAN_HANDOFF)
    5. Groundedness 0.50 - 0.75 -> NEEDS_CLARIFICATION
    6. Overall Confidence < 0.60 -> ESCALATE
    7. Risk Score >= 0.65 -> REQUIRE_HITL
    8. Otherwise -> AUTO_PROCEED
    """
    category = state.get("category", "other")
    is_production = state.get("is_production_impact", False)
    groundedness_val = state.get("groundedness_score")
    groundedness: float = float(groundedness_val) if groundedness_val is not None else 1.0
    confidence_val = state.get("confidence_score")
    confidence: float = float(confidence_val) if confidence_val is not None else 1.0
    description = (state.get("description", "") + " " + state.get("title", "")).lower()

    # Rule 1: Security Category or Security Incident
    if category == "security":
        return {
            "decision": "REQUIRE_HITL",
            "action_type": "EXECUTE_HIGH_RISK",
            "target_status": "pending_hitl",
            "policy_triggered": "POLICY_SECURITY_CATEGORY_MANDATORY_HITL",
            "reason": "Ticket thuộc danh mục Security bắt buộc phê duyệt bởi Quản lý",
        }

    # Rule 2: Sensitive Actions (Reset Password Admin, Sharepoint Permissions, Database Drop)
    sensitive_keywords = ["reset password", "admin", "quyen root", "sharepoint permission", "database", "drop table"]
    if any(kw in description for kw in sensitive_keywords):
        return {
            "decision": "REQUIRE_HITL",
            "action_type": "EXECUTE_HIGH_RISK",
            "target_status": "pending_hitl",
            "policy_triggered": "POLICY_SENSITIVE_ACTION_MANDATORY_HITL",
            "reason": "Yêu cầu chứa hành vi nhạy cảm (Reset password/Phân quyền/Hạ tầng)",
        }

    # Rule 3: Production Impact
    if is_production:
        return {
            "decision": "REQUIRE_HITL",
            "action_type": "EXECUTE_HIGH_RISK",
            "target_status": "pending_hitl",
            "policy_triggered": "POLICY_PRODUCTION_IMPACT_HITL",
            "reason": "Sự cố ảnh hưởng hệ thống Production",
        }

    # Rule 4: Groundedness Low (< 0.50) -> Human Handoff
    if groundedness < 0.50:
        return {
            "decision": "ESCALATE",
            "action_type": "HUMAN_HANDOFF",
            "target_status": "waiting_for_agent",
            "policy_triggered": "POLICY_LOW_GROUNDEDNESS_ESCALATE",
            "reason": "Giải pháp AI có điểm Groundedness thấp (< 0.50) — Chuyển Chuyên viên",
        }

    # Rule 5: Groundedness Medium (0.50 - 0.75) -> Needs Clarification
    if 0.50 <= groundedness < 0.75:
        return {
            "decision": "NEEDS_CLARIFICATION",
            "action_type": "ASK_CLARIFICATION",
            "target_status": "needs_clarification",
            "policy_triggered": "POLICY_MEDIUM_GROUNDEDNESS_CLARIFY",
            "reason": "Giải pháp cần người dùng làm rõ thêm thông tin",
        }

    # Rule 6: Low Confidence (< 0.60)
    if confidence < 0.60:
        return {
            "decision": "ESCALATE",
            "action_type": "HUMAN_HANDOFF",
            "target_status": "waiting_for_agent",
            "policy_triggered": "POLICY_LOW_CONFIDENCE_ESCALATE",
            "reason": "Độ tin cậy tổng thể của AI dưới 60% (PRD FR-09)",
        }

    # Rule 7: Calculated Risk Score Threshold (>= 0.65)
    if risk_score >= 0.65:
        return {
            "decision": "REQUIRE_HITL",
            "action_type": "EXECUTE_HIGH_RISK",
            "target_status": "pending_hitl",
            "policy_triggered": "POLICY_HIGH_RISK_SCORE_HITL",
            "reason": f"Điểm rủi ro tổng hợp cao ({risk_score:.2f} >= 0.65)",
        }

    # Default Rule: Auto Proceed
    return {
        "decision": "AUTO_PROCEED",
        "action_type": "AUTO_ANSWER",
        "target_status": "pending_closure",
        "policy_triggered": "POLICY_DEFAULT_AUTO_PROCEED",
        "reason": "Ticket đạt toàn bộ tiêu chuẩn an toàn tự động",
    }
