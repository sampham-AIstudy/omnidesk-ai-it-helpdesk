"""
Access Control & RBAC Guardrails Module
Enforces Role-Based Access Control (RBAC) and Multi-Tenant Company Isolation.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Tool permissions by user role
ROLE_PERMISSIONS: dict[str, list[str]] = {
    "employee": [
        "search_kb",
        "get_own_ticket",
        "create_ticket",
        "add_ticket_comment",
    ],
    "helpdesk": [
        "search_kb",
        "get_ticket",
        "update_ticket",
        "add_ticket_comment",
        "route_ticket_low_risk",
    ],
    "technician": [
        "search_kb",
        "get_ticket",
        "update_ticket",
        "add_ticket_comment",
        "route_ticket_low_risk",
        "propose_resolution",
    ],
    "admin": [
        "search_kb",
        "get_ticket",
        "update_ticket",
        "add_ticket_comment",
        "route_ticket",
        "unlock_account",
        "reset_password",
        "approve_hitl",
        "manage_system",
    ],
}


def check_ticket_access(user: dict[str, Any], ticket: dict[str, Any]) -> dict[str, Any]:
    """Validate ticket access based on tenant isolation, department scope, and role."""
    user_company = str(user.get("company_unit", user.get("company", ""))).lower()
    ticket_company = str(ticket.get("company_unit", ticket.get("company", ""))).lower()

    user_role = str(user.get("role", "employee")).lower()
    user_id = str(user.get("user_id", user.get("id", "")))
    ticket_creator_id = str(ticket.get("created_by_id", ticket.get("user_id", "")))

    # Cross-tenant isolation check
    central_it = user_role == "admin" or user_company == "corporate"
    if not central_it and user_company and ticket_company and user_company != ticket_company:
        return {
            "allowed": False,
            "decision": "DENY",
            "reason": f"Cross-tenant access denied: User company '{user_company}' vs Ticket company '{ticket_company}'",
        }

    # Employee role scope check (can only access own tickets)
    if user_role == "employee" and user_id and ticket_creator_id and user_id != ticket_creator_id:
        return {
            "allowed": False,
            "decision": "DENY",
            "reason": "Employees can only view and update their own tickets",
        }

    return {"allowed": True, "decision": "ALLOW", "reason": "Authorized ticket access"}


def check_kb_access(user: dict[str, Any], doc_metadata: dict[str, Any]) -> dict[str, Any]:
    """Validate KB document retrieval access by tenant and department."""
    user_company = str(user.get("company_unit", user.get("company", ""))).lower()
    doc_company = str(doc_metadata.get("company_unit", doc_metadata.get("company", "all"))).lower()
    user_department = str(user.get("department", "")).lower()
    doc_department = str(doc_metadata.get("department", "")).lower()
    user_role = str(user.get("role", "employee")).lower()
    central_it = user_role == "admin"

    applicable_to_all = doc_metadata.get("applicable_to_all", True)
    if isinstance(applicable_to_all, str):
        applicable_to_all = applicable_to_all.lower() in {"true", "1", "yes", "all"}
    company_allowed = applicable_to_all or doc_company in {"", "all", user_company}
    if not central_it and not company_allowed:
        return {
            "allowed": False,
            "decision": "DENY",
            "reason": f"KB tenant isolation mismatch: '{user_company}' vs '{doc_company}'",
        }

    if not central_it and doc_department and doc_department != user_department:
        return {
            "allowed": False,
            "decision": "DENY",
            "reason": "KB department scope mismatch",
        }

    return {"allowed": True, "decision": "ALLOW", "reason": "Authorized KB access"}


def check_tool_permission(user: dict[str, Any], tool_name: str) -> dict[str, Any]:
    """Validate tool execution permissions by role."""
    user_role = str(user.get("role", "employee")).lower()
    allowed_tools = ROLE_PERMISSIONS.get(user_role, ROLE_PERMISSIONS["employee"])

    if tool_name not in allowed_tools and user_role != "admin":
        return {
            "allowed": False,
            "decision": "DENY",
            "reason": f"Role '{user_role}' is not authorized to execute tool '{tool_name}'",
        }

    return {"allowed": True, "decision": "ALLOW", "reason": f"Tool '{tool_name}' permitted for role '{user_role}'"}


if __name__ == "__main__":
    u = {"user_id": "u1", "company_unit": "VinUni", "role": "employee"}
    t = {"ticket_id": "t1", "company_unit": "VinFast", "created_by_id": "u2"}
    print("Cross Tenant Check:", check_ticket_access(u, t))
