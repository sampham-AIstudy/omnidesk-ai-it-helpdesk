"""Semantic duplicate-ticket detection built on the existing Chroma embeddings.

This service deliberately provides suggestions, never a rejection. Tenant filtering
is applied again after vector retrieval because vector stores are not an authority
for access control.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from difflib import SequenceMatcher

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.config import get_settings
from src.models.audit_log import AuditAction, AuditLog
from src.models.ticket import Ticket, TicketStatus
from src.models.user import User
from src.services.rag_service import embed_query_for_collection, get_ticket_duplicate_collection
from src.services.ticket_service import write_audit_log

logger = logging.getLogger(__name__)
settings = get_settings()
embed_query = embed_query_for_collection

ACTIVE_STATUSES = {
    TicketStatus.OPEN, TicketStatus.CLASSIFYING, TicketStatus.NEEDS_CLARIFICATION,
    TicketStatus.PENDING_HITL, TicketStatus.IN_PROGRESS, TicketStatus.WAITING_FOR_AGENT,
    TicketStatus.HUMAN_ACTIVE, TicketStatus.PENDING_CLOSURE, TicketStatus.ESCALATED,
    TicketStatus.REOPENED,
}
RESOLVED_STATUSES = {TicketStatus.RESOLVED, TicketStatus.CLOSED}
ERROR_CODE_RE = re.compile(r"(?:error|err|code|mã lỗi|ma loi)\s*[:#-]?\s*([A-Z][A-Z0-9_-]{2,})", re.I)
SERVICE_RE = re.compile(r"\[Hệ Thống / Dịch Vụ:\s*([^\]]+)\]|\[System / Service:\s*([^\]]+)\]", re.I)
DETAIL_RE = re.compile(r"---\s*(?:MÔ TẢ CHI TIẾT SỰ CỐ|CHI TIẾT SỰ CỐ)\s*---\s*(.*)$", re.I | re.S)
ENTITY_STOPWORDS = {"and", "the", "for", "with", "from", "that", "this", "khong", "không", "duoc", "được", "cua", "của", "voi", "với", "toi", "tôi", "may", "máy", "loi", "lỗi", "help", "ticket"}


class DuplicateClass:
    EXACT = "EXACT_DUPLICATE"
    SEMANTIC = "SEMANTIC_DUPLICATE"
    POSSIBLE = "POSSIBLE_DUPLICATE"
    NOT = "NOT_DUPLICATE"


@dataclass(frozen=True)
class DuplicateMatch:
    ticket: Ticket
    classification: str
    score: float
    method: str
    title_score: float
    semantic_score: float
    is_active: bool
    is_resolved: bool
    solution: str | None


@dataclass(frozen=True)
class DuplicateCheck:
    normalized_title: str
    normalized_description: str
    matches: list[DuplicateMatch]
    same_user_repeat_count: int
    shared_incident_signal: bool

    @property
    def primary(self) -> DuplicateMatch | None:
        return self.matches[0] if self.matches else None


def normalize_ticket_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).casefold()
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    normalized = normalized.replace("đ", "d")
    normalized = re.sub(r"[^\w\s.-]", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def ticket_fingerprint(title: str, description: str) -> str:
    return hashlib.sha256(f"{normalize_ticket_text(title)}\n{normalize_ticket_text(description)}".encode()).hexdigest()


def _extract_error_codes(value: str) -> set[str]:
    return {match.upper() for match in ERROR_CODE_RE.findall(value)}


def _extract_service(title: str, description: str) -> str:
    match = SERVICE_RE.search(description)
    if match:
        return normalize_ticket_text(next(item for item in match.groups() if item is not None))[:160]
    marker = re.match(r"\[([^\]]+)\]", title.strip())
    return normalize_ticket_text(marker.group(1) if marker else "")[:160]


def _entities(value: str) -> set[str]:
    return {
        token for token in re.findall(r"[\w.-]{3,}", normalize_ticket_text(value))
        if token not in ENTITY_STOPWORDS and not token.isdigit()
    }


def _reported_symptoms(value: str) -> str:
    """Use the user's free-text symptom, not shared form metadata, for duplicate checks."""
    match = DETAIL_RE.search(value)
    return normalize_ticket_text(match.group(1) if match else value)


def _has_specific_symptom_match(title: str, description: str, ticket: Ticket, title_score: float) -> bool:
    """Reject broad infrastructure matches that do not share an actual symptom."""
    incoming_errors = _extract_error_codes(f"{title} {description}")
    existing_errors = _extract_error_codes(f"{ticket.title} {ticket.description}")
    if incoming_errors and existing_errors and incoming_errors & existing_errors:
        return True

    incoming_symptoms = _entities(_reported_symptoms(description))
    existing_symptoms = _entities(_reported_symptoms(ticket.description))
    if incoming_symptoms and existing_symptoms:
        overlap = len(incoming_symptoms & existing_symptoms) / max(1, len(incoming_symptoms | existing_symptoms))
        if overlap >= 0.12:
            return True

    # A descriptive title can establish a match when either form lacks a useful symptom field.
    return title_score >= 0.78 and (not incoming_symptoms or not existing_symptoms)


def _same_tenant(metadata: dict, user: User) -> bool:
    company = user.company_unit.value if hasattr(user.company_unit, "value") else str(user.company_unit)
    department = user.department or ""
    return metadata.get("company_unit") == company and metadata.get("department", "") == department


def _time_score(created_at: datetime | None) -> float:
    if not created_at:
        return 0.0
    now = datetime.now(UTC)
    created = created_at if created_at.tzinfo else created_at.replace(tzinfo=UTC)
    hours = max(0.0, (now - created).total_seconds() / 3600)
    if hours <= 24:
        return 1.0
    if hours <= 24 * 7:
        return 0.55
    if hours <= 24 * 30:
        return 0.25
    return 0.08


def _score_candidate(title: str, description: str, ticket: Ticket, semantic_score: float) -> tuple[float, str, float]:
    normalized_title = normalize_ticket_text(title)
    normalized_description = normalize_ticket_text(description)
    old_title = normalize_ticket_text(ticket.title)
    old_description = normalize_ticket_text(ticket.description)
    if normalized_title == old_title and normalized_description == old_description:
        return 1.0, "exact_normalized_payload", 1.0

    title_score = SequenceMatcher(None, normalized_title, old_title).ratio()
    service_score = float(_extract_service(title, description) == _extract_service(ticket.title, ticket.description) and bool(_extract_service(title, description)))
    incoming_errors, existing_errors = _extract_error_codes(f"{title} {description}"), _extract_error_codes(f"{ticket.title} {ticket.description}")
    error_score = float(bool(incoming_errors & existing_errors)) if incoming_errors and existing_errors else 0.0
    incoming_entities, existing_entities = _entities(f"{title} {description}"), _entities(f"{ticket.title} {ticket.description}")
    entity_score = len(incoming_entities & existing_entities) / max(1, len(incoming_entities | existing_entities))
    category_score = float(bool(ticket.category) and bool(_extract_service(title, description)) and service_score > 0)
    if not _has_specific_symptom_match(title, description, ticket, title_score):
        return 0.0, "insufficient_symptom_overlap", title_score
    score = min(1.0, 0.60 * semantic_score + 0.18 * title_score + 0.08 * service_score + 0.06 * error_score + 0.05 * entity_score + 0.02 * category_score + 0.01 * _time_score(ticket.created_at))
    return score, "semantic_vector_hybrid", title_score


def classify_duplicate(score: float, exact: bool = False) -> str:
    if exact:
        return DuplicateClass.EXACT
    if score >= settings.duplicate_high_threshold:
        return DuplicateClass.SEMANTIC
    if score >= settings.duplicate_possible_threshold:
        return DuplicateClass.POSSIBLE
    return DuplicateClass.NOT


def _index_payload(ticket: Ticket, user: User | None = None) -> tuple[str, str, dict]:
    submitter = user or ticket.submitter
    company = submitter.company_unit.value if hasattr(submitter.company_unit, "value") else str(submitter.company_unit)
    return (
        f"ticket-{ticket.id}",
        f"{ticket.title}\n{ticket.description}",
        {
            "ticket_id": ticket.id,
            "company_unit": company,
            "department": submitter.department or "",
            "submitter_id": ticket.submitter_id,
            "status": ticket.status.value if hasattr(ticket.status, "value") else str(ticket.status),
            "category": ticket.category.value if ticket.category else "",
            "service": _extract_service(ticket.title, ticket.description),
            "fingerprint": ticket_fingerprint(ticket.title, ticket.description),
        },
    )


def index_ticket_for_duplicate_detection(ticket: Ticket, user: User | None = None) -> None:
    """Upsert a ticket using the existing RAG embedding backend."""
    if user is None and not ticket.submitter:
        raise ValueError("Ticket submitter is required to index duplicate metadata")
    doc_id, document, metadata = _index_payload(ticket, user)
    collection = get_ticket_duplicate_collection()
    collection.upsert(
        ids=[doc_id], documents=[document],
        embeddings=[embed_query_for_collection(document, collection)], metadatas=[metadata]
    )


async def rebuild_ticket_duplicate_index(db: AsyncSession) -> int:
    """Backfill legacy tickets at startup; no LLM/RAG invocation is made."""
    result = await db.execute(select(Ticket).options(selectinload(Ticket.submitter)))
    tickets = result.scalars().all()
    if not tickets:
        return 0
    await asyncio.to_thread(lambda: [index_ticket_for_duplicate_detection(ticket) for ticket in tickets])
    logger.info("Duplicate ticket index synchronized: %d tickets", len(tickets))
    return len(tickets)


async def check_duplicate_tickets(db: AsyncSession, title: str, description: str, user: User) -> DuplicateCheck:
    """Suggest only the requester's own active tickets with a matching symptom."""
    query_text = f"{title}\n{description}"
    normalized_title, normalized_description = normalize_ticket_text(title), normalize_ticket_text(description)
    try:
        collection = get_ticket_duplicate_collection()
        result = await asyncio.to_thread(
            lambda: collection.query(
                query_embeddings=[embed_query_for_collection(query_text, collection)],
                n_results=settings.duplicate_search_candidates,
                include=["metadatas", "distances"],
            )
        )
        metadata_rows = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
    except Exception as exc:
        logger.warning("Duplicate semantic lookup unavailable: %s", exc)
        metadata_rows, distances = [], []

    candidate_ids = [int(item["ticket_id"]) for item in metadata_rows if _same_tenant(item, user) and item.get("ticket_id")]
    tickets_by_id: dict[int, Ticket] = {}
    if candidate_ids:
        loaded = await db.execute(select(Ticket).where(Ticket.id.in_(candidate_ids)))
        tickets_by_id = {ticket.id: ticket for ticket in loaded.scalars().all()}

    matches: list[DuplicateMatch] = []
    for metadata, distance in zip(metadata_rows, distances):
        if not _same_tenant(metadata, user):
            continue
        ticket = tickets_by_id.get(int(metadata.get("ticket_id", 0)))
        if not ticket or ticket.submitter_id != user.id:
            continue
        semantic_score = max(0.0, 1.0 - float(distance))
        score, method, title_score = _score_candidate(title, description, ticket, semantic_score)
        exact = ticket_fingerprint(title, description) == metadata.get("fingerprint")
        classification = classify_duplicate(score, exact=exact)
        if classification == DuplicateClass.NOT:
            continue
        status = TicketStatus(ticket.status)
        if status not in ACTIVE_STATUSES:
            continue
        matches.append(DuplicateMatch(
            ticket=ticket, classification=classification, score=score, method=method,
            title_score=title_score, semantic_score=semantic_score, is_active=status in ACTIVE_STATUSES,
            is_resolved=status in RESOLVED_STATUSES,
            solution=ticket.resolution_summary or ticket.suggested_solution,
        ))
    matches.sort(key=lambda item: item.score, reverse=True)

    since = datetime.now(UTC) - timedelta(minutes=settings.duplicate_spam_window_minutes)
    recent = await db.execute(select(Ticket).where(Ticket.submitter_id == user.id, Ticket.created_at >= since))
    same_user_repeat_count = sum(ticket_fingerprint(title, description) == ticket_fingerprint(item.title, item.description) for item in recent.scalars())
    shared_incident_signal = False
    return DuplicateCheck(normalized_title, normalized_description, matches[:2], same_user_repeat_count, shared_incident_signal)


async def audit_duplicate_decision(db: AsyncSession, check: DuplicateCheck, user: User, ticket_id: int | None = None, action: AuditAction = AuditAction.DUPLICATE_DETECTED) -> None:
    primary = check.primary
    await write_audit_log(
        db=db, ticket_id=ticket_id, actor_id=user.id, actor_type="user", action=action,
        description="Semantic duplicate ticket decision",
        metadata={
            "classification": primary.classification if primary else DuplicateClass.NOT,
            "score": round(primary.score, 4) if primary else 0.0,
            "method": primary.method if primary else "semantic_vector_hybrid",
            "matched_ticket_ids": [match.ticket.id for match in check.matches],
            "same_user_repeat_count": check.same_user_repeat_count,
            "shared_incident_signal": check.shared_incident_signal,
        },
        confidence_score=primary.score if primary else 0.0,
        model_used="chroma-hybrid-duplicate-detection",
    )


async def duplicate_metrics(db: AsyncSession) -> dict[str, float | int]:
    """Derive dashboard metrics from immutable duplicate audit events."""
    result = await db.execute(select(AuditLog).where(AuditLog.action.in_([
        AuditAction.DUPLICATE_DETECTED, AuditAction.DUPLICATE_PREVENTED, AuditAction.DUPLICATE_CONFIRMED,
        AuditAction.DUPLICATE_FALSE_POSITIVE,
    ])))
    logs = result.scalars().all()
    detection_logs = [log for log in logs if log.action == AuditAction.DUPLICATE_DETECTED]
    checks = len(detection_logs)
    detected = 0
    for log in detection_logs:
        try:
            if json.loads(log.metadata_json or "{}").get("classification") != DuplicateClass.NOT:
                detected += 1
        except json.JSONDecodeError:
            continue
    prevented = sum(log.action == AuditAction.DUPLICATE_PREVENTED for log in logs)
    confirmed = sum(log.action == AuditAction.DUPLICATE_CONFIRMED for log in logs)
    false_positives = sum(log.action == AuditAction.DUPLICATE_FALSE_POSITIVE for log in logs)
    return {
        "duplicate_detection_rate": round(detected / max(1, checks), 4),
        "duplicate_prevented_count": prevented,
        "duplicate_false_positive_rate": round(false_positives / max(1, detected), 4),
        "existing_solution_reuse_rate": round(prevented / max(1, detected), 4),
        "tickets_saved": prevented,
        "estimated_llm_cost_saved": round(prevented * 0.004, 4),
        "duplicate_confirmed_count": confirmed,
    }
