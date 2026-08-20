"""Closed-topic, privacy-safe telemetry for retrieval outcome gap analysis.

This module intentionally accepts a query only long enough to map it to a
closed taxonomy.  The query is never placed in a model, log payload, or event.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.models.knowledge_gap import KnowledgeGapEvent
from src.observability.tracing import current_trace_id, set_current_attributes
from src.services.web_research_service import ResearchResult

settings = get_settings()

_PORT_403 = re.compile(r"\b(?:cong|port|tcp\s+port|udp\s+port)\s*403\b", re.I)
_HTTP_403 = re.compile(r"\b(?:http\s*(?:status\s*)?403|403\s*forbidden|(?:web|browser|api)\b.{0,32}\b403)\b", re.I)

# These values are closed labels, not user-derived strings.
_TOPIC_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("network.connection_refused", ("connection refused", "ket noi bi tu choi")),
    ("network.service_not_listening", ("service not listening", "dich vu khong lang nghe")),
    ("network.port_timeout", ("port timeout", "timeout cong", "timeout port")),
    ("network.firewall_acl", ("firewall", "tuong lua", " acl", " nat")),
    ("vpn.internal_resource_access", ("vpn connected", "vpn ket noi", "tai nguyen noi bo", "internal resource")),
    ("vpn.forticlient", ("forticlient", "fortigate", "ssl-vpn", "ssl vpn")),
    ("routing", ("split tunnel", "split-tunnel", "routing", "route ", "dinh tuyen")),
    ("dns", ("dns", "name resolution", "phan giai ten mien")),
    ("dhcp", ("dhcp", "cap phat ip")),
    ("proxy", ("proxy", " pac ", "waf")),
    ("network.smb_network_drive", ("network drive", "o dia mang", "file share", "smb", "dfs")),
    ("network.tcp_connectivity", ("tcp", "udp", "cong ", "port ", "80/443")),
)

_WEB_RESEARCH_ATTEMPT_REASONS = {
    "internal_kb_empty",
    "low_rag_confidence",
    "user_requested_current_information",
    "vendor_documentation_can_improve_answer",
    "search_provider_unavailable",
    "sensitive_or_empty_search_query",
    "web_research_disabled",
}


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).casefold()
    return "".join(char for char in normalized if not unicodedata.combining(char)).replace("đ", "d")


def normalize_knowledge_topic(query: str) -> str:
    """Return one closed taxonomy label; never return user-supplied content."""
    text = _fold(query or "")
    # Explicit physical/network port wording wins over a bare status-code token.
    if _PORT_403.search(text):
        return "network.tcp_connectivity"
    if _HTTP_403.search(text):
        return "http.status_403"
    for topic, markers in _TOPIC_RULES:
        if any(marker in text for marker in markers):
            return topic
    return "general.it_support"


@dataclass(frozen=True)
class EvidenceCounts:
    evidence_count: int
    internal: int
    official: int
    historical: int
    episodic: int


def count_evidence(rag_docs: list[dict], *, episodic_evidence_count: int = 0) -> EvidenceCounts:
    internal = official = historical = 0
    for doc in rag_docs:
        source = str((doc.get("metadata") or {}).get("source") or "")
        if source in {"internal_curated_kb", "approved_internal_source"}:
            internal += 1
        elif source == "official_web_documentation":
            official += 1
        elif source == "historical_resolved_ticket":
            historical += 1
    return EvidenceCounts(
        evidence_count=len(rag_docs) + episodic_evidence_count,
        internal=internal,
        official=official,
        historical=historical,
        episodic=episodic_evidence_count,
    )


def web_research_attempted(research: ResearchResult | None) -> bool:
    return bool(research and (research.triggered or research.reason in _WEB_RESEARCH_ATTEMPT_REASONS))


async def record_retrieval_outcome(
    db: AsyncSession,
    *,
    surface: str,
    transport: str,
    tenant_scope: str,
    department_scope: str | None,
    query: str,
    retrieval_required: bool,
    retrieval_strategy: str,
    rag_docs: list[dict],
    top_score: float | None,
    insufficient_evidence: bool,
    research: ResearchResult | None = None,
    web_research_provenance_used: bool = False,
    episodic_evidence_count: int = 0,
    hitl_or_escalation: bool = False,
) -> KnowledgeGapEvent | None:
    """Persist one eligible outcome without retaining the query or user identity."""
    if not retrieval_required:
        return None

    counts = count_evidence(rag_docs, episodic_evidence_count=episodic_evidence_count)
    no_evidence = counts.evidence_count == 0
    low_score = top_score is not None and top_score < settings.rag_min_relevance_score
    research_attempted = web_research_attempted(research)
    is_gap = bool(no_evidence or low_score or insufficient_evidence or research_attempted or hitl_or_escalation)
    event = KnowledgeGapEvent(
        correlation_id=(current_trace_id() or uuid4().hex)[:64],
        surface=surface,
        transport=transport,
        tenant_scope=(tenant_scope or "unknown")[:64],
        department_scope=(department_scope or "")[:100] or None,
        normalized_topic=normalize_knowledge_topic(query),
        retrieval_required=True,
        retrieval_strategy=retrieval_strategy[:64],
        top_score=top_score,
        evidence_count=counts.evidence_count,
        internal_evidence_count=counts.internal,
        official_evidence_count=counts.official,
        historical_evidence_count=counts.historical,
        episodic_evidence_count=counts.episodic,
        no_evidence=no_evidence,
        insufficient_evidence=insufficient_evidence,
        web_research_triggered=research_attempted,
        web_research_provider=(settings.web_search_provider if research_attempted else None),
        web_research_result_count=len(research.sources) if research else 0,
        web_research_rejected_result_count=research.rejected_result_count if research else 0,
        web_research_failure_category=research.failure_category if research else None,
        web_research_provenance_used=web_research_provenance_used,
        hitl_or_escalation=hitl_or_escalation,
        is_knowledge_gap=is_gap,
    )
    db.add(event)
    await db.flush()
    set_current_attributes({"helpdesk.gap.detected": is_gap, "helpdesk.gap.topic": event.normalized_topic})
    return event
