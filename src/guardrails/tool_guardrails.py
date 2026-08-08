"""
Tool Execution Guardrail Module
Enforces policy check on LLM tool execution proposals.
LLM output is treated as a PROPOSAL, never direct execution authority.
"""

import logging
from typing import Any, Dict, Set

from src.guardrails.access_guardrails import check_tool_permission

logger = logging.getLogger(__name__)

HIGH_RISK_ACTIONS: Set[str] = {
    "reset_password",
    "disable_account",
    "unlock_privileged_account",
    "close_account",
    "restart_server",
    "restart_database",
    "change_firewall",
    "modify_network",
    "production_change",
    "delete_data",
    "change_permissions",
}


def evaluate_tool_call(user: Dict[str, Any], tool_proposal: Dict[str, Any], ticket: Dict[str, Any] = None) -> Dict[str, Any]:
    """Evaluate tool proposal and return ALLOW, DENY, or HITL policy decision."""
    tool_name = tool_proposal.get("tool_name", tool_proposal.get("name", ""))
    tool_args = tool_proposal.get("arguments", tool_proposal.get("args", {}))

    if not tool_name:
        return {"decision": "DENY", "risk": "CRITICAL", "reason": "Empty tool proposal name"}

    # 1. RBAC Check
    perm_res = check_tool_permission(user, tool_name)
    if not perm_res["allowed"]:
        return {
            "decision": "DENY",
            "risk": "HIGH",
            "reason": perm_res["reason"],
            "policy_id": "POLICY_RBAC_DENY",
        }

    # 2. Check High-Risk Actions -> Force HITL
    if tool_name in HIGH_RISK_ACTIONS:
        return {
            "decision": "HITL",
            "risk": "HIGH",
            "reason": f"Tool '{tool_name}' is classified as a high-risk operation requiring human approval",
            "policy_id": "POLICY_HIGH_RISK_HITL",
        }

    # 3. Check Production / VIP Impact
    if ticket:
        if ticket.get("is_production_impact", False):
            return {
                "decision": "HITL",
                "risk": "HIGH",
                "reason": "Production-impacting ticket requires human approval before tool execution",
                "policy_id": "POLICY_PROD_HITL",
            }
        if ticket.get("is_vip", False) and tool_name not in ["search_kb", "get_ticket"]:
            return {
                "decision": "HITL",
                "risk": "MEDIUM",
                "reason": "VIP user action requires human approval",
                "policy_id": "POLICY_VIP_HITL",
            }

    return {
        "decision": "ALLOW",
        "risk": "LOW",
        "reason": f"Tool proposal '{tool_name}' passed policy checks",
        "policy_id": "POLICY_ALLOW_LOW_RISK",
    }


if __name__ == "__main__":
    u = {"user_id": "u1", "role": "admin"}
    prop = {"tool_name": "restart_database"}
    print("Evaluate Tool Call:", evaluate_tool_call(u, prop))
