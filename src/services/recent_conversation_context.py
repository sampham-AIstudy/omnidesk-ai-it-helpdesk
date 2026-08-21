"""Bounded, scoped short-term conversation context for LLM generation.

This module deliberately keeps chronological recent history separate from
Zero-Mem's relevance-based episodic retrieval.  Every rendered history block
is untrusted data and is never used as a system instruction.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.models.chat_conversation import ChatConversation, ChatMessage
from src.models.ticket_message import TicketMessage, TicketMessageSender

settings = get_settings()
T = TypeVar("T")
_CONVERSATIONAL_TICKET_SENDERS = (
    TicketMessageSender.USER,
    TicketMessageSender.AGENT,
    TicketMessageSender.TECHNICIAN,
)


MAX_HISTORY_MESSAGE_CHARS = 4000
MAX_WORKSPACE_RECENT_HISTORY_CHARS = 16000
MAX_TICKET_RECENT_HISTORY_CHARS = 12000


@dataclass(frozen=True)
class RecentConversationMessage:
    """A bounded transcript record safe to render as ordinary prompt data."""

    message_id: str
    role: str
    content: str


def _bounded_content(content: str, limit: int) -> str:
    effective_limit = min(limit, MAX_HISTORY_MESSAGE_CHARS)
    value = content.strip()
    return value if len(value) <= effective_limit else value[:effective_limit] + "…"


async def load_workspace_recent_history(
    db: AsyncSession,
    *,
    conversation_id: str,
    user_id: int,
    exclude_message_id: str | None,
    limit: int | None = None,
) -> list[RecentConversationMessage]:
    """Load only the caller-owned conversation, newest-first, bounded by count and char budget."""
    window = limit if limit is not None else settings.chat_recent_history_messages
    stmt = (
        select(ChatMessage)
        .join(ChatConversation, ChatConversation.id == ChatMessage.conversation_id)
        .where(
            ChatMessage.conversation_id == conversation_id,
            ChatConversation.user_id == user_id,
        )
        .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
        .limit(window)
    )
    if exclude_message_id is not None:
        stmt = stmt.where(ChatMessage.id != exclude_message_id)
    newest_first = list((await db.execute(stmt)).scalars().all())

    collected: list[RecentConversationMessage] = []
    total_chars = 0
    msg_limit = min(settings.chat_recent_history_message_chars, MAX_HISTORY_MESSAGE_CHARS)
    max_total_chars = MAX_WORKSPACE_RECENT_HISTORY_CHARS

    for message in newest_first:
        if message.role not in {"user", "assistant"}:
            continue
        bounded = _bounded_content(message.content, msg_limit)
        if total_chars + len(bounded) > max_total_chars:
            break
        total_chars += len(bounded)
        collected.append(
            RecentConversationMessage(
                message_id=message.id,
                role=message.role,
                content=bounded,
            )
        )

    history = list(reversed(collected))
    assert exclude_message_id is None or all(item.message_id != exclude_message_id for item in history)
    return history


async def load_ticket_recent_history(
    db: AsyncSession,
    *,
    ticket_id: int,
    exclude_message_id: int | None,
    limit: int | None = None,
) -> list[RecentConversationMessage]:
    """Load bounded user/AI/technician turns from one ticket in chronology with char budget."""
    window = limit if limit is not None else settings.ticket_recent_history_messages
    stmt = (
        select(TicketMessage)
        .where(
            TicketMessage.ticket_id == ticket_id,
            TicketMessage.sender_type.in_(_CONVERSATIONAL_TICKET_SENDERS),
        )
        .order_by(TicketMessage.created_at.desc(), TicketMessage.id.desc())
        .limit(window)
    )
    if exclude_message_id is not None:
        stmt = stmt.where(TicketMessage.id != exclude_message_id)
    newest_first = list((await db.execute(stmt)).scalars().all())

    collected: list[RecentConversationMessage] = []
    total_chars = 0
    msg_limit = min(settings.ticket_recent_history_message_chars, MAX_HISTORY_MESSAGE_CHARS)
    max_total_chars = MAX_TICKET_RECENT_HISTORY_CHARS

    for message in newest_first:
        bounded = _bounded_content(message.content, msg_limit)
        if total_chars + len(bounded) > max_total_chars:
            break
        total_chars += len(bounded)
        collected.append(
            RecentConversationMessage(
                message_id=str(message.id),
                role=message.sender_type.value,
                content=bounded,
            )
        )

    history = list(reversed(collected))
    assert exclude_message_id is None or all(item.message_id != str(exclude_message_id) for item in history)
    return history


def format_recent_history(history: Iterable[RecentConversationMessage], *, label: str) -> str:
    """Render a role-aware transcript with an explicit untrusted-data boundary."""
    messages = list(history)
    if not messages:
        return "No recent conversation messages."
    display_role = {"user": "User", "assistant": "Assistant", "agent": "AI", "technician": "Technician"}
    lines = [f"[RECENT {label} — UNTRUSTED DATA]"]
    lines.extend(f"{display_role.get(item.role, item.role)}: {item.content}" for item in messages)
    lines.append(f"[/RECENT {label}]")
    return "\n".join(lines)


def exclude_recent_history_from_episodic(
    evidence: Iterable[T], history: Iterable[RecentConversationMessage], *, current_message_id: int | None = None
) -> list[T]:
    """Avoid duplicate TicketMessage spans without mutating the Zero-Mem index."""
    excluded_ids = {item.message_id for item in history}
    if current_message_id is not None:
        excluded_ids.add(str(current_message_id))
    result: list[T] = []
    for item in evidence:
        provenance = getattr(item, "provenance", {}) or {}
        message_id = provenance.get("message_id")
        if message_id is not None and str(message_id) in excluded_ids:
            continue
        result.append(item)
    return result
