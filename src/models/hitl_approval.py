"""HITL Approval Model — Lưu lịch sử các lần xin duyệt HITL."""
from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base

if TYPE_CHECKING:
    from src.models.ticket import Ticket
    from src.models.user import User


class HITLApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class HITLApproval(Base):
    __tablename__ = "hitl_approvals"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)

    approval_type: Mapped[str] = mapped_column(String(50), default="manager_approval", nullable=False)
    status: Mapped[HITLApprovalStatus] = mapped_column(String(20), default=HITLApprovalStatus.PENDING, nullable=False)

    requested_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    decided_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)

    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decision_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    requested_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="hitl_approvals")
    requested_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[requested_by_id])
    decided_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[decided_by_id])
