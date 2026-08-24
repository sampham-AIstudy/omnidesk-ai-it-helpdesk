"""
SLA Guardrail Module
Monitors SLA timers, remaining time, breach risks, and triggers automatic escalations.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def evaluate_sla_status(ticket: dict[str, Any], remaining_minutes: float) -> dict[str, Any]:
    """Evaluate SLA breach risk and return status."""
    priority = ticket.get("priority", "P3")
    failed_attempts = ticket.get("failed_resolution_count", 0)

    if remaining_minutes <= 0:
        status = "BREACHED"
        should_escalate = True
    elif remaining_minutes <= 10 or priority == "P1":
        status = "BREACH_RISK"
        should_escalate = True
    elif remaining_minutes <= 60:
        status = "WARNING"
        should_escalate = False
    else:
        status = "NORMAL"
        should_escalate = False

    if failed_attempts >= 2:
        should_escalate = True
        status = "BREACH_RISK"

    return {
        "status": status,
        "remaining_minutes": remaining_minutes,
        "should_escalate": should_escalate,
        "reason": f"SLA status '{status}' with {remaining_minutes:.1f} mins remaining (Priority: {priority})",
    }
