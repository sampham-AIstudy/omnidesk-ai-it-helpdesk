"""Ticket model — Core entity của hệ thống Help Desk."""
from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    TypeDecorator,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base

if TYPE_CHECKING:
    from src.models.user import User


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


class TicketSupportMode(str, enum.Enum):
    AI = "ai"
    HUMAN = "human"


class TicketStatus(str, enum.Enum):
    OPEN = "open"                           # Mới tạo
    CLASSIFYING = "classifying"             # Agent đang phân loại
    NEEDS_CLARIFICATION = "needs_clarification" # AI cần thêm thông tin
    PENDING_HITL = "pending_hitl"           # Chờ HITL approval
    IN_PROGRESS = "in_progress"            # Đang xử lý
    WAITING_FOR_AGENT = "waiting_for_agent" # Chờ chuyên viên tiếp nhận
    HUMAN_ACTIVE = "human_active"           # Chuyên viên đang hỗ trợ
    PENDING_CLOSURE = "pending_closure"    # Chờ người dùng/chuyên viên xác nhận
    RESOLVED = "resolved"                  # Đã giải quyết
    CLOSED = "closed"                      # Đã đóng
    REOPENED = "reopened"                  # Mở lại
    ESCALATED = "escalated"               # Đã leo thang
    REJECTED = "rejected"                  # Bị từ chối
    SECURITY_REVIEW = "security_review"    # Nghi vấn bảo mật / Forensic audit
    CANCELLED = "cancelled"                # Đã hủy


ALLOWED_TICKET_TRANSITIONS: dict[TicketStatus, set[TicketStatus]] = {
    TicketStatus.OPEN: {TicketStatus.CLASSIFYING, TicketStatus.NEEDS_CLARIFICATION, TicketStatus.PENDING_HITL, TicketStatus.IN_PROGRESS, TicketStatus.WAITING_FOR_AGENT, TicketStatus.RESOLVED, TicketStatus.REJECTED, TicketStatus.SECURITY_REVIEW, TicketStatus.CANCELLED},
    TicketStatus.CLASSIFYING: {TicketStatus.NEEDS_CLARIFICATION, TicketStatus.PENDING_HITL, TicketStatus.IN_PROGRESS, TicketStatus.WAITING_FOR_AGENT, TicketStatus.RESOLVED, TicketStatus.REJECTED, TicketStatus.SECURITY_REVIEW, TicketStatus.CANCELLED},
    TicketStatus.NEEDS_CLARIFICATION: {TicketStatus.CLASSIFYING, TicketStatus.IN_PROGRESS, TicketStatus.WAITING_FOR_AGENT, TicketStatus.CANCELLED},
    TicketStatus.PENDING_HITL: {TicketStatus.IN_PROGRESS, TicketStatus.WAITING_FOR_AGENT, TicketStatus.REJECTED, TicketStatus.CLOSED, TicketStatus.CANCELLED},
    TicketStatus.IN_PROGRESS: {TicketStatus.NEEDS_CLARIFICATION, TicketStatus.WAITING_FOR_AGENT, TicketStatus.HUMAN_ACTIVE, TicketStatus.ESCALATED, TicketStatus.PENDING_CLOSURE, TicketStatus.RESOLVED, TicketStatus.CLOSED, TicketStatus.CANCELLED},
    TicketStatus.WAITING_FOR_AGENT: {TicketStatus.HUMAN_ACTIVE, TicketStatus.ESCALATED, TicketStatus.CLOSED, TicketStatus.CANCELLED},
    TicketStatus.HUMAN_ACTIVE: {TicketStatus.ESCALATED, TicketStatus.PENDING_CLOSURE, TicketStatus.RESOLVED, TicketStatus.CLOSED, TicketStatus.CANCELLED},
    TicketStatus.ESCALATED: {TicketStatus.HUMAN_ACTIVE, TicketStatus.RESOLVED, TicketStatus.CLOSED, TicketStatus.CANCELLED},
    TicketStatus.PENDING_CLOSURE: {TicketStatus.RESOLVED, TicketStatus.CLOSED, TicketStatus.REOPENED, TicketStatus.WAITING_FOR_AGENT},
    TicketStatus.RESOLVED: {TicketStatus.CLOSED, TicketStatus.REOPENED},
    TicketStatus.CLOSED: {TicketStatus.REOPENED},
    TicketStatus.REOPENED: {TicketStatus.CLASSIFYING, TicketStatus.WAITING_FOR_AGENT, TicketStatus.HUMAN_ACTIVE, TicketStatus.IN_PROGRESS},
    TicketStatus.REJECTED: set(),
    TicketStatus.SECURITY_REVIEW: {TicketStatus.CLASSIFYING, TicketStatus.REJECTED, TicketStatus.CLOSED},
    TicketStatus.CANCELLED: set(),
}


def can_transition_ticket(current_status: TicketStatus | str, new_status: TicketStatus | str) -> bool:
    """Validate if transitioning from current_status to new_status is allowed under State Machine rules."""
    try:
        curr_enum = TicketStatus(current_status)
        new_enum = TicketStatus(new_status)
    except ValueError:
        return False
    if curr_enum == new_enum:
        return True
    return new_enum in ALLOWED_TICKET_TRANSITIONS.get(curr_enum, set())


class FlexibleEnum(TypeDecorator):
    """
    Robust Enum TypeDecorator for SQLAlchemy:
    - Handles case mismatches (e.g. 'software' vs 'SOFTWARE', 'ACCESS_PERMISSION' vs 'access_permission')
    - Handles string values or Enum instances when writing to DB
    - Graceful fallback when reading unknown values instead of crashing with 500 Internal Server Error
    """
    impl = String(50)
    cache_ok = True

    def __init__(self, enum_cls, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.enum_cls = enum_cls

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, self.enum_cls):
            return value.value
        return str(value).lower().strip()

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        val_str = str(value).lower().strip()
        for e in self.enum_cls:
            if e.value.lower() == val_str or e.name.lower() == val_str:
                return e
        for attr in ('OTHER', 'other'):
            if hasattr(self.enum_cls, attr):
                return getattr(self.enum_cls, attr)
        return list(self.enum_cls)[0]


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ticket_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)

    # Nội dung
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Classification (do AI phân loại)
    category: Mapped[TicketCategory | None] = mapped_column(FlexibleEnum(TicketCategory), nullable=True)
    priority: Mapped[TicketPriority | None] = mapped_column(FlexibleEnum(TicketPriority), nullable=True)
    urgency: Mapped[TicketUrgency | None] = mapped_column(FlexibleEnum(TicketUrgency), nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # AI Analysis
    suggested_solution: Mapped[str | None] = mapped_column(Text, nullable=True)
    rag_sources: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string
    agent_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Routing & Support Mode
    routing_target: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_production_impact: Mapped[bool] = mapped_column(Boolean, default=False)
    support_mode: Mapped[TicketSupportMode] = mapped_column(
        FlexibleEnum(TicketSupportMode), default=TicketSupportMode.AI, nullable=False
    )

    # Status
    status: Mapped[TicketStatus] = mapped_column(
        FlexibleEnum(TicketStatus), default=TicketStatus.OPEN, nullable=False, index=True
    )

    # Closure & Rating
    closed_by: Mapped[str | None] = mapped_column(String(50), nullable=True)
    resolution_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Duplicate/incident linkage. Never used to auto-close or reject a ticket.
    duplicate_of_ticket_id: Mapped[int | None] = mapped_column(ForeignKey("tickets.id"), nullable=True, index=True)
    duplicate_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    duplicate_detection_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    duplicate_confirmed_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    parent_incident_ticket_id: Mapped[int | None] = mapped_column(ForeignKey("tickets.id"), nullable=True, index=True)

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

    # SLA & Activity
    sla_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sla_warning_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    sla_escalated: Mapped[bool] = mapped_column(Boolean, default=False)
    first_response_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reopened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Expedite & Pin
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    pinned_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    pinned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pin_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    submitter: Mapped[User] = relationship("User", back_populates="tickets", foreign_keys=[submitter_id])
    assignee: Mapped[User | None] = relationship("User", back_populates="assigned_tickets", foreign_keys=[assignee_id])
    audit_logs: Mapped[list] = relationship("AuditLog", back_populates="ticket")
    messages: Mapped[list] = relationship("TicketMessage", back_populates="ticket")
    hitl_approvals: Mapped[list] = relationship("HITLApproval", back_populates="ticket", cascade="all, delete-orphan")
    ai_runs: Mapped[list] = relationship("AIRun", back_populates="ticket", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Ticket #{self.ticket_number} [{self.status}]>"
