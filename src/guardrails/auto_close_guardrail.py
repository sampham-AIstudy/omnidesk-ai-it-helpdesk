"""
Auto-Close Guardrail Module
Strict rules governing automatic ticket closure.
Zero auto-close for P1/P2 production incidents, security incidents, VIP issues, or ungrounded resolutions.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def evaluate_auto_close(ticket: dict[str, Any], resolution: dict[str, Any]) -> dict[str, Any]:
    """Evaluate whether a ticket can be automatically closed."""
    priority = ticket.get("priority", "P3")
    is_prod = ticket.get("is_production_impact", False)
    is_vip = ticket.get("is_vip", False)
    is_sec = ticket.get("is_security_incident", False)
    risk = ticket.get("risk_level", "LOW")

    solution_confidence = resolution.get("confidence", 0.0)
    grounded = resolution.get("grounded", False)
    approved_kb = resolution.get("approved_kb_source", True)

    # Hard block rules
    if priority in ["P1", "P2"] and is_prod:
        return {"can_auto_close": False, "action": "PROPOSE_RESOLUTION", "reason": "P1/P2 production incidents cannot be auto-closed"}

    if is_sec:
        return {"can_auto_close": False, "action": "PROPOSE_RESOLUTION", "reason": "Security incidents cannot be auto-closed"}

    if is_vip:
        return {"can_auto_close": False, "action": "PROPOSE_RESOLUTION", "reason": "VIP user tickets require human closure approval"}

    if risk in ["HIGH", "CRITICAL"]:
        return {"can_auto_close": False, "action": "PROPOSE_RESOLUTION", "reason": f"High risk ticket ({risk}) cannot be auto-closed"}

    if not grounded:
        return {"can_auto_close": False, "action": "PROPOSE_RESOLUTION", "reason": "Resolution instructions are not grounded in KB documents"}

    if not approved_kb:
        return {"can_auto_close": False, "action": "PROPOSE_RESOLUTION", "reason": "KB source is not approved"}

    if solution_confidence < 0.90:
        return {
            "can_auto_close": False,
            "action": "PROPOSE_RESOLUTION",
            "reason": f"Solution confidence ({solution_confidence:.2f}) below auto-close threshold 0.90",
        }

    return {
        "can_auto_close": True,
        "action": "AUTO_CLOSE",
        "reason": "Safe low-risk ticket with high confidence grounded resolution",
    }
