"""Service Request domain model.

Service requests deliberately live outside the Incident ``Ticket`` model: they
have a different identifier, lifecycle and fulfillment/approval semantics.
"""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models.ticket import FlexibleEnum


class ServiceRequestStatus(enum.StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    WAITING_FOR_USER = "waiting_for_user"
    FULFILLED = "fulfilled"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class ServiceRequest(Base):
    __tablename__ = "service_requests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    request_number: Mapped[str] = mapped_column(String(24), unique=True, nullable=False, index=True)
    service_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    service_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[ServiceRequestStatus] = mapped_column(
        FlexibleEnum(ServiceRequestStatus), default=ServiceRequestStatus.SUBMITTED, nullable=False, index=True
    )
    fulfillment_group: Mapped[str] = mapped_column(String(100), nullable=False)
    approval_policy: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False, default="low")
    sla_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    form_data: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    approval_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitter_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    requested_for_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Service Requests have their own fulfillment ownership.  This deliberately
    # does not reuse Ticket.assignee_id or the incident state machine.
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fulfilled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fulfilled_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

