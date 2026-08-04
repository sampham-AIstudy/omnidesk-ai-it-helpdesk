"""HITL node — Xác định xem ticket có cần Human-in-the-Loop không."""
from __future__ import annotations

import logging

from src.agents.state import TicketAgentState
from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _determine_hitl(state: TicketAgentState) -> tuple[bool, str]:
    """
    Quyết định HITL dựa trên các tiêu chí:
    - Confidence thấp (< threshold)
    - Production impact
    - VIP submitter
    - Ticket category nhạy cảm (security, infrastructure critical)
    - Priority critical
    """
    reasons = []

    confidence = state.get("confidence_score", 0.5)
    is_production = state.get("is_production_impact", False)
    is_vip = state.get("submitter_is_vip", False)
    category = state.get("category", "other")
    priority = state.get("priority", "medium")
    urgency = state.get("urgency", "medium")

    # 1. Confidence thấp
    if confidence < settings.confidence_threshold_hitl:
        reasons.append(f"Confidence thấp ({confidence:.0%})")

    # 2. Production system impact
    if is_production:
        reasons.append("Ảnh hưởng hệ thống production")

    # 3. VIP submitter
    if is_vip:
        reasons.append("Người gửi là VIP")

    # 4. Category nhạy cảm + mức độ cao
    sensitive_categories = {
        "security": "always",          # Luôn HITL
        "infrastructure": "high",      # HITL nếu priority ≥ high
        "erp_sap": "high",
        "hr_system": "critical",       # HITL nếu critical
    }

    cat_rule = sensitive_categories.get(category, None)
    if cat_rule == "always":
        reasons.append(f"Category '{category}' luôn cần phê duyệt")
    elif cat_rule == "high" and priority in ("high", "critical"):
        reasons.append(f"Category '{category}' với priority '{priority}' cần phê duyệt")
    elif cat_rule == "critical" and priority == "critical":
        reasons.append(f"Category '{category}' critical cần phê duyệt")

    # 5. Emergency urgency luôn HITL
    if urgency == "emergency":
        reasons.append("Mức khẩn cấp: Emergency")

    hitl_required = len(reasons) > 0
    reason_text = "; ".join(reasons) if reasons else ""

    return hitl_required, reason_text


async def hitl_check_node(state: TicketAgentState) -> TicketAgentState:
    """Đánh dấu ticket cần HITL hay không."""
    hitl_required, reason = _determine_hitl(state)

    if hitl_required:
        logger.info(
            f"[HITL] Ticket #{state.get('ticket_number')} cần HITL: {reason}"
        )
    else:
        logger.info(
            f"[HITL] Ticket #{state.get('ticket_number')} không cần HITL"
        )

    return {
        **state,
        "hitl_required": hitl_required,
        "hitl_reason": reason,
    }
