"""
LangGraph Help Desk Agent Workflow with Multi-Stage Guardrail Short-Circuiting.

Flow:
  START ──► input_guardrail (Step 1)
               │
               ├─── [if is_blocked == True] ──► END (SHORT-CIRCUIT EARLY EXIT!)
               │
               └─── [if safe] ──► classify ──► rag ──► output_guardrail (Step 2)
                                                             │
                                                             ▼
                                                        hitl_check
                                                             │
                                                             ├─── [if hitl] ──► END (pending_hitl)
                                                             └─── [if not hitl] ──► router ──► END
"""
from __future__ import annotations

import logging

from langgraph.graph import END, START, StateGraph

from src.agents.nodes.classifier import classify_node
from src.agents.nodes.hitl_node import hitl_check_node
from src.agents.nodes.input_guardrail_node import input_guardrail_node
from src.agents.nodes.output_guardrail_node import output_guardrail_node
from src.agents.nodes.rag_node import rag_node
from src.agents.nodes.router_node import router_node
from src.agents.state import TicketAgentState

logger = logging.getLogger(__name__)


# ─── Edge Routing Functions ───────────────────────────────────────────────────

def after_input_guardrail(state: TicketAgentState) -> str:
    """Step 1 Input Guardrail Edge: Short-circuit to END if blocked."""
    if state.get("is_blocked", False):
        logger.warning(f"[Graph] → SHORT-CIRCUIT BLOCK for ticket #{state.get('ticket_number')}. Stopping pipeline!")
        return "end_blocked"
    if state.get("needs_clarification", False):
        logger.info("[Graph] → CLARIFICATION_REQUIRED for ticket #%s. Skipping LLM and RAG.", state.get("ticket_number"))
        return "end_clarification"
    return "classify"


def after_classify(state: TicketAgentState) -> str:
    """Sau classify: nếu lỗi → dừng."""
    if state.get("error"):
        logger.error(f"[Graph] Classify error: {state.get('error')}")
        return "end_error"
    return "rag"


def after_hitl_check(state: TicketAgentState) -> str:
    """Sau HITL check: nếu cần HITL → dừng (DB cập nhật status pending_hitl)."""
    if state.get("hitl_required", False):
        logger.info(f"[Graph] → HITL_PAUSE for ticket #{state.get('ticket_number')}")
        return "end_hitl_pending"
    return "router"


# ─── Build Graph ─────────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    graph = StateGraph(TicketAgentState)

    # Add nodes
    graph.add_node("input_guardrail", input_guardrail_node)
    graph.add_node("classify", classify_node)
    graph.add_node("rag", rag_node)
    graph.add_node("output_guardrail", output_guardrail_node)
    graph.add_node("hitl_check", hitl_check_node)
    graph.add_node("router", router_node)

    # Edges
    graph.add_edge(START, "input_guardrail")

    # Step 1 Early Exit Short-Circuit
    graph.add_conditional_edges(
        "input_guardrail",
        after_input_guardrail,
        {
            "end_blocked": END,  # SHORT-CIRCUIT EARLY EXIT!
            "end_clarification": END,
            "classify": "classify",
        },
    )

    graph.add_conditional_edges(
        "classify",
        after_classify,
        {
            "rag": "rag",
            "end_error": END,
        },
    )

    graph.add_edge("rag", "output_guardrail")
    graph.add_edge("output_guardrail", "hitl_check")

    graph.add_conditional_edges(
        "hitl_check",
        after_hitl_check,
        {
            "end_hitl_pending": END,   # Pause: ticket status = pending_hitl in DB
            "router": "router",
        },
    )

    graph.add_edge("router", END)

    return graph.compile()


# Singleton compiled graph
agent = build_graph()


async def process_ticket(
    ticket_id: int,
    ticket_number: str,
    title: str,
    description: str,
    submitter_id: int,
    is_production_impact: bool = False,
    submitter_is_vip: bool = False,
    company_unit: str = "corporate",
    department: str | None = None,
) -> TicketAgentState:
    """
    Chạy Help Desk agent workflow cho một ticket.
    Returns final state sau khi graph hoàn thành.
    """
    initial_state: TicketAgentState = {
        "ticket_id": ticket_id,
        "ticket_number": ticket_number,
        "title": title,
        "description": description,
        "submitter_id": submitter_id,
        "is_production_impact": is_production_impact,
        "submitter_is_vip": submitter_is_vip,
        "company_unit": company_unit,
        "department": department,
        "hitl_required": False,
        "is_blocked": False,
        "needs_clarification": False,
        "error": None,
    }

    logger.info(f"[Graph] Starting workflow for ticket #{ticket_number}")
    final_state = await agent.ainvoke(initial_state)
    logger.info(
        f"[Graph] Finished ticket #{ticket_number}: "
        f"action={final_state.get('action_taken')} "
        f"is_blocked={final_state.get('is_blocked')} "
        f"hitl={final_state.get('hitl_required')}"
    )
    return final_state
