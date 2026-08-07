"""Auto-close node — Tự đóng ticket đơn giản khi confidence đủ cao."""
from __future__ import annotations

import logging

from src.agents.state import TicketAgentState
from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _is_auto_close_eligible(state: TicketAgentState) -> bool:
    """
    Điều kiện auto-close:
    - Confidence >= threshold (mặc định 0.75 theo PRD FR-09)
    - Không phải production impact
    - Không phải VIP (hoặc là VIP nhưng category đơn giản)
    - Category cho phép auto-close
    - Priority không phải critical
    - Có giải pháp từ RAG
    """
    confidence = state.get("confidence_score", 0.0)
    is_production = state.get("is_production_impact", False)
    is_vip = state.get("submitter_is_vip", False)
    category = state.get("category", "other")
    priority = state.get("priority", "medium")
    has_solution = bool(state.get("suggested_solution"))

    # Không auto-close các category nguy hiểm
    no_auto_close_categories = {"security", "infrastructure", "erp_sap"}

    if confidence < settings.confidence_threshold_auto_close:
        return False
    if is_production:
        return False
    if is_vip and category not in ("email", "software", "hardware"):
        return False
    if category in no_auto_close_categories:
        return False
    if priority == "critical":
        return False
    if not has_solution:
        return False

    return True


async def auto_close_check_node(state: TicketAgentState) -> TicketAgentState:
    """Kiểm tra ticket có đủ điều kiện tự đóng không."""
    eligible = _is_auto_close_eligible(state)

    logger.info(
        f"[AutoClose] Ticket #{state.get('ticket_number')} "
        f"auto_close_eligible={eligible} "
        f"confidence={state.get('confidence_score', 0):.2f}"
    )

    if eligible:
        action = "auto_closed"
    else:
        action = state.get("action_taken", "routed")

    return {
        **state,
        "auto_close_eligible": eligible,
        "action_taken": action,
    }
