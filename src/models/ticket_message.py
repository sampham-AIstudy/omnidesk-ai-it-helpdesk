"""Ticket conversation messages for agent/user/technician collaboration."""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class TicketMessageSender(str, enum.Enum):
    USER = "user"
    AGENT = "agent"
    TECHNICIAN = "technician"
    SYSTEM = "system"


class TicketMessage(Base):
    __tablename__ = "ticket_messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"), nullable=False, index=True)
    sender_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    sender_type: Mapped[TicketMessageSender] = mapped_column(
        Enum(TicketMessageSender), nullable=False, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sources_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(nullable=True)
    routing_hint: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="messages")
    sender: Mapped["User | None"] = relationship("User")

    def __repr__(self) -> str:
        return f"<TicketMessage #{self.id} ticket={self.ticket_id} sender={self.sender_type}>"
