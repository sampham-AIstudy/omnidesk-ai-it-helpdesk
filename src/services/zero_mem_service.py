"""Production-oriented Zero-Mem for ticket and conversation history.

This module deliberately has no LLM imports.  It indexes only provenance and
observed entities, retrieves original ticket/message records through dense,
lexical and relational signals, then deterministically calibrates the result.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import time
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.models.episodic_memory import EpisodicMemoryEntity, EpisodicMemoryTrace
from src.models.ticket import Ticket
from src.models.ticket_message import TicketMessage
from src.models.user import User, UserRole
from src.services.rag_service import embed_query, get_episodic_memory_collection, scan_indirect_injection

logger = logging.getLogger(__name__)
settings = get_settings()

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_.-]{1,}|\b\d{1,3}(?:\.\d{1,3}){3}\b")
_ERROR_RE = re.compile(r"(?:error|err|code|ma loi|mã lỗi)\s*[:#-]?\s*([A-Za-z][A-Za-z0-9_-]{2,}|\d{3,8})", re.I)
_TICKET_RE = re.compile(r"\bINC-\d{8}-\d{4}\b|\bINC-\d+\b", re.I)
_TEMPORAL_RE = re.compile(r"\b(hom qua|hôm qua|truoc do|trước đó|luc nay|lúc nãy|gan day|gần đây|today|yesterday|previous|last|again)\b", re.I)
_RELATIONAL_RE = re.compile(r"\b(nao khac|nào khác|ai khac|ai khác|cung|cùng|lien quan|liên quan|tuong tu|tương tự|same|other|related|across)\b", re.I)
_STOPWORDS = {"the", "and", "for", "with", "from", "that", "this", "have", "you", "your", "toi", "minh", "khong", "duoc", "nhung", "mot", "cua", "van", "loi", "ticket", "help", "desk"}


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value).casefold()
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn").replace("đ", "d")


def _tokens(value: str) -> set[str]:
    return {token.casefold() for token in _TOKEN_RE.findall(_fold(value)) if token.casefold() not in _STOPWORDS}


def extract_entities(value: str) -> dict[str, str]:
    """Extract observed IT identifiers; no model-generated triples or inference."""
    entities: dict[str, str] = {}
    for ticket_id in _TICKET_RE.findall(value):
        entities[ticket_id.casefold()] = "TICKET"
    for error_code in _ERROR_RE.findall(_fold(value)):
        entities[error_code.casefold()] = "ERROR_CODE"
    for ip in re.findall(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", value):
        entities[ip] = "IP"
    for token in _tokens(value):
        if len(token) >= 3:
            entities.setdefault(token, "TERM")
    return entities


@dataclass(frozen=True)
class QueryProfile:
    keywords: set[str]
    entities: set[str]
    route: str  # relational | local_temporal
    temporal: bool
    ticket_boundary: int | None = None


@dataclass
class MemoryEvidence:
    trace_id: str
    ticket_id: int
    source_type: str
    speaker: str
    sequence_no: int
    timestamp: datetime | None
    text: str
    score: float = 0.0
    provenance: dict[str, object] = field(default_factory=dict)

    @property
    def title(self) -> str:
        return f"Ticket #{self.provenance.get('ticket_number', self.ticket_id)}"


def profile_query(query: str, ticket_id: int | None = None) -> QueryProfile:
    entities = set(extract_entities(query))
    temporal = bool(_TEMPORAL_RE.search(query))
    relational = bool(_RELATIONAL_RE.search(query)) or len(entities) >= 2
    return QueryProfile(_tokens(query), entities, "relational" if relational and not temporal else "local_temporal", temporal, ticket_id)


def _trace_id_for_ticket(ticket_id: int) -> str:
    return f"ticket:{ticket_id}:root"


def _trace_id_for_message(message_id: int) -> str:
    return f"message:{message_id}"


def _ticket_text(ticket: Ticket) -> str:
    parts = [ticket.title, ticket.description]
    if ticket.resolution_summary:
        parts.append(ticket.resolution_summary)
    elif ticket.suggested_solution:
        parts.append(ticket.suggested_solution)
    return "\n".join(part for part in parts if part)


async def _remove_trace_projection(db: AsyncSession, trace_id: str) -> None:
    """Remove every searchable projection while retaining the source transcript."""
    await db.execute(delete(EpisodicMemoryTrace).where(EpisodicMemoryTrace.trace_id == trace_id))
    await db.execute(delete(EpisodicMemoryEntity).where(EpisodicMemoryEntity.trace_id == trace_id))
    try:
        await db.execute(
            text("DELETE FROM episodic_memory_fts WHERE trace_id = :trace_id"),
            {"trace_id": trace_id},
        )
        await asyncio.to_thread(
            lambda: get_episodic_memory_collection().delete(ids=[trace_id])
        )
    except Exception as exc:
        logger.debug("Could not remove episodic vector/FTS trace %s: %s", trace_id, exc)


async def _upsert_trace(
    db: AsyncSession, *, trace_id: str, source_type: str, ticket: Ticket,
    message: TicketMessage | None, content: str, speaker: str, sequence_no: int,
    owner: User | None = None,
) -> None:
    # Do not assign/load the legacy Ticket.submitter relationship here: this
    # index is write-adjacent and must never mutate the authoritative ticket.
    # Keep injection payloads in the authoritative transcript for incident
    # investigation, but remove them from every searchable memory projection.
    if scan_indirect_injection(content):
        await _remove_trace_projection(db, trace_id)
        logger.warning("Skipped unsafe prompt-injection content from episodic memory: %s", trace_id)
        return
    submitter = owner or await db.get(User, ticket.submitter_id)
    if submitter is None:
        return
    existing = (await db.execute(select(EpisodicMemoryTrace).where(EpisodicMemoryTrace.trace_id == trace_id))).scalar_one_or_none()
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    values = {
        "source_type": source_type, "ticket_id": ticket.id, "message_id": message.id if message else None,
        "tenant_id": submitter.company_unit.value if hasattr(submitter.company_unit, "value") else str(submitter.company_unit),
        "department": submitter.department or "", "owner_user_id": ticket.submitter_id,
        "speaker": speaker, "sequence_no": sequence_no,
        "event_at": message.created_at if message else ticket.created_at, "content_hash": digest,
    }
    if existing is None:
        existing = EpisodicMemoryTrace(trace_id=trace_id, **values)
        db.add(existing)
    else:
        for name, value in values.items():
            setattr(existing, name, value)
    await db.flush()
    await db.execute(delete(EpisodicMemoryEntity).where(EpisodicMemoryEntity.trace_id == trace_id))
    db.add_all(EpisodicMemoryEntity(trace_id=trace_id, entity=entity, entity_type=entity_type) for entity, entity_type in extract_entities(content).items())
    # FTS is an optimization only.  Its content is a search index, never a source of record.
    try:
        await db.execute(text("DELETE FROM episodic_memory_fts WHERE trace_id = :trace_id"), {"trace_id": trace_id})
        await db.execute(text("INSERT INTO episodic_memory_fts(trace_id, tenant_id, department, owner_user_id, content) VALUES (:trace_id, :tenant_id, :department, :owner_user_id, :content)"), {**values, "trace_id": trace_id, "content": content})
    except Exception as exc:
        logger.debug("Episodic FTS index skipped: %s", exc)
    metadata = {"trace_id": trace_id, "ticket_id": ticket.id, "tenant_id": values["tenant_id"], "department": values["department"], "owner_user_id": ticket.submitter_id, "source_type": source_type, "sequence_no": sequence_no}
    await asyncio.to_thread(lambda: get_episodic_memory_collection().upsert(ids=[trace_id], documents=[content], embeddings=[embed_query(content)], metadatas=[metadata]))


async def index_ticket_trace(db: AsyncSession, ticket: Ticket, owner: User | None = None) -> None:
    """Index the original ticket report after it receives an id; zero LLM calls."""
    await _upsert_trace(db, trace_id=_trace_id_for_ticket(ticket.id), source_type="ticket", ticket=ticket, message=None, content=_ticket_text(ticket), speaker="user", sequence_no=0, owner=owner)


async def index_message_trace(db: AsyncSession, ticket: Ticket, message: TicketMessage) -> None:
    await _upsert_trace(db, trace_id=_trace_id_for_message(message.id), source_type="message", ticket=ticket, message=message, content=message.content, speaker=message.sender_type.value if hasattr(message.sender_type, "value") else str(message.sender_type), sequence_no=message.id)


async def index_message_by_id(db: AsyncSession, message: TicketMessage) -> None:
    """Index a message regardless of which ticket workflow created it."""
    ticket = (await db.execute(select(Ticket).where(Ticket.id == message.ticket_id))).scalar_one_or_none()
    if ticket is not None:
        await index_message_trace(db, ticket, message)


def _visible(trace: EpisodicMemoryTrace, user: User) -> bool:
    role = user.role.value if hasattr(user.role, "value") else str(user.role)
    tenant = user.company_unit.value if hasattr(user.company_unit, "value") else str(user.company_unit)
    if role == UserRole.ADMIN.value:
        return True
    if trace.tenant_id != tenant:
        return False
    if role == UserRole.EMPLOYEE.value:
        return trace.owner_user_id == user.id
    # Support personnel are limited to their department unless they are corporate.
    return tenant == "corporate" or trace.department == (user.department or "")


async def _fts_scores(db: AsyncSession, profile: QueryProfile, user: User) -> dict[str, float]:
    if not profile.keywords:
        return {}
    query = " OR ".join(sorted(profile.keywords)[:12])
    tenant = user.company_unit.value if hasattr(user.company_unit, "value") else str(user.company_unit)
    try:
        result = await db.execute(text("SELECT trace_id, -bm25(episodic_memory_fts) AS rank FROM episodic_memory_fts WHERE episodic_memory_fts MATCH :query AND tenant_id = :tenant LIMIT :limit"), {"query": query, "tenant": tenant, "limit": settings.zero_mem_primary_candidates * 3})
        rows = result.fetchall()
        raw = {str(row[0]): float(row[1]) for row in rows}
        maximum = max(raw.values(), default=0.0)
        return {key: (value / maximum if maximum else 0.0) for key, value in raw.items()}
    except Exception as exc:
        logger.debug("Episodic lexical retrieval unavailable: %s", exc)
        return {}


async def _graph_scores(db: AsyncSession, profile: QueryProfile) -> dict[str, float]:
    if not profile.entities:
        return {}
    result = await db.execute(select(EpisodicMemoryEntity.trace_id, EpisodicMemoryEntity.entity).where(EpisodicMemoryEntity.entity.in_(profile.entities)))
    counts: dict[str, float] = {}
    for trace_id, entity in result.fetchall():
        counts[trace_id] = counts.get(trace_id, 0.0) + (1.0 if entity in profile.entities else 0.0)
    maximum = max(counts.values(), default=0.0)
    return {trace_id: score / maximum for trace_id, score in counts.items()} if maximum else {}


def _dense_scores(query: str) -> dict[str, float]:
    try:
        result = get_episodic_memory_collection().query(query_embeddings=[embed_query(query)], n_results=settings.zero_mem_primary_candidates * 3, include=["metadatas", "distances"])
        metadata = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        return {str(item.get("trace_id")): max(0.0, 1.0 - float(distance)) for item, distance in zip(metadata, distances) if item.get("trace_id")}
    except Exception as exc:
        logger.debug("Episodic dense retrieval unavailable: %s", exc)
        return {}


async def _hydrate(db: AsyncSession, trace_ids: set[str], user: User) -> dict[str, MemoryEvidence]:
    if not trace_ids:
        return {}
    rows = (await db.execute(select(EpisodicMemoryTrace).where(EpisodicMemoryTrace.trace_id.in_(trace_ids)))).scalars().all()
    rows = [row for row in rows if _visible(row, user)]
    ticket_ids = {row.ticket_id for row in rows}
    tickets = (await db.execute(select(Ticket).where(Ticket.id.in_(ticket_ids)))).scalars().all() if ticket_ids else []
    by_ticket = {ticket.id: ticket for ticket in tickets}
    message_ids = {row.message_id for row in rows if row.message_id}
    messages = (await db.execute(select(TicketMessage).where(TicketMessage.id.in_(message_ids)))).scalars().all() if message_ids else []
    by_message = {message.id: message for message in messages}
    evidence: dict[str, MemoryEvidence] = {}
    for row in rows:
        ticket = by_ticket.get(row.ticket_id)
        if ticket is None:
            continue
        message = by_message.get(row.message_id) if row.message_id else None
        content = message.content if message else _ticket_text(ticket)
        if not content or scan_indirect_injection(content):
            continue
        evidence[row.trace_id] = MemoryEvidence(
            row.trace_id,
            row.ticket_id,
            row.source_type,
            row.speaker,
            row.sequence_no,
            row.event_at,
            content,
            provenance={
                "ticket_number": ticket.ticket_number,
                "owner_user_id": row.owner_user_id,
                "message_id": row.message_id,
            },
        )
    return evidence


def _normalize(scores: dict[str, float]) -> dict[str, float]:
    maximum = max(scores.values(), default=0.0)
    return {key: value / maximum for key, value in scores.items()} if maximum else {}


async def retrieve_episodic_evidence(db: AsyncSession, query: str, user: User, *, ticket_id: int | None = None) -> tuple[list[MemoryEvidence], dict[str, object]]:
    """Dual-view, ACL-first historical evidence retrieval. Never invokes an LLM."""
    started = time.perf_counter()
    if not settings.zero_mem_enabled:
        return [], {"enabled": False, "memory_llm_calls": 0, "memory_llm_tokens": 0}
    profile = profile_query(query, ticket_id)
    dense_task = asyncio.create_task(asyncio.to_thread(_dense_scores, query))
    lexical = await _fts_scores(db, profile, user)
    graph = await _graph_scores(db, profile)
    dense = await dense_task
    trace_ids = set(dense) | set(lexical) | set(graph)
    hydrated = await _hydrate(db, trace_ids, user)
    if ticket_id is not None:
        hydrated = {key: item for key, item in hydrated.items() if item.ticket_id == ticket_id}
    dense, lexical, graph = _normalize(dense), _normalize(lexical), _normalize(graph)
    primary = graph if profile.route == "relational" else {key: max(dense.get(key, 0.0), lexical.get(key, 0.0)) for key in trace_ids}
    secondary = {key: max(dense.get(key, 0.0), lexical.get(key, 0.0)) for key in trace_ids} if profile.route == "relational" else graph
    rho = settings.zero_mem_primary_view_weight
    ranked: list[MemoryEvidence] = []
    for trace_id, item in hydrated.items():
        item.score = rho * primary.get(trace_id, 0.0) + (1 - rho) * secondary.get(trace_id, 0.0)
        if profile.temporal and item.timestamp:
            item.score += 0.03
        ranked.append(item)
    ranked.sort(key=lambda item: item.score, reverse=True)
    main = ranked[:settings.zero_mem_final_evidence]
    # Evidence closure: add bounded local neighbours from the same ticket, not generated summaries.
    selected = {item.trace_id: item for item in main}
    if settings.zero_mem_neighbor_window and main:
        for item in main[:2]:
            if item.source_type != "message":
                continue
            neighbour_rows = (await db.execute(select(EpisodicMemoryTrace).where(EpisodicMemoryTrace.ticket_id == item.ticket_id, EpisodicMemoryTrace.source_type == "message", EpisodicMemoryTrace.sequence_no.between(item.sequence_no - settings.zero_mem_neighbor_window, item.sequence_no + settings.zero_mem_neighbor_window)))).scalars().all()
            neighbours = await _hydrate(db, {row.trace_id for row in neighbour_rows}, user)
            selected.update(neighbours)
    result = sorted(selected.values(), key=lambda item: (item.score, item.timestamp.timestamp() if item.timestamp else 0.0), reverse=True)[:settings.zero_mem_final_evidence + settings.zero_mem_neighbor_window * 2]
    metrics = {"enabled": True, "route": profile.route, "memory_candidates_count": len(trace_ids), "evidence_final_count": len(result), "memory_retrieval_latency_ms": round((time.perf_counter() - started) * 1000, 2), "memory_llm_calls": 0, "memory_llm_tokens": 0}
    return result, metrics


def evidence_context(evidence: list[MemoryEvidence]) -> str:
    """Bounded, provenance-labelled original spans for the final QA reader."""
    if not evidence:
        return "No authorized episodic evidence found."
    return "\n\n".join(f"[H{index}] {item.title}; source={item.source_type}; speaker={item.speaker}; time={item.timestamp}\n{item.text[:1200]}" for index, item in enumerate(evidence, start=1))


async def rebuild_episodic_memory_index(db: AsyncSession) -> int:
    """Backfill existing history without LLM calls; intended for startup/CLI use."""
    tickets = (await db.execute(select(Ticket))).scalars().all()
    messages = (await db.execute(select(TicketMessage))).scalars().all()
    unsafe_ticket_ids = {
        message.ticket_id
        for message in messages
        if scan_indirect_injection(message.content)
    }
    unsafe_ticket_ids.update(
        ticket.id for ticket in tickets if scan_indirect_injection(_ticket_text(ticket))
    )
    for ticket in tickets:
        if ticket.id in unsafe_ticket_ids:
            await _remove_trace_projection(db, _trace_id_for_ticket(ticket.id))
        else:
            await index_ticket_trace(db, ticket)
    for message in messages:
        if message.ticket_id in unsafe_ticket_ids:
            await _remove_trace_projection(db, _trace_id_for_message(message.id))
        else:
            await index_message_by_id(db, message)
    logger.info(
        "Zero-Mem episodic index synchronized: %d tickets, %d messages; quarantined %d ticket(s)",
        len(tickets),
        len(messages),
        len(unsafe_ticket_ids),
    )
    return len(tickets) + len(messages)


async def audit_memory_retrieval(db: AsyncSession, *, user_id: int, ticket_id: int | None, metrics: dict[str, object]) -> None:
    """Persist token-free retrieval telemetry without recording raw query text."""
    if not metrics.get("evidence_final_count"):
        return
    from src.models.audit_log import AuditAction
    from src.services.ticket_service import write_audit_log
    await write_audit_log(
        db=db, ticket_id=ticket_id, actor_id=user_id, actor_type="agent",
        action=AuditAction.MEMORY_RETRIEVED,
        description="Zero-Mem retrieved authorized episodic evidence",
        metadata=metrics,
    )
