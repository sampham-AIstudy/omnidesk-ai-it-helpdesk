"""AuditLog model — Ghi nhận mọi hành động trên ticket."""
from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base

if TYPE_CHECKING:
    from src.models.ticket import Ticket
    from src.models.user import User


class AuditAction(enum.StrEnum):
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
    WEB_RESEARCH_EXECUTED = "web_research_executed"
    DUPLICATE_DETECTED = "duplicate_detected"
    DUPLICATE_PREVENTED = "duplicate_prevented"
    DUPLICATE_CONFIRMED = "duplicate_confirmed"
    DUPLICATE_FALSE_POSITIVE = "duplicate_false_positive"
    MEMORY_RETRIEVED = "memory_retrieved"
    SERVICE_REQUEST_CREATED = "service_request_created"
    SERVICE_REQUEST_ASSIGNED = "service_request_assigned"
    SERVICE_REQUEST_STATUS_CHANGED = "service_request_status_changed"
    SERVICE_REQUEST_FULFILLED = "service_request_fulfilled"
    SERVICE_REQUEST_APPROVAL_REQUIRED = "service_request_approval_required"
    SERVICE_REQUEST_APPROVED = "service_request_approved"
    SERVICE_REQUEST_REJECTED = "service_request_rejected"
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DEACTIVATED = "user_deactivated"
    USER_REACTIVATED = "user_reactivated"
    TECHNICIAN_FULFILLMENT_GROUPS_UPDATED = "technician_fulfillment_groups_updated"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    ticket_id: Mapped[int | None] = mapped_column(
        ForeignKey("tickets.id"), nullable=True, index=True
    )
    service_request_id: Mapped[int | None] = mapped_column(
        ForeignKey("service_requests.id"), nullable=True, index=True
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
    ticket: Mapped[Ticket | None] = relationship("Ticket", back_populates="audit_logs")
    actor: Mapped[User | None] = relationship("User", back_populates="audit_logs")

    def __repr__(self) -> str:
        return f"<AuditLog ticket={self.ticket_id} action={self.action}>"
