"""Safe external knowledge retrieval for the Help Desk assistant.

Web pages are deliberately treated as untrusted data.  This module only sends a
redacted version of the user's question to a search provider, never ticket
content, ACL context, or internal RAG text.  It never follows instructions from
search snippets and drops snippets that look like indirect prompt injection.
"""
from __future__ import annotations

import html
import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from typing import Protocol
from urllib.parse import parse_qs, unquote, urlparse

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.guardrails.rag_guardrails import detect_document_injection
from src.models.audit_log import AuditAction
from src.models.web_research import WebResearchRun, WebResearchSource
from src.services.ticket_service import write_audit_log

logger = logging.getLogger(__name__)
settings = get_settings()

OFFICIAL_DOMAINS = (
    "microsoft.com", "microsoftonline.com", "office.com", "github.com",
    "cisco.com", "apple.com", "google.com", "cloudflare.com", "aws.amazon.com",
    "docs.vmware.com", "redhat.com", "ubuntu.com", "mozilla.org", "zoom.us",
    "atlassian.com", "slack.com", "okta.com", "fortinet.com", "paloaltonetworks.com",
)
FRESHNESS_MARKERS = (
    "latest", "newest", "current", "today", "recent", "update", "updated", "version",
    "moi nhat", "mới nhất", "hien nay", "hiện nay", "cap nhat", "cập nhật", "phien ban", "phiên bản",
)
VENDOR_MARKERS = (
    "microsoft", "windows", "m365", "office", "outlook", "azure", "cisco", "apple",
    "google", "chrome", "aws", "vmware", "linux", "ubuntu", "fortinet", "okta",
)
TICKET_RESEARCH_PRODUCT_MARKERS = (
    "adobe", "creative cloud", "forticlient", "fortigate", "teams", "zoom",
    "outlook", "office", "m365", "microsoft", "windows", "gmail", "chrome",
    "sap", "erp", "vpn", "wifi", "wi-fi", "printer", "máy in", "may in",
)
ERROR_CODE_MARKER = re.compile(r"\b(?:0x[0-9a-f]{4,}|err(?:or)?[-_ ]?\d{2,}|[a-z]{2,12}-\d{3,})\b", re.I)
POLICY_REQUIRED = re.compile(r"\b(must|required|mandatory|bắt buộc|phải|không được)\b", re.I)
POLICY_NEGATED = re.compile(r"\b(not required|optional|never|required? not|không bắt buộc|không cần|được phép)\b", re.I)
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\d .()\-]{7,}\d)(?!\w)")
CARD_RE = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
SECRET_RE = re.compile(
    r"\b(?:api[_ -]?key|access[_ -]?token|secret|password|passwd|authorization)\s*[:=]\s*[^\s,;]+",
    re.I,
)
INTERNAL_DATA_RE = re.compile(
    r"\b(?:confidential|internal[ -]?only|restricted|do not share|ticket\s*(?:#|id)?\s*(?:inc|req)-?\d+|"
    r"nội bộ|mật|không chia sẻ|tuyệt mật)\b|\b[a-z0-9][a-z0-9.-]*\.(?:local|internal)\b",
    re.I,
)


@dataclass(frozen=True)
class ResearchSource:
    title: str
    url: str
    domain: str
    snippet: str
    content: str
    retrieved_at: datetime
    source_type: str
    relevance_score: float


@dataclass(frozen=True)
class ResearchResult:
    triggered: bool
    reason: str
    query: str | None
    sources: list[ResearchSource]


class SearchProvider(Protocol):
    async def search(self, query: str, limit: int) -> list[ResearchSource]: ...


class _DuckDuckGoParser(HTMLParser):
    """Small dependency-free parser for the stable DuckDuckGo HTML result shape."""

    def __init__(self) -> None:
        super().__init__()
        self.results: list[dict[str, str]] = []
        self._active: str | None = None
        self._href = ""
        self._chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        classes = attributes.get("class") or ""
        if tag == "a" and "result__a" in classes:
            self._active, self._href, self._chunks = "title", attributes.get("href") or "", []
        elif "result__snippet" in classes:
            self._active, self._chunks = "snippet", []

    def handle_data(self, data: str) -> None:
        if self._active:
            self._chunks.append(data)

    def handle_endtag(self, tag: str) -> None:
        if not self._active or tag not in {"a", "div", "span"}:
            return
        value = " ".join("".join(self._chunks).split())
        if self._active == "title" and value:
            self.results.append({"title": value, "href": self._href, "snippet": ""})
        elif self._active == "snippet" and value and self.results:
            self.results[-1]["snippet"] = value
        self._active = None
        self._chunks = []


def _unwrap_result_url(url: str) -> str:
    parsed = urlparse(html.unescape(url))
    if parsed.netloc.endswith("duckduckgo.com") and parsed.path.startswith("/l/"):
        target = parse_qs(parsed.query).get("uddg", [""])[0]
        return unquote(target)
    return url


def _valid_http_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def classify_source_type(domain: str) -> str:
    clean_domain = domain.lower().removeprefix("www.")
    if any(clean_domain == item or clean_domain.endswith(f".{item}") for item in OFFICIAL_DOMAINS):
        return "OFFICIAL"
    return "WEB"


def sanitize_search_query(message: str) -> str | None:
    """Remove PII/secrets before an external request; return None if nothing useful remains."""
    # A declared confidential/ticket payload is not safe to transform into a public search query.
    if INTERNAL_DATA_RE.search(message):
        return None
    sanitized = EMAIL_RE.sub("[redacted email]", message)
    sanitized = PHONE_RE.sub("[redacted phone]", sanitized)
    sanitized = CARD_RE.sub("[redacted number]", sanitized)
    sanitized = SECRET_RE.sub("[redacted secret]", sanitized)
    sanitized = re.sub(r"\s+", " ", sanitized).strip()
    if not sanitized or len(re.sub(r"\[redacted [^]]+\]", "", sanitized).strip()) < 4:
        return None
    return sanitized[:300]


def has_actionable_external_context(message: str) -> bool:
    """Whether a ticket has enough product/error detail for safe web research.

    A vague request such as "how do I install it" must ask for the application
    name instead of searching the public web for an arbitrary phrase.
    """
    normalized = message.casefold()
    return bool(ERROR_CODE_MARKER.search(normalized)) or any(
        marker in normalized for marker in TICKET_RESEARCH_PRODUCT_MARKERS
    )


def _needs_external_research(message: str, rag_docs: list[dict]) -> tuple[bool, str]:
    """Conservative decision gate: internal RAG wins when it is clearly sufficient."""
    normalized = message.casefold()
    best_score = max((float(doc.get("relevance_score", 0)) for doc in rag_docs), default=0.0)
    asks_fresh = any(marker in normalized for marker in FRESHNESS_MARKERS)
    asks_vendor = any(marker in normalized for marker in VENDOR_MARKERS)
    if not rag_docs:
        return True, "internal_kb_empty"
    if best_score < settings.web_research_min_rag_score:
        return True, "low_rag_confidence"
    if asks_fresh:
        return True, "user_requested_current_information"
    if asks_vendor and best_score < 0.82:
        return True, "vendor_documentation_can_improve_answer"
    return False, "internal_kb_sufficient"


def detect_internal_external_conflict(internal_docs: list[dict], external_sources: list[ResearchSource]) -> bool:
    """Flag an explicit policy polarity conflict; internal policy remains authoritative."""
    internal_text = " ".join(
        f"{doc.get('metadata', {}).get('title', '')} {doc.get('content', '')}" for doc in internal_docs
    )
    external_text = " ".join(f"{source.title} {source.snippet} {source.content}" for source in external_sources)
    if not internal_text or not external_text or not POLICY_REQUIRED.search(internal_text):
        return False
    return bool(POLICY_NEGATED.search(external_text))


def _is_untrusted_content_safe(source: ResearchSource) -> bool:
    # Search snippets are data, never instructions. Drop likely injection instead of forwarding it.
    scan = detect_document_injection(f"{source.title}\n{source.snippet}\n{source.content}")
    return not scan.get("detected", False)


class DuckDuckGoHtmlProvider:
    """No-key provider. Failures simply fall back to the internal KB response."""

    async def search(self, query: str, limit: int) -> list[ResearchSource]:
        timeout = httpx.Timeout(settings.web_research_timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers={"User-Agent": "HelpDeskResearch/1.0"}) as client:
            response = await client.get("https://html.duckduckgo.com/html/", params={"q": query})
            response.raise_for_status()
        parser = _DuckDuckGoParser()
        parser.feed(response.text)
        now = datetime.now(UTC)
        sources: list[ResearchSource] = []
        for rank, result in enumerate(parser.results):
            url = _unwrap_result_url(result["href"])
            if not _valid_http_url(url):
                continue
            domain = urlparse(url).netloc.lower().removeprefix("www.")
            sources.append(ResearchSource(
                title=result["title"][:500], url=url, domain=domain,
                snippet=result.get("snippet", "")[:2000], content=result.get("snippet", "")[:4000],
                retrieved_at=now, source_type=classify_source_type(domain),
                relevance_score=max(0.1, 1.0 - rank * 0.08),
            ))
            if len(sources) >= limit:
                break
        # Official vendor docs are ranked before generic web results.
        return sorted(sources, key=lambda item: (item.source_type != "OFFICIAL", -item.relevance_score))


def get_search_provider() -> SearchProvider | None:
    if not settings.web_research_enabled or settings.web_search_provider == "disabled":
        return None
    return DuckDuckGoHtmlProvider()


async def maybe_research_web(message: str, rag_docs: list[dict], provider: SearchProvider | None = None) -> ResearchResult:
    should_search, reason = _needs_external_research(message, rag_docs)
    if not should_search:
        return ResearchResult(False, reason, None, [])

    query = sanitize_search_query(message)
    if not query:
        return ResearchResult(False, "sensitive_or_empty_search_query", None, [])
    active_provider = provider or get_search_provider()
    if not active_provider:
        return ResearchResult(False, "web_research_disabled", query, [])

    try:
        raw_sources = await active_provider.search(query, settings.web_research_max_results)
    except Exception as exc:  # A failed external dependency must not block Help Desk service.
        logger.info("External research unavailable: %s", exc)
        return ResearchResult(False, "search_provider_unavailable", query, [])

    safe_sources = [source for source in raw_sources if _valid_http_url(source.url) and _is_untrusted_content_safe(source)]
    if len(safe_sources) != len(raw_sources):
        logger.warning("Dropped %d external results due to URL or indirect injection policy", len(raw_sources) - len(safe_sources))
    return ResearchResult(bool(safe_sources), reason, query, safe_sources)


async def persist_research_audit(
    db: AsyncSession,
    research: ResearchResult,
    user_id: int | None,
    ticket_id: int | None,
    confidence: float,
) -> WebResearchRun | None:
    """Persist every used URL and an audit event without storing original PII-bearing input."""
    if not research.triggered or not research.query:
        return None
    run = WebResearchRun(
        query=research.query,
        search_provider=settings.web_search_provider,
        user_id=user_id,
        ticket_id=ticket_id,
        confidence=confidence,
    )
    db.add(run)
    await db.flush()
    for source in research.sources:
        db.add(WebResearchSource(
            research_run_id=run.id, title=source.title, url=source.url, domain=source.domain,
            snippet=source.snippet, content=source.content, retrieved_at=source.retrieved_at,
            source_type=source.source_type, relevance_score=source.relevance_score,
        ))
    await write_audit_log(
        db=db,
        ticket_id=ticket_id,
        actor_id=user_id,
        actor_type="agent",
        action=AuditAction.WEB_RESEARCH_EXECUTED,
        description=f"External research executed via {settings.web_search_provider}",
        metadata={
            "query": research.query,
            "search_provider": settings.web_search_provider,
            "sources_used": [source.title for source in research.sources],
            "urls": [source.url for source in research.sources],
            "reason": research.reason,
        },
        confidence_score=confidence,
        model_used="external-research",
    )
    return run


def citation_source_payload(source: ResearchSource, citation_id: int) -> dict:
    """Only create a citation from a URL returned by the provider."""
    if not _valid_http_url(source.url):
        raise ValueError("Citation requires a retrieved http(s) URL")
    return {
        "id": citation_id,
        "title": source.title,
        "url": source.url,
        "domain": source.domain,
        "snippet": source.snippet,
        "source_type": source.source_type,
        "relevance_score": source.relevance_score,
        "retrieved_at": source.retrieved_at.isoformat(),
    }


def remove_hallucinated_citations(answer: str, citations: list[dict]) -> tuple[str, list[int]]:
    """Strip citation labels the model was not given; callers only render validated URLs."""
    valid_ids = {int(item["id"]) for item in citations}
    used_ids: list[int] = []

    def replace(match: re.Match[str]) -> str:
        value = int(match.group(1))
        if value not in valid_ids:
            return ""
        if value not in used_ids:
            used_ids.append(value)
        return f"[{value}]"

    return re.sub(r"\[(\d{1,3})\]", replace, answer), used_ids
