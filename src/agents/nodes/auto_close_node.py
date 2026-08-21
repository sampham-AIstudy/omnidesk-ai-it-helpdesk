"""Closure guard — AI is never allowed to close an incident ticket."""
from __future__ import annotations

import logging

from src.agents.state import TicketAgentState

logger = logging.getLogger(__name__)


def _is_auto_close_eligible(state: TicketAgentState) -> bool:
    """Only the requester or a human technician may close a ticket."""
    return False


async def auto_close_check_node(state: TicketAgentState) -> TicketAgentState:
    """Record that the AI may suggest a resolution, but never close it."""
    logger.info(
        f"[ClosureGuard] Ticket #{state.get('ticket_number')} remains open for user or technician closure"
    )

    return {
        **state,
        "auto_close_eligible": False,
    }
