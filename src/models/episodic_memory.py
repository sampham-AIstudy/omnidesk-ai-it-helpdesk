"""Provenance-only index for Zero-Mem episodic retrieval.

The authoritative text remains in ``tickets`` and ``ticket_messages``.  These
tables only store a stable pointer, security boundary, ordering information and
observed entities, so memory never becomes a synthetic source of truth.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class EpisodicMemoryTrace(Base):
    __tablename__ = "episodic_memory_traces"
    __table_args__ = (UniqueConstraint("source_type", "ticket_id", "message_id", name="uq_memory_trace_source"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    trace_id: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(16), nullable=False)  # ticket | message
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"), nullable=False, index=True)
    message_id: Mapped[int | None] = mapped_column(ForeignKey("ticket_messages.id"), nullable=True, unique=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    department: Mapped[str] = mapped_column(String(100), default="", nullable=False, index=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    speaker: Mapped[str] = mapped_column(String(20), nullable=False)
    sequence_no: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    event_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    indexed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class EpisodicMemoryEntity(Base):
    __tablename__ = "episodic_memory_entities"
    __table_args__ = (UniqueConstraint("trace_id", "entity", name="uq_memory_trace_entity"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    trace_id: Mapped[str] = mapped_column(ForeignKey("episodic_memory_traces.trace_id"), nullable=False, index=True)
    entity: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False, default="TERM")
