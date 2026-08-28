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
    rag_sources: list[Any]     # Persisted provenance links for KB/web sources
    runbook_steps: list[str]   # Extracted runbook steps nếu có
    # Các thành phần tín hiệu trung gian RAG confidence (tính tại rag_node, dùng ở output_guardrail_node)
    c_retrieval: float | None     # C_retrieval: độ tương quan top-1 & uy tín nguồn
    c_consensus: float | None     # C_consensus: độ đồng thuận thứ hạng giữa Dense Vector và BM25

    # ── Routing & Risk (output từ policy/hitl node) ───────────────────────────
    routing_target: str        # Đội kỹ thuật được route tới
    hitl_required: bool        # HITL cần thiết không?
    hitl_reason: str           # Lý do cần HITL
    risk_score: float
    decision_factors_json: str

    # ── Action taken ──────────────────────────────────────────────────────────
    action_taken: str          # "auto_closed" | "routed" | "hitl_pending" | "escalated" | "blocked_by_guardrail"
    auto_close_eligible: bool  # Có thể tự đóng không?

    # ── Guardrail Evaluation ──────────────────────────────────────────────────
    is_blocked: bool           # Guardrail early exit flag
    block_reason: str          # Lý do bị chặn
    block_type: str            # "PROMPT_INJECTION" | "OFF_TOPIC" | "TURNSTILE_FAILED" | "PII_LEAK"
    safe_response: str         # Thông điệp phản hồi an toàn khi bị chặn
    needs_clarification: bool  # Thiếu ngữ cảnh tối thiểu để phân loại/RAG an toàn
    clarification_response: str

    # ── Error handling ────────────────────────────────────────────────────────
    error: str | None
    error_node: str | None

    # ── Metadata ──────────────────────────────────────────────────────────────
    model_used: str
    processing_start: str      # ISO timestamp
    token_count: int
