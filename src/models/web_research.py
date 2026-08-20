"""Persistent audit trail for untrusted external research."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class WebResearchRun(Base):
    __tablename__ = "web_research_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    search_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    ticket_id: Mapped[int | None] = mapped_column(ForeignKey("tickets.id"), nullable=True, index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    sources: Mapped[list[WebResearchSource]] = relationship(
        back_populates="research_run", cascade="all, delete-orphan"
    )


class WebResearchSource(Base):
    __tablename__ = "web_research_sources"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    research_run_id: Mapped[int] = mapped_column(ForeignKey("web_research_runs.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    snippet: Mapped[str] = mapped_column(Text, default="")
    content: Mapped[str] = mapped_column(Text, default="")
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)  # OFFICIAL | WEB
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0)

    research_run: Mapped[WebResearchRun] = relationship(back_populates="sources")
