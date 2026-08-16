"""Normalized, server-enforced technician fulfillment-group eligibility."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class TechnicianFulfillmentGroup(Base):
    """One canonical catalog group that a technician may take new work from."""

    __tablename__ = "technician_fulfillment_groups"
    __table_args__ = (
        UniqueConstraint("technician_id", "fulfillment_group", name="uq_technician_fulfillment_group"),
        Index("idx_technician_fulfillment_group_group_technician", "fulfillment_group", "technician_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    technician_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    fulfillment_group: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
