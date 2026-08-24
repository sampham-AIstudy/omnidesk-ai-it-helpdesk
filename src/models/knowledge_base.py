"""KnowledgeBase model — Lưu trữ entries cho RAG."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class KnowledgeBaseEntry(Base):
    __tablename__ = "knowledge_base"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Chroma vector ID (để đồng bộ)
    chroma_id: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)

    # Content
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    solution: Mapped[str | None] = mapped_column(Text, nullable=True)
    runbook: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON steps

    # Classification metadata
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)     # comma-separated

    # Scope
    company_unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    applicable_to_all: Mapped[bool] = mapped_column(Boolean, default=True)

    # Usage tracking
    usage_count: Mapped[int] = mapped_column(default=0)
    helpful_votes: Mapped[int] = mapped_column(default=0)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<KB #{self.id}: {self.title[:40]}>"
