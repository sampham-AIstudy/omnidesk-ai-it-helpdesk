"""Review-gated preference candidates; these are not training jobs."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


def _candidate_id() -> str:
    return str(uuid.uuid4())


class PreferenceCandidate(Base):
    __tablename__ = "preference_candidates"
    __table_args__ = (
        CheckConstraint(
            "review_status IN ('PENDING_REVIEW', 'APPROVED', 'REJECTED')",
            name="ck_preference_candidates_review_status",
        ),
        CheckConstraint(
            "quality_tier IN ('HIGH', 'MEDIUM', 'LOW')",
            name="ck_preference_candidates_quality_tier",
        ),
    )

    candidate_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_candidate_id)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    group_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    chosen: Mapped[str] = mapped_column(Text, nullable=False)
    rejected: Mapped[str] = mapped_column(Text, nullable=False)
    source_event_ids_json: Mapped[str] = mapped_column(Text, nullable=False)
    label_evidence_json: Mapped[str] = mapped_column(Text, nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False)
    quality_tier: Mapped[str] = mapped_column(String(10), nullable=False, default="LOW", index=True)
    review_status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING_REVIEW", index=True)
    reviewed_by_id: Mapped[int | None] = mapped_column(nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # This is a one-way dataset control, separate from the immutable human
    # review decision. It preserves an auditable record when controlled smoke
    # data must remain in the append-only evidence trail.
    excluded_from_training: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    training_exclusion_reason: Mapped[str | None] = mapped_column(String(160), nullable=True)
    training_excluded_by: Mapped[str | None] = mapped_column(String(80), nullable=True)
    training_excluded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
