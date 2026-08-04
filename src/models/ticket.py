"""Ticket model — Core entity của hệ thống Help Desk."""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class TicketCategory(str, enum.Enum):
    NETWORK = "network"                    # Mạng/kết nối
    SOFTWARE = "software"                  # Phần mềm/ứng dụng
    HARDWARE = "hardware"                  # Phần cứng
    ACCESS_PERMISSION = "access_permission"  # Quyền truy cập
    EMAIL = "email"                        # Email/Outlook
    ERP_SAP = "erp_sap"                   # ERP/SAP
    SECURITY = "security"                  # Bảo mật
    HR_SYSTEM = "hr_system"               # Hệ thống HR
    INFRASTRUCTURE = "infrastructure"      # Hạ tầng/Server
    OTHER = "other"                        # Khác


class TicketPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TicketUrgency(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EMERGENCY = "emergency"


class TicketStatus(str, enum.Enum):
    OPEN = "open"                           # Mới tạo
    CLASSIFYING = "classifying"             # Agent đang phân loại
    PENDING_HITL = "pending_hitl"           # Chờ HITL approval
    IN_PROGRESS = "in_progress"            # Đang xử lý
    PENDING_CLOSURE = "pending_closure"    # Chờ auto-close confirmation
    RESOLVED = "resolved"                  # Đã giải quyết
    CLOSED = "closed"                      # Đã đóng
    ESCALATED = "escalated"               # Đã leo thang
    REJECTED = "rejected"                  # Bị từ chối


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ticket_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)

    # Nội dung
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Classification (do AI phân loại)
    category: Mapped[TicketCategory | None] = mapped_column(Enum(TicketCategory), nullable=True)
    priority: Mapped[TicketPriority | None] = mapped_column(Enum(TicketPriority), nullable=True)
    urgency: Mapped[TicketUrgency | None] = mapped_column(Enum(TicketUrgency), nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # AI Analysis
    suggested_solution: Mapped[str | None] = mapped_column(Text, nullable=True)
    rag_sources: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string
    agent_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Routing
    routing_target: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_production_impact: Mapped[bool] = mapped_column(Boolean, default=False)

    # Status
    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus), default=TicketStatus.OPEN, nullable=False, index=True
    )

    # HITL
    hitl_required: Mapped[bool] = mapped_column(Boolean, default=False)
    hitl_approved_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    hitl_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    hitl_decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # LangGraph checkpoint key for resume
    graph_checkpoint_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Users
    submitter_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    # SLA
    sla_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sla_warning_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    sla_escalated: Mapped[bool] = mapped_column(Boolean, default=False)
    first_response_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    submitter: Mapped["User"] = relationship("User", back_populates="tickets", foreign_keys=[submitter_id])
    assignee: Mapped["User | None"] = relationship("User", back_populates="assigned_tickets", foreign_keys=[assignee_id])
    audit_logs: Mapped[list] = relationship("AuditLog", back_populates="ticket")

    def __repr__(self) -> str:
        return f"<Ticket #{self.ticket_number} [{self.status}]>"
