"""TicketAgentState — State schema cho LangGraph Help Desk workflow."""
from __future__ import annotations

from typing import Any, TypedDict


class TicketAgentState(TypedDict, total=False):
    """State đầy đủ cho Help Desk AI Agent workflow."""

    # ── Input ─────────────────────────────────────────────────────────────────
    ticket_id: int
    ticket_number: str
    title: str
    description: str
    submitter_id: int
    is_production_impact: bool
    submitter_is_vip: bool
    company_unit: str          # real_estate | automotive | healthcare | corporate
    department: str | None

    # ── Classification (output từ classifier node) ────────────────────────────
    category: str              # TicketCategory value
    priority: str              # TicketPriority value
    urgency: str               # TicketUrgency value
    confidence_score: float    # 0.0 – 1.0
    agent_reasoning: str       # LLM chain-of-thought

    # ── RAG (output từ rag_node) ──────────────────────────────────────────────
    rag_context: list[dict]    # [{content, metadata, relevance_score}]
    suggested_solution: str    # Synthesized answer từ RAG + LLM
    rag_sources: list[str]     # KB entry titles used
    runbook_steps: list[str]   # Extracted runbook steps nếu có

    # ── Routing ───────────────────────────────────────────────────────────────
    routing_target: str        # Đội kỹ thuật được route tới
    hitl_required: bool        # HITL cần thiết không?
    hitl_reason: str           # Lý do cần HITL

    # ── Action taken ──────────────────────────────────────────────────────────
    action_taken: str          # "auto_closed" | "routed" | "hitl_pending" | "escalated"
    auto_close_eligible: bool  # Có thể tự đóng không?

    # ── Error handling ────────────────────────────────────────────────────────
    error: str | None
    error_node: str | None

    # ── Metadata ──────────────────────────────────────────────────────────────
    model_used: str
    processing_start: str      # ISO timestamp
    token_count: int
