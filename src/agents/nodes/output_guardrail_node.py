"""
Output Guardrail Node — Step 2 Post-Generation Guardrail.

Runs after RAG synthesis to sanitize output for PII, leaked secrets, or credentials.
"""
import logging
import re
from typing import Any, Dict

from src.agents.state import TicketAgentState

logger = logging.getLogger(__name__)

# Patterns for PII / Sensitive Data Sanitization
SECRET_PATTERNS = [
    (r"sk-[a-zA-Z0-9]{32,}", "[REDACTED_API_KEY]"),
    (r"(password|paswd|pwd)\s*=\s*['\"]?[^'\"]+['\"]?", "[REDACTED_CREDENTIAL]"),
    (r"postgres://[^\s]+", "[REDACTED_DB_URI]"),
    (r"mongodb(\+srv)?://[^\s]+", "[REDACTED_DB_URI]"),
]


async def output_guardrail_node(state: TicketAgentState) -> Dict[str, Any]:
    """Step 2 Output Guardrail Node: Sanitizes output text."""
    solution = state.get("suggested_solution", "")
    if not solution:
        return {}

    logger.info("[OutputGuardrailNode] Step 2: Sanitizing generated output for ticket #%s", state.get("ticket_number"))

    sanitized = solution
    for pattern, replacement in SECRET_PATTERNS:
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)

    if sanitized != solution:
        logger.warning("[OutputGuardrailNode] Sanitized sensitive data from solution for ticket #%s", state.get("ticket_number"))
        return {"suggested_solution": sanitized}

    return {}
