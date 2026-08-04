"""AuditLog model — Ghi nhận mọi hành động trên ticket."""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class AuditAction(str, enum.Enum):
    TICKET_CREATED = "ticket_created"
    TICKET_CLASSIFIED = "ticket_classified"
    TICKET_ROUTED = "ticket_routed"
    TICKET_AUTO_CLOSED = "ticket_auto_closed"
    TICKET_MANUALLY_CLOSED = "ticket_manually_closed"
    TICKET_ESCALATED = "ticket_escalated"
    TICKET_ASSIGNED = "ticket_assigned"
    HITL_TRIGGERED = "hitl_triggered"
    HITL_APPROVED = "hitl_approved"
    HITL_REJECTED = "hitl_rejected"
    SLA_WARNING = "sla_warning"
    SLA_BREACHED = "sla_breached"
    COMMENT_ADDED = "comment_added"
    STATUS_CHANGED = "status_changed"
    KB_SUGGESTION_SENT = "kb_suggestion_sent"
    KB_CREATED = "kb_created"
    KB_UPDATED = "kb_updated"
    KB_DELETED = "kb_deleted"
    RUNBOOK_EXECUTED = "runbook_executed"
    AGENT_DECISION = "agent_decision"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    ticket_id: Mapped[int | None] = mapped_column(
        ForeignKey("tickets.id"), nullable=True, index=True
    )
    actor_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    actor_type: Mapped[str] = mapped_column(
        String(20), default="system"  # "user" | "agent" | "system"
    )

    action: Mapped[AuditAction] = mapped_column(Enum(AuditAction), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON payload

    # For AI decisions
    confidence_score: Mapped[float | None] = mapped_column(nullable=True)
    model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    # Relationships
    ticket: Mapped["Ticket | None"] = relationship("Ticket", back_populates="audit_logs")
    actor: Mapped["User | None"] = relationship("User", back_populates="audit_logs")

    def __repr__(self) -> str:
        return f"<AuditLog ticket={self.ticket_id} action={self.action}>"
