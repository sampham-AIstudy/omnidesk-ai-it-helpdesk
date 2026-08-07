"""
Routing Guardrail Module
Validates technical assignment group routing proposals.
Auto-routes only if routing_confidence >= 0.85, assignment group exists/active, and not critical.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

VALID_ASSIGNMENT_GROUPS = {
    "Network Operations",
    "Endpoint Support",
    "Collaboration Team",
    "Enterprise Applications",
    "SOC",
    "Database Operations",
    "IT Support Tier 1",
    "IT Support Tier 2",
}


def evaluate_routing(proposed_group: str, confidence: float, ticket: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate assignment group routing decision."""
    if proposed_group not in VALID_ASSIGNMENT_GROUPS:
        return {
            "decision": "HITL",
            "reason": f"Unknown or inactive assignment group '{proposed_group}'",
        }

    is_critical = ticket.get("priority") == "P1" or ticket.get("is_security_incident", False)
    if is_critical:
        return {
            "decision": "HITL",
            "reason": "Critical P1 or security incident tickets require human verification before assignment",
        }

    if confidence < 0.85:
        return {
            "decision": "HITL",
            "reason": f"Routing confidence ({confidence:.2f}) below threshold 0.85",
        }

    return {
        "decision": "ALLOW",
        "assigned_group": proposed_group,
        "reason": f"Auto-routed to {proposed_group} with high confidence ({confidence:.2f})",
    }
