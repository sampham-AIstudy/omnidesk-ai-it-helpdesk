"""Safe external knowledge retrieval for the Help Desk assistant.

Web pages are deliberately treated as untrusted data.  This module only sends a
redacted version of the user's question to a search provider, never ticket
content, ACL context, or internal RAG text.  It never follows instructions from
search snippets and drops snippets that look like indirect prompt injection.
"""
from __future__ import annotations

import asyncio
import html
import ipaddress
import logging
import re
import socket
import time
from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from html.parser import HTMLParser
from typing import Any, Protocol
from urllib.parse import parse_qs, unquote, urlparse

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.guardrails.rag_guardrails import detect_document_injection
from src.models.audit_log import AuditAction
from src.models.web_research import WebResearchRun, WebResearchSource
from src.services.reranker_service import rerank_candidates
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
EMPLOYEE_ID_RE = re.compile(
    r"\b(?:employee|staff|nhân\s*viên|ma\s*nhan\s*vien|mã\s*nhân\s*viên)\s*(?:id|code|mã)?\s*[:#-]?\s*[A-Z]{0,4}\d{4,}\b",
    re.I,
)
PERSON_LABEL_RE = re.compile(
    r"\b(?i:user|employee|staff|nhân\s*viên|nguoi\s*dung|người\s*dùng)\s*(?:(?i:name|tên)\s*)?[:=-]?\s*"
    r"(?:[A-ZÀ-Ỵ][A-Za-zÀ-ỹ'’-]*\s+){0,2}[A-ZÀ-Ỵ][A-Za-zÀ-ỹ'’-]*"
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
    raw_result_count: int = 0
    rejected_result_count: int = 0
    failure_category: str | None = None
    provider: str | None = None
    independent_domain_count: int = 0


class SearchProvider(Protocol):
    async def search(self, query: str, limit: int) -> list[ResearchSource]: ...

    @property
    def name(self) -> str: ...


class WebpageReader(Protocol):
    async def read(self, source: ResearchSource) -> ResearchSource | None: ...


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
    """Validate an outbound URL before it reaches the webpage reader.

    Search results are untrusted input too.  Reject credentials, unusual ports,
    localhost, and IP literals that are not globally routable; the reader also
    resolves host names immediately before requesting them.
    """
    try:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return False
        if parsed.username or parsed.password or parsed.port not in {None, 80, 443}:
            return False
        hostname = parsed.hostname.rstrip(".").casefold()
        if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith(".local"):
            return False
        try:
            return ipaddress.ip_address(hostname).is_global
        except ValueError:
            return True
    except ValueError:
        return False


async def _has_public_dns_target(hostname: str) -> bool:
    """Block common DNS-based SSRF targets before any HTTP request.

    A networking library ultimately resolves again when connecting, so this is
    a defence-in-depth check rather than a claim of DNS-rebinding immunity.
    Redirects are disabled in the reader to avoid a second, unchecked target.
    """
    try:
        addresses = await asyncio.to_thread(socket.getaddrinfo, hostname, None, type=socket.SOCK_STREAM)
        return bool(addresses) and all(ipaddress.ip_address(item[4][0]).is_global for item in addresses)
    except (OSError, ValueError):
        return False


def classify_source_type(domain: str) -> str:
    clean_domain = domain.lower().removeprefix("www.")
    if any(clean_domain == item or clean_domain.endswith(f".{item}") for item in OFFICIAL_DOMAINS):
        return "OFFICIAL"
    return "WEB"


def _diversity_domain(domain: str) -> str:
    """Collapse vendor subdomains before applying the source-diversity cap."""
    clean_domain = domain.lower().removeprefix("www.")
    for official in OFFICIAL_DOMAINS:
        if clean_domain == official or clean_domain.endswith(f".{official}"):
            return official
    labels = clean_domain.split(".")
    return ".".join(labels[-2:]) if len(labels) > 2 else clean_domain


def sanitize_search_query(message: str) -> str | None:
    """Remove PII/secrets before an external request; return None if nothing useful remains."""
    # A declared confidential/ticket payload is not safe to transform into a public search query.
    if INTERNAL_DATA_RE.search(message):
        return None
    # Reuse the canonical redactor so the outbound boundary gets the same IP,
    # national-ID and secret coverage as other product paths.  Keep the local
    # email expression because Presidio is intentionally optional at startup.
    from src.guardrails.output_guardrails import redact_secrets_and_pii

    sanitized = redact_secrets_and_pii(message).get("redacted", message)
    sanitized = EMAIL_RE.sub("[redacted email]", sanitized)
    sanitized = PHONE_RE.sub("[redacted phone]", sanitized)
    sanitized = CARD_RE.sub("[redacted number]", sanitized)
    sanitized = SECRET_RE.sub("[redacted secret]", sanitized)
    sanitized = EMPLOYEE_ID_RE.sub("[redacted employee id]", sanitized)
    sanitized = PERSON_LABEL_RE.sub("[redacted person]", sanitized)
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


def should_research_web(
    message: str, rag_docs: list[dict], *, insufficient_internal: bool = False
) -> tuple[bool, str]:
    """Conservative decision gate: internal RAG wins when it is clearly sufficient."""
    normalized = message.casefold()
    best_score = max((float(doc.get("relevance_score", 0)) for doc in rag_docs), default=0.0)
    asks_fresh = any(marker in normalized for marker in FRESHNESS_MARKERS)
    asks_vendor = any(marker in normalized for marker in VENDOR_MARKERS)
    if insufficient_internal:
        return True, "adaptive_insufficient_internal_evidence"
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


async def _get_with_retry(
    client: httpx.AsyncClient, url: str, *, params: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    """Bounded retry/backoff for transient provider and reader failures."""
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = await client.get(url, params=params, headers=headers)
            if response.status_code == 429 or response.status_code >= 500:
                raise httpx.HTTPStatusError("Transient HTTP response", request=response.request, response=response)
            response.raise_for_status()
            return response
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            last_error = exc
            if attempt == 2:
                raise
            await asyncio.sleep(0.15 * (2 ** attempt))
    raise last_error or RuntimeError("request failed")


async def _post_with_retry(
    client: httpx.AsyncClient, url: str, *, payload: dict[str, Any], headers: dict[str, str],
) -> httpx.Response:
    """Bounded retry/backoff for JSON search APIs using POST authentication."""
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code == 429 or response.status_code >= 500:
                raise httpx.HTTPStatusError("Transient HTTP response", request=response.request, response=response)
            response.raise_for_status()
            return response
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            last_error = exc
            if attempt == 2:
                raise
            await asyncio.sleep(0.15 * (2 ** attempt))
    raise last_error or RuntimeError("request failed")


async def _read_page_with_retry(client: httpx.AsyncClient, url: str, max_bytes: int) -> tuple[str, str]:
    """Read a bounded text response; never buffer an arbitrary web page."""
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            async with client.stream("GET", url) as response:
                if response.status_code == 429 or response.status_code >= 500:
                    raise httpx.HTTPStatusError("Transient HTTP response", request=response.request, response=response)
                response.raise_for_status()
                content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
                declared_size = response.headers.get("content-length")
                if content_type not in {"text/html", "text/plain", "application/xhtml+xml"}:
                    raise ValueError("unsupported page content type")
                if declared_size and int(declared_size) > max_bytes:
                    raise ValueError("web page exceeds read limit")
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > max_bytes:
                        raise ValueError("web page exceeds read limit")
                return content_type, bytes(body).decode(response.encoding or "utf-8", errors="replace")
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            last_error = exc
            if attempt == 2:
                raise
            await asyncio.sleep(0.15 * (2 ** attempt))
    raise last_error or RuntimeError("page request failed")


def _source_from_result(title: str, url: str, snippet: str, rank: int) -> ResearchSource | None:
    if not _valid_http_url(url):
        return None
    domain = (urlparse(url).hostname or "").lower().removeprefix("www.")
    return ResearchSource(
        title=title[:500] or domain,
        url=url,
        domain=domain,
        snippet=snippet[:2000],
        content="",
        retrieved_at=datetime.now(UTC),
        source_type=classify_source_type(domain),
        relevance_score=max(0.1, 1.0 - rank * 0.08),
    )


class DuckDuckGoHtmlProvider:
    """No-key fallback; it returns URLs and snippets, never evidence content."""

    name = "duckduckgo_html"

    async def search(self, query: str, limit: int) -> list[ResearchSource]:
        timeout = httpx.Timeout(settings.web_research_timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers={"User-Agent": "HelpDeskResearch/1.0"}) as client:
            response = await _get_with_retry(client, "https://html.duckduckgo.com/html/", params={"q": query})
        parser = _DuckDuckGoParser()
        parser.feed(response.text)
        sources = [
            source for rank, result in enumerate(parser.results)
            if (source := _source_from_result(result["title"], _unwrap_result_url(result["href"]), result.get("snippet", ""), rank))
        ]
        return sorted(sources[:limit], key=lambda item: (item.source_type != "OFFICIAL", -item.relevance_score))


class ExaSearchProvider:
    """Semantic web search; returned excerpts are never treated as final evidence."""

    name = "exa"

    async def search(self, query: str, limit: int) -> list[ResearchSource]:
        timeout = httpx.Timeout(settings.web_research_timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout, headers={"Accept": "application/json"}) as client:
            response = await _post_with_retry(
                client, "https://api.exa.ai/search",
                payload={"query": query, "type": "auto", "numResults": limit, "contents": {"highlights": True}},
                headers={"x-api-key": settings.exa_api_key},
            )
        results = response.json().get("results", [])
        return [
            source for rank, item in enumerate(results)
            if isinstance(item, dict) and (source := _source_from_result(
                str(item.get("title", "")), str(item.get("url", "")),
                " ".join(str(value) for value in item.get("highlights", []) if isinstance(value, str)) or str(item.get("text", "")), rank,
            ))
        ][:limit]


class TavilySearchProvider:
    name = "tavily"

    async def search(self, query: str, limit: int) -> list[ResearchSource]:
        timeout = httpx.Timeout(settings.web_research_timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout, headers={"Accept": "application/json"}) as client:
            response = await _post_with_retry(
                client, "https://api.tavily.com/search",
                payload={"query": query, "max_results": limit, "search_depth": "basic"},
                headers={"Authorization": f"Bearer {settings.tavily_api_key}"},
            )
        return [
            source for rank, item in enumerate(response.json().get("results", []))
            if isinstance(item, dict) and (source := _source_from_result(str(item.get("title", "")), str(item.get("url", "")), str(item.get("content", "")), rank))
        ][:limit]


class FallbackSearchProvider:
    """Use the first healthy configured provider, then the no-key fallback."""

    def __init__(self, providers: Sequence[SearchProvider]) -> None:
        self.providers = list(providers)
        self.last_provider_name: str | None = None

    @property
    def name(self) -> str:
        return self.last_provider_name or "fallback"

    async def search(self, query: str, limit: int) -> list[ResearchSource]:
        last_error: Exception | None = None
        for provider in self.providers:
            try:
                results = await provider.search(query, limit)
                if results:
                    self.last_provider_name = provider.name
                    return results
            except Exception as exc:
                last_error = exc
                logger.info("External search provider %s unavailable: %s", provider.name, type(exc).__name__)
        if last_error:
            raise last_error
        return []


class _ArticleTextParser(HTMLParser):
    """Dependency-free readable-text extractor with conservative size bounds."""

    _SKIP_TAGS = {"script", "style", "noscript", "svg", "canvas", "iframe", "nav", "footer", "header", "form", "aside"}

    def __init__(self) -> None:
        super().__init__()
        self._skip_depth = 0
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        role = (attributes.get("role") or "").lower()
        classes = (attributes.get("class") or "").lower()
        if tag in self._SKIP_TAGS or role in {"navigation", "banner", "contentinfo"} or "cookie" in classes:
            self._skip_depth += 1
        elif tag in {"p", "br", "li", "h1", "h2", "h3", "pre", "code", "article", "main"} and not self._skip_depth:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self._parts.append(data)

    def text(self) -> str:
        return re.sub(r"\n{3,}", "\n\n", " ".join("".join(self._parts).split())).strip()


def _extract_article_text(raw_html: str) -> str:
    """Prefer a production-grade extractor, with a deterministic local fallback."""
    try:
        import trafilatura

        extracted = trafilatura.extract(
            raw_html, include_comments=False, include_tables=True, favor_precision=True,
        )
        if extracted and len(extracted.strip()) >= 80:
            return extracted.strip()
    except (ImportError, TypeError, ValueError):
        # Development and constrained test environments still get bounded,
        # non-script text instead of silently reverting to SERP snippets.
        pass
    parser = _ArticleTextParser()
    parser.feed(raw_html)
    return parser.text()


_page_cache: dict[str, tuple[float, str]] = {}


class HttpxWebpageReader:
    """Fetch and extract public HTML/text pages after a strict outbound policy."""

    async def read(self, source: ResearchSource) -> ResearchSource | None:
        parsed = urlparse(source.url)
        if not _valid_http_url(source.url) or not parsed.hostname or not await _has_public_dns_target(parsed.hostname):
            return None
        now = time.monotonic()
        cached = _page_cache.get(source.url)
        if cached and cached[0] > now:
            return replace(source, content=cached[1])
        timeout = httpx.Timeout(settings.web_research_timeout_seconds)
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=False, headers={"User-Agent": "HelpDeskResearch/1.0", "Accept": "text/html,text/plain;q=0.9"}) as client:
                content_type, raw = await _read_page_with_retry(
                    client, source.url, settings.web_research_max_page_chars * 8,
                )
        except (httpx.HTTPError, ValueError):
            return None
        if content_type == "text/plain":
            extracted = re.sub(r"\s+", " ", raw).strip()
        else:
            extracted = _extract_article_text(raw)
        extracted = extracted[:settings.web_research_max_page_chars]
        if len(extracted) < 80:
            return None
        if settings.web_research_cache_ttl_seconds:
            _page_cache[source.url] = (now + settings.web_research_cache_ttl_seconds, extracted)
        return replace(source, content=extracted, retrieved_at=datetime.now(UTC))


class FirecrawlWebpageReader:
    """Use Firecrawl for main-content extraction, without provider-side caching."""

    async def read(self, source: ResearchSource) -> ResearchSource | None:
        parsed = urlparse(source.url)
        if not _valid_http_url(source.url) or not parsed.hostname or not await _has_public_dns_target(parsed.hostname):
            return None
        now = time.monotonic()
        cached = _page_cache.get(source.url)
        if cached and cached[0] > now:
            return replace(source, content=cached[1])
        timeout = httpx.Timeout(settings.web_research_timeout_seconds)
        try:
            async with httpx.AsyncClient(timeout=timeout, headers={"Accept": "application/json"}) as client:
                response = await _post_with_retry(
                    client,
                    "https://api.firecrawl.dev/v2/scrape",
                    payload={
                        "url": source.url,
                        "formats": ["markdown"],
                        "onlyMainContent": True,
                        "blockAds": True,
                        "removeBase64Images": True,
                        "storeInCache": False,
                    },
                    headers={"Authorization": f"Bearer {settings.firecrawl_api_key}"},
                )
        except httpx.HTTPError:
            return None
        payload = response.json()
        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        markdown = data.get("markdown", "") if isinstance(data, dict) else ""
        if not isinstance(markdown, str):
            return None
        extracted = markdown.strip()[:settings.web_research_max_page_chars]
        if len(extracted) < 80:
            return None
        if settings.web_research_cache_ttl_seconds:
            _page_cache[source.url] = (now + settings.web_research_cache_ttl_seconds, extracted)
        return replace(source, content=extracted, retrieved_at=datetime.now(UTC))


class FallbackWebpageReader:
    """Prefer a configured extractor but retain safe local page retrieval."""

    def __init__(self, readers: Sequence[WebpageReader]) -> None:
        self.readers = list(readers)

    async def read(self, source: ResearchSource) -> ResearchSource | None:
        for reader in self.readers:
            try:
                result = await reader.read(source)
                if result is not None:
                    return result
            except Exception as exc:
                logger.info("Webpage reader %s unavailable: %s", type(reader).__name__, type(exc).__name__)
        return None


def get_webpage_reader() -> WebpageReader:
    readers: list[WebpageReader] = []
    if settings.firecrawl_api_key:
        readers.append(FirecrawlWebpageReader())
    readers.append(HttpxWebpageReader())
    return FallbackWebpageReader(readers)


def get_search_provider() -> SearchProvider | None:
    if not settings.web_research_enabled or settings.web_search_provider == "disabled":
        return None
    selected = settings.web_search_provider
    if selected == "exa":
        return ExaSearchProvider() if settings.exa_api_key else FallbackSearchProvider([DuckDuckGoHtmlProvider()])
    if selected == "tavily":
        return TavilySearchProvider() if settings.tavily_api_key else FallbackSearchProvider([DuckDuckGoHtmlProvider()])
    if selected == "duckduckgo_html":
        return DuckDuckGoHtmlProvider()
    providers: list[SearchProvider] = []
    if settings.exa_api_key:
        providers.append(ExaSearchProvider())
    if settings.tavily_api_key:
        providers.append(TavilySearchProvider())
    providers.append(DuckDuckGoHtmlProvider())
    return FallbackSearchProvider(providers)


async def maybe_research_web(
    message: str,
    rag_docs: list[dict],
    provider: SearchProvider | None = None,
    *,
    insufficient_internal: bool = False,
    queries: Sequence[str] | None = None,
    reader: WebpageReader | None = None,
) -> ResearchResult:
    should_search, reason = should_research_web(
        message, rag_docs, insufficient_internal=insufficient_internal
    )
    if not should_search:
        return ResearchResult(False, reason, None, [])

    query = sanitize_search_query(message)
    if not query:
        return ResearchResult(
            False, "sensitive_or_empty_search_query", None, [],
            failure_category="query_blocked",
        )
    active_provider = provider or get_search_provider()
    if not active_provider:
        return ResearchResult(False, "web_research_disabled", query, [], failure_category="disabled")

    # Reuse already-computed internal-RAG decomposition when supplied.  The
    # original query is always retained and every outbound variant is redacted
    # independently, so a decomposition cannot broaden the data boundary.
    search_queries: list[str] = []
    for candidate in [query, *(queries or [])]:
        safe_candidate = sanitize_search_query(candidate)
        if safe_candidate and safe_candidate not in search_queries:
            search_queries.append(safe_candidate)
        if len(search_queries) >= settings.web_research_max_queries:
            break
    try:
        result_sets = await asyncio.gather(*(
            active_provider.search(candidate, settings.web_research_max_results)
            for candidate in search_queries
        ))
    except Exception as exc:  # A failed external dependency must not block Help Desk service.
        logger.info("External research unavailable: %s", exc)
        return ResearchResult(False, "search_provider_unavailable", query, [], failure_category="provider_unavailable")

    raw_sources = [item for result_set in result_sets for item in result_set]
    unique_sources: list[ResearchSource] = []
    seen_urls: set[str] = set()
    domain_counts: dict[str, int] = {}
    for source in sorted(raw_sources, key=lambda item: (item.source_type != "OFFICIAL", -item.relevance_score)):
        canonical_url = source.url.rstrip("/")
        if canonical_url in seen_urls or not _valid_http_url(source.url):
            continue
        diversity_key = _diversity_domain(source.domain)
        if domain_counts.get(diversity_key, 0) >= settings.web_research_max_per_domain:
            continue
        seen_urls.add(canonical_url)
        domain_counts[diversity_key] = domain_counts.get(diversity_key, 0) + 1
        unique_sources.append(source)
        if len(unique_sources) >= settings.web_research_max_pages:
            break

    active_reader = reader or get_webpage_reader()
    fetched = await asyncio.gather(*(active_reader.read(source) for source in unique_sources), return_exceptions=True)
    readable_sources = [item for item in fetched if isinstance(item, ResearchSource) and _is_untrusted_content_safe(item)]
    rejected = len(raw_sources) - len(readable_sources)
    if rejected:
        logger.info("Dropped %d web search results that failed URL, fetch, extraction, diversity, or injection policy", rejected)
    ranked_sources = _rerank_web_sources(query, readable_sources)
    return ResearchResult(
        bool(ranked_sources), reason, query, ranked_sources,
        raw_result_count=len(raw_sources),
        rejected_result_count=rejected,
        failure_category="all_results_rejected" if raw_sources and not ranked_sources else None,
        provider=getattr(active_provider, "name", settings.web_search_provider),
        independent_domain_count=len({_diversity_domain(source.domain) for source in ranked_sources}),
    )


def _chunk_web_content(content: str) -> list[str]:
    chunk_size, overlap = 1200, 180
    if len(content) <= chunk_size:
        return [content]
    chunks: list[str] = []
    start = 0
    while start < len(content):
        end = min(len(content), start + chunk_size)
        chunks.append(content[start:end])
        if end == len(content):
            break
        start = end - overlap
    return chunks


def _rerank_web_sources(query: str, sources: list[ResearchSource]) -> list[ResearchSource]:
    """Use the existing local CrossEncoder for web evidence, with safe fallback.

    Citations remain URL-level.  We keep the best few semantic chunks per URL
    instead of making each chunk look like a separate external source.
    """
    candidates: list[dict[str, Any]] = []
    for source_index, source in enumerate(sources):
        for chunk_index, chunk in enumerate(_chunk_web_content(source.content)[:settings.web_research_max_chunks_per_source]):
            candidates.append({
                "doc_id": f"{source_index}:{chunk_index}",
                "content": chunk,
                "metadata": {"title": source.title, "source": "external_web"},
                "relevance_score": source.relevance_score,
                "fusion_score": source.relevance_score,
                "source_index": source_index,
                "chunk_index": chunk_index,
            })
    if not candidates:
        return []
    reranked = rerank_candidates(
        query, candidates, top_k=len(candidates), top_n_candidates=len(candidates),
        enabled=settings.web_research_reranker_enabled,
    )
    selected: dict[int, list[dict[str, Any]]] = {}
    for candidate in reranked:
        index = int(candidate["source_index"])
        selected.setdefault(index, []).append(candidate)
    enriched: list[ResearchSource] = []
    for index, source in enumerate(sources):
        best_chunks = selected.get(index, [])[:settings.web_research_max_chunks_per_source]
        if not best_chunks:
            continue
        score = float(best_chunks[0].get("relevance_score", source.relevance_score))
        if source.source_type == "OFFICIAL":
            score = min(1.0, score * 1.05)
        content = "\n\n".join(str(chunk["content"]) for chunk in best_chunks)
        enriched.append(replace(source, content=content[:settings.web_research_max_page_chars], relevance_score=max(0.0, min(1.0, score))))
    return sorted(enriched, key=lambda item: (item.source_type != "OFFICIAL", -item.relevance_score))[:settings.web_research_max_pages]


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
        search_provider=research.provider or settings.web_search_provider,
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
        description=f"External research executed via {research.provider or settings.web_search_provider}",
        metadata={
            "query": research.query,
            "search_provider": research.provider or settings.web_search_provider,
            "independent_domain_count": research.independent_domain_count,
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
