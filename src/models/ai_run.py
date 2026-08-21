"""AI Run Model — Lưu AI Observability, Trace ID, Model Provider & Token Cost Metrics."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base

if TYPE_CHECKING:
    from src.models.ticket import Ticket
    from src.models.ticket_message import TicketMessage


class AIRun(Base):
    __tablename__ = "ai_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    trace_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)

    ticket_id: Mapped[int | None] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"), nullable=True, index=True)
    message_id: Mapped[int | None] = mapped_column(ForeignKey("ticket_messages.id", ondelete="CASCADE"), nullable=True)

    workflow: Mapped[str] = mapped_column(String(50), default="rag_chat", nullable=False)
    provider: Mapped[str] = mapped_column(String(50), default="mistral", nullable=False)
    model: Mapped[str] = mapped_column(String(100), default="mistral-small-latest", nullable=False)

    classification_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    retrieval_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    groundedness_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    input_guardrail_result: Mapped[str] = mapped_column(String(20), default="pass", nullable=False)
    output_guardrail_result: Mapped[str] = mapped_column(String(20), default="pass", nullable=False)

    input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    decision: Mapped[str] = mapped_column(String(50), default="AUTO_RESPOND", nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    ticket: Mapped[Ticket | None] = relationship("Ticket", back_populates="ai_runs")
    message: Mapped[TicketMessage | None] = relationship("TicketMessage")
