"""Privacy-safe retrieval outcome telemetry used for knowledge-gap analysis."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class KnowledgeGapEvent(Base):
    """One eligible retrieval turn, stored without user text or identifiers.

    ``is_knowledge_gap`` distinguishes a strong retrieval outcome from the
    subset that should contribute to a knowledge-expansion queue.  Retaining
    both lets the report calculate rates without retaining raw queries.
    """

    __tablename__ = "knowledge_gap_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    correlation_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    surface: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    transport: Mapped[str] = mapped_column(String(12), nullable=False, default="rest")
    tenant_scope: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    department_scope: Mapped[str | None] = mapped_column(String(100), nullable=True)
    normalized_topic: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    retrieval_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    retrieval_strategy: Mapped[str] = mapped_column(String(64), nullable=False)
    top_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    internal_evidence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    official_evidence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    historical_evidence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    episodic_evidence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    no_evidence: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    insufficient_evidence: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    web_research_triggered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    web_research_provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    web_research_result_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    web_research_rejected_result_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    web_research_failure_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    web_research_provenance_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    hitl_or_escalation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_knowledge_gap: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
