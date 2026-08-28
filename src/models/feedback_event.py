"""Append-only, privacy-filtered feedback evidence for offline improvement work."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, event, func
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


def _event_id() -> str:
    return str(uuid.uuid4())


class FeedbackEvent(Base):
    """An immutable snapshot, never a mutable replacement for ``Ticket.rating``.

    Unsafe source text is deliberately omitted from discarded events.  Events
    are append-only so a later rating, reopen, or human correction cannot
    rewrite the generation it refers to.
    """

    __tablename__ = "feedback_events"

    event_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_event_id)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    ticket_id: Mapped[int | None] = mapped_column(ForeignKey("tickets.id"), nullable=True, index=True)
    conversation_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    message_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    target_event_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)

    actor_role: Mapped[str] = mapped_column(String(32), nullable=False)
    query_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    answer_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    retrieved_source_ids_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    citations_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    model_provider: Mapped[str | None] = mapped_column(String(80), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(80), nullable=True)

    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    ticket_outcome: Mapped[str | None] = mapped_column(String(40), nullable=True)
    outcome_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    human_correction: Mapped[str | None] = mapped_column(Text, nullable=True)

    eligible_for_dataset: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    discard_reason: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    provenance_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


@event.listens_for(FeedbackEvent, "before_update")
def _reject_feedback_event_update(*_args) -> None:
    raise ValueError("FeedbackEvent rows are immutable; append a new event instead")


@event.listens_for(FeedbackEvent, "before_delete")
def _reject_feedback_event_delete(*_args) -> None:
    raise ValueError("FeedbackEvent rows are append-only and cannot be deleted")
