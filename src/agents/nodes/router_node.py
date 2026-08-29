"""Router node — Định tuyến ticket đến đúng nhóm kỹ thuật."""
from __future__ import annotations

import logging

from src.agents.state import TicketAgentState

logger = logging.getLogger(__name__)

# Routing matrix: (category, company_unit) → team
ROUTING_TABLE: dict[str, dict[str, str]] = {
    "network": {
        "default": "Network Team",
        "healthcare": "Healthcare IT - Network",
        "real_estate": "RE IT - Network",
        "automotive": "Auto IT - Network",
    },
    "software": {
        "default": "Software Support Team",
        "healthcare": "Healthcare IT - Software",
        "real_estate": "RE IT - Software",
        "automotive": "Auto IT - Software",
    },
    "hardware": {
        "default": "Hardware Support Team",
    },
    "access_permission": {
        "default": "Identity & Access Management (IAM)",
    },
    "email": {
        "default": "Messaging Team (Exchange)",
    },
    "erp_sap": {
        "default": "SAP Basis Team",
        "real_estate": "RE - SAP Team",
        "automotive": "Auto - SAP Team",
    },
    "security": {
        "default": "IT Security Team",
    },
    "hr_system": {
        "default": "HR Systems Team",
    },
    "infrastructure": {
        "default": "Infrastructure & DevOps Team",
        "healthcare": "Healthcare IT - Infrastructure (CRITICAL)",
    },
    "other": {
        "default": "IT General Support",
    },
}


async def router_node(state: TicketAgentState) -> TicketAgentState:
    """Định tuyến ticket đến đúng nhóm kỹ thuật."""
    category = state.get("category", "other")
    company = state.get("company_unit", "corporate")
    priority = state.get("priority", "medium")

    # Tra bảng routing
    category_routes = ROUTING_TABLE.get(category, ROUTING_TABLE["other"])
    team = category_routes.get(company, category_routes.get("default", "IT General Support"))

    # Nếu critical → thêm suffix
    if priority == "critical":
        team = f"{team} [🔴 CRITICAL]"

    logger.info(
        f"[Router] Ticket #{state.get('ticket_number')} → {team} "
        f"(category={category}, company={company})"
    )

    existing_action = state.get("action_taken")
    action_taken = existing_action if existing_action else "routed"

    return {
        **state,
        "routing_target": team,
        "action_taken": action_taken,
    }
