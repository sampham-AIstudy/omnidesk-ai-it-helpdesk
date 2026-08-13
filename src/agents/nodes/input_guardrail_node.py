"""
Input Guardrail Node — Step 1 Early Exit Guardrail.

Runs FIRST in the LangGraph workflow before any Classifier, RAG, or LLM calls.
If a security policy violation (Prompt Injection, Off-topic content, Bot attack) is detected:
- Flags is_blocked = True
- Sets action_taken = "blocked_by_guardrail"
- Instantly short-circuits the pipeline to END (0 LLM calls, 0 RAG searches).
"""
import logging
from typing import Any, Dict

from src.agents.state import TicketAgentState
from src.guardrails.input_guardrails import InputGuardrailPlugin
from src.observability.tracing import set_current_attributes, traced_async_operation

logger = logging.getLogger(__name__)
guardrail_plugin = InputGuardrailPlugin()


@traced_async_operation("guardrail.input")
async def input_guardrail_node(state: TicketAgentState) -> Dict[str, Any]:
    """Step 1 Input Guardrail Node."""
    title = state.get("title", "")
    description = state.get("description", "")
    full_text = f"{title} {description}".strip()

    logger.info("[InputGuardrailNode] Step 1: Evaluating security policies for ticket #%s", state.get("ticket_number"))

    eval_result = guardrail_plugin.on_user_message_callback(full_text)
    set_current_attributes({"helpdesk.guardrail.result": eval_result.get("decision", "UNKNOWN")})

    if eval_result.get("decision") == "BLOCK":
        reason = eval_result.get("reason", "Security policy violation")
        safe_response = eval_result.get(
            "safe_response",
            "Yêu cầu của bạn bị hệ thống an ninh từ chối do vi phạm chính sách bảo mật."
        )

        logger.warning(
            "[InputGuardrailNode] SHORT-CIRCUIT BLOCK on ticket #%s. Reason: %s",
            state.get("ticket_number"),
            reason
        )

        return {
            "is_blocked": True,
            "block_reason": reason,
            "block_type": "SECURITY_VIOLATION",
            "safe_response": safe_response,
            "suggested_solution": safe_response,
            "action_taken": "blocked_by_guardrail",
            "hitl_required": False,
            "auto_close_eligible": False,
        }

    # A vague request is safe, but must not be sent to retrieval: the nearest
    # KB document could otherwise create a confident but unrelated diagnosis.
    if eval_result.get("needs_clarification", False):
        response = eval_result.get("clarification_response")
        logger.info("[InputGuardrailNode] Ticket #%s needs clarification before AI processing.", state.get("ticket_number"))
        return {
            "is_blocked": False,
            "needs_clarification": True,
            "clarification_response": response,
            "suggested_solution": response,
            "action_taken": "ask_clarification",
            "auto_close_eligible": False,
        }

    logger.info("[InputGuardrailNode] Step 1 PASSED: Ticket #%s input is safe.", state.get("ticket_number"))
    return {"is_blocked": False, "needs_clarification": False}
