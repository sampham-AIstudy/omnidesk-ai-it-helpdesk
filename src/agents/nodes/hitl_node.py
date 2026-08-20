"""HITL node — Multi-Factor Risk Engine & Deterministic Policy Engine Integration."""
from __future__ import annotations

import json
import logging

from src.agents.nodes.policy_engine import evaluate_policy
from src.agents.state import TicketAgentState
from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _determine_hitl(state: TicketAgentState) -> tuple[bool, str]:
    """Baseline confidence gate from PRD FR-09, independent of risk policies."""
    if state.get("is_production_impact", False):
        return True, "production impact requires HITL review"
    confidence = float(state.get("confidence_score", 0.0))
    if confidence < settings.confidence_threshold_hitl:
        return True, "Confidence dưới 60% requires HITL review"
    return False, "Confidence is within the normal processing band"


def calculate_ticket_risk_score(state: TicketAgentState) -> tuple[float, dict[str, float]]:
    """
    Multi-Factor Risk Engine (Calibrated 0.0 -> 1.0):
    Risk Score = (priority * 0.20) + (impact * 0.25) + (action_sensitivity * 0.30) + (uncertainty * 0.15) + (privilege * 0.10)
    """
    confidence = state.get("confidence_score", 0.5)
    is_production = state.get("is_production_impact", False)
    is_vip = state.get("submitter_is_vip", False)
    category = state.get("category", "other")
    priority = state.get("priority", "medium")
    urgency = state.get("urgency", "medium")
    description = (state.get("description", "") + " " + state.get("title", "")).lower()

    # 1. Priority Score (0.20)
    priority_map = {"low": 0.1, "medium": 0.3, "high": 0.7, "critical": 1.0}
    priority_score = priority_map.get(priority, 0.3)

    # 2. System Impact Score (0.25)
    impact_score = 1.0 if is_production else (0.8 if urgency == "emergency" else 0.2)

    # 3. Action Sensitivity Score (0.30)
    action_risk_keywords = ["reset password", "admin", "mat khau", "quyen truy cap", "permission", "hardware replacement", "thay the phan cung", "database", "server"]
    has_sensitive_action = any(k in description for k in action_risk_keywords)
    cat_risk_map = {"security": 1.0, "infrastructure": 0.8, "access_permission": 0.9, "erp_sap": 0.7}
    action_score = max(cat_risk_map.get(category, 0.2), 1.0 if has_sensitive_action else 0.1)

    # 4. Uncertainty Score (0.15)
    uncertainty_score = max(0.0, 1.0 - confidence)

    # 5. Privilege Risk Score (0.10)
    privilege_score = 1.0 if is_vip else 0.2

    # Weighted Risk Sum
    risk_score = round(
        (priority_score * 0.20) +
        (impact_score * 0.25) +
        (action_score * 0.30) +
        (uncertainty_score * 0.15) +
        (privilege_score * 0.10),
        2
    )

    components = {
        "priority": priority_score,
        "impact": impact_score,
        "action_sensitivity": action_score,
        "uncertainty": uncertainty_score,
        "privilege": privilege_score,
    }

    return risk_score, components


async def hitl_check_node(state: TicketAgentState) -> TicketAgentState:
    """Đánh giá Risk Engine & Deterministic Safety Policy Engine."""
    risk_score, components = calculate_ticket_risk_score(state)
    policy_res = evaluate_policy(state, risk_score)

    # No grounded KB context means the AI must invite a specialist, regardless
    # of the classifier's confidence about the ticket category.
    if (
        not state.get("rag_context")
        and not state.get("is_production_impact", False)
        and policy_res["decision"] != "REQUIRE_HITL"
    ):
        return {
            **state,
            "hitl_required": False,
            "hitl_reason": "No sufficiently relevant knowledge-base guidance; hand off to IT Support.",
            "risk_score": risk_score,
            "action_taken": "human_handoff",
            "decision_factors_json": json.dumps({
                "risk_score": risk_score,
                "components": components,
                "policy_decision": "ESCALATE",
                "policy_triggered": "POLICY_NO_RELEVANT_KB_HANDOFF",
                "action_type": "HUMAN_HANDOFF",
                "target_status": "waiting_for_agent",
            }, ensure_ascii=False),
        }

    confidence_requires_hitl, confidence_reason = _determine_hitl(state)
    hitl_required = confidence_requires_hitl or (policy_res["decision"] == "REQUIRE_HITL")
    if confidence_requires_hitl:
        reason_text = f"[confidence_gate] {confidence_reason} (Risk: {risk_score:.2f})"
    else:
        reason_text = f"[{policy_res['policy_triggered']}] {policy_res['reason']} (Risk: {risk_score:.2f})"

    logger.info(
        f"[PolicyEngine] Ticket #{state.get('ticket_number')} "
        f"Decision: {policy_res['decision']} | Action: {policy_res['action_type']} | "
        f"Reason: {reason_text}"
    )

    decision_factors = {
        "risk_score": risk_score,
        "components": components,
        "policy_decision": policy_res["decision"],
        "policy_triggered": policy_res["policy_triggered"],
        "action_type": policy_res["action_type"],
        "target_status": policy_res["target_status"],
    }

    return {
        **state,
        "hitl_required": hitl_required,
        "hitl_reason": reason_text,
        "risk_score": risk_score,
        "action_taken": policy_res["action_type"].lower(),
        "decision_factors_json": json.dumps(decision_factors, ensure_ascii=False),
    }
