"""
Human-in-the-Loop (HITL) Decision Router Module
Evaluates proposals using the Risk-Aware Router Matrix: Confidence x Risk x Context.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class RiskAwareRouter:
    """Decision Matrix combining Confidence and Risk level."""

    def route(self, confidence_level: str, risk_level: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Map confidence and risk to decision: AUTO, REVIEW, HITL."""
        conf = confidence_level.upper()
        risk = risk_level.upper()
        ctx = context or {}

        # Risk overrides confidence for High/Critical actions
        if risk in ["HIGH", "CRITICAL"] or conf == "LOW":
            decision = "HITL"
            reason = f"Decision HITL triggered: Risk '{risk}', Confidence '{conf}'"
        elif conf == "HIGH" and risk == "LOW":
            decision = "AUTO"
            reason = "High confidence low risk: Approved for AUTO processing"
        elif conf == "HIGH" and risk == "MEDIUM":
            decision = "AUTO" if not ctx.get("is_vip") else "REVIEW"
            reason = "High confidence medium risk: Auto or Review based on VIP context"
        elif conf == "MEDIUM" and risk == "LOW":
            decision = "REVIEW"
            reason = "Medium confidence low risk: Routed for Human Review"
        else:
            decision = "HITL"
            reason = f"Combination Conf '{conf}' and Risk '{risk}' requires HITL approval"

        return {
            "decision": decision,
            "confidence_level": conf,
            "risk_level": risk,
            "reason": reason,
        }


def route_decision(confidence: float, risk: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """Helper function to map numeric confidence to level and evaluate router."""
    if confidence >= 0.90:
        conf_level = "HIGH"
    elif confidence >= 0.70:
        conf_level = "MEDIUM"
    else:
        conf_level = "LOW"

    router = RiskAwareRouter()
    return router.route(conf_level, risk, context)


if __name__ == "__main__":
    print("Test Router (High Conf, High Risk):", route_decision(0.95, "HIGH"))
    print("Test Router (High Conf, Low Risk):", route_decision(0.95, "LOW"))
