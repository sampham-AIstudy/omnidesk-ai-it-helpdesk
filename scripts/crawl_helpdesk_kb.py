"""Crawl an allow-listed set of authoritative IT help-desk documents.

The crawler intentionally does not follow links. It checks robots.txt, limits the
response size, removes page chrome, deduplicates text blocks, and emits small RAG
documents with provenance and checksums.

Examples:
    python scripts/crawl_helpdesk_kb.py
    python scripts/crawl_helpdesk_kb.py --index
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger("helpdesk_kb_crawler")

DEFAULT_MANIFEST = Path(__file__).with_name("it_helpdesk_sources.json")
DEFAULT_OUTPUT = Path("data/enriched_helpdesk_kb.json")
USER_AGENT = "HelpDeskAI-KBCrawler/1.0 (curated documentation ingestion)"
BLOCK_TAGS = {"h1", "h2", "h3", "h4", "p", "li", "pre", "code"}
SKIP_TAGS = {"script", "style", "svg", "nav", "footer", "form", "noscript"}


@dataclass(frozen=True)
class Source:
    key: str
    title: str
    url: str
    category: str
    tags: tuple[str, ...]


class ArticleTextParser(HTMLParser):
    """Extract readable blocks while dropping scripts and common page chrome."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._all_blocks: list[str] = []
        self._scoped_blocks: list[str] = []
        self.page_title = ""
        self._buffer: list[str] = []
        self._active_blocks = 0
        self._skip_depth = 0
        self._in_title = False
        self._content_depth = 0
        self._block_is_scoped = False

    @property
    def blocks(self) -> list[str]:
        return self._scoped_blocks or self._all_blocks

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag in {"main", "article"}:
            self._content_depth += 1
        if tag == "title":
            self._in_title = True
        if tag in BLOCK_TAGS:
            if self._active_blocks == 0:
                self._buffer = []
                self._block_is_scoped = self._content_depth > 0
            self._active_blocks += 1

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1
            return
        if self._skip_depth:
            return
        if tag == "title":
            self._in_title = False
        if tag in BLOCK_TAGS and self._active_blocks:
            self._active_blocks -= 1
            if self._active_blocks == 0:
                value = clean_text(" ".join(self._buffer))
                if len(value) >= 8:
                    self._all_blocks.append(value)
                    if self._block_is_scoped:
                        self._scoped_blocks.append(value)
                self._buffer = []
        if tag in {"main", "article"} and self._content_depth:
            self._content_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        value = clean_text(data)
        if not value:
            return
        if self._in_title:
            self.page_title = clean_text(f"{self.page_title} {value}")
        if self._active_blocks:
            self._buffer.append(value)


def clean_text(value: str) -> str:
    value = value.replace("\u200b", " ").replace("\xa0", " ")
    return re.sub(r"\s+", " ", value).strip()


def deduplicate_blocks(blocks: list[str]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for block in blocks:
        normalized = re.sub(r"\W+", " ", block.casefold()).strip()
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        if digest not in seen:
            seen.add(digest)
            unique.append(block)
    return unique


def chunk_blocks(
    blocks: list[str], max_chars: int = 1800, overlap_blocks: int = 1
) -> list[str]:
    if max_chars < 200:
        raise ValueError("max_chars must be at least 200")

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for block in blocks:
        pieces = [block[i : i + max_chars] for i in range(0, len(block), max_chars)]
        for piece in pieces:
            added_len = len(piece) + (2 if current else 0)
            if current and current_len + added_len > max_chars:
                chunks.append("\n\n".join(current))
                current = current[-overlap_blocks:] if overlap_blocks else []
                current_len = sum(len(item) for item in current) + 2 * max(0, len(current) - 1)
                if current and current_len + len(piece) + 2 > max_chars:
                    current = []
                    current_len = 0
            current.append(piece)
            current_len += len(piece) + (2 if len(current) > 1 else 0)
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def load_sources(path: Path) -> list[Source]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    sources = [
        Source(
            key=item["key"],
            title=item["title"],
            url=item["url"],
            category=item["category"],
            tags=tuple(item.get("tags", [])),
        )
        for item in payload
    ]
    keys = [source.key for source in sources]
    if len(keys) != len(set(keys)):
        raise ValueError("Source keys must be unique")
    for source in sources:
        parsed = urlparse(source.url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError(f"Only HTTPS sources are allowed: {source.url}")
    return sources


def robots_allowed(client: httpx.Client, url: str) -> bool:
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        response = client.get(robots_url)
        if response.status_code >= 400:
            return True
        parser = RobotFileParser()
        parser.set_url(robots_url)
        parser.parse(response.text.splitlines())
        return parser.can_fetch(USER_AGENT, url)
    except httpx.HTTPError as exc:
        logger.warning("Không đọc được robots.txt của %s: %s", parsed.netloc, exc)
        return False


def fetch_source(
    client: httpx.Client,
    source: Source,
    allowed_hosts: set[str],
    max_bytes: int,
) -> tuple[str, list[str]]:
    if not robots_allowed(client, source.url):
        raise RuntimeError("robots.txt không cho phép hoặc không thể kiểm tra")

    with client.stream("GET", source.url) as response:
        response.raise_for_status()
        final_host = (urlparse(str(response.url)).hostname or "").lower()
        if final_host not in allowed_hosts:
            raise RuntimeError(f"redirect ra ngoài allow-list: {final_host}")
        content_type = response.headers.get("content-type", "").lower()
        if "text/html" not in content_type:
            raise RuntimeError(f"content-type không được hỗ trợ: {content_type}")
        raw = bytearray()
        for part in response.iter_bytes():
            raw.extend(part)
            if len(raw) > max_bytes:
                raise RuntimeError(f"trang vượt giới hạn {max_bytes} bytes")

    parser = ArticleTextParser()
    parser.feed(bytes(raw).decode(response.encoding or "utf-8", errors="replace"))
    blocks = deduplicate_blocks(parser.blocks)
    if not blocks:
        raise RuntimeError("không trích xuất được nội dung")
    return parser.page_title or source.title, blocks


def crawl(
    sources: list[Source],
    timeout: float = 20.0,
    max_bytes: int = 2_000_000,
    max_chars: int = 1800,
    max_chunks_per_source: int = 8,
    delay: float = 0.5,
) -> dict:
    allowed_hosts = {
        (urlparse(source.url).hostname or "").lower() for source in sources
    }
    documents: list[dict] = []
    failures: list[dict] = []
    retrieved_at = datetime.now(UTC).isoformat()

    with httpx.Client(
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
        timeout=timeout,
    ) as client:
        for position, source in enumerate(sources):
            try:
                page_title, blocks = fetch_source(client, source, allowed_hosts, max_bytes)
                chunks = chunk_blocks(blocks, max_chars=max_chars)[:max_chunks_per_source]
                for index, chunk in enumerate(chunks, start=1):
                    checksum = hashlib.sha256(chunk.encode("utf-8")).hexdigest()
                    documents.append(
                        {
                            "doc_id": f"web-{source.key}-{index:03d}",
                            "title": source.title,
                            "content": chunk,
                            "category": source.category,
                            "tags": ",".join(source.tags),
                            "source": "official_web_documentation",
                            "source_title": page_title,
                            "source_url": source.url,
                            "retrieved_at": retrieved_at,
                            "content_sha256": checksum,
                        }
                    )
                logger.info("%s: %d blocks -> %d chunks", source.key, len(blocks), len(chunks))
            except (httpx.HTTPError, RuntimeError, UnicodeError) as exc:
                logger.error("%s: %s", source.key, exc)
                failures.append({"key": source.key, "url": source.url, "error": str(exc)})
            if position < len(sources) - 1 and delay:
                time.sleep(delay)

    return {
        "schema_version": 1,
        "generated_at": retrieved_at,
        "source_count": len(sources),
        "document_count": len(documents),
        "documents": documents,
        "failures": failures,
    }


def index_documents(documents: list[dict]) -> int:
    from src.services.rag_service import index_document

    for item in documents:
        content = f"{item['title']}. Từ khóa: {item['tags']}. {item['content']}"
        index_document(
            doc_id=item["doc_id"],
            content=content,
            metadata={
                "title": item["title"],
                "category": item["category"],
                "tags": item["tags"],
                "source": item["source"],
                "source_title": item["source_title"],
                "source_url": item["source_url"],
                "retrieved_at": item["retrieved_at"],
                "content_sha256": item["content_sha256"],
                "applicable_to_all": True,
                "company_unit": "all",
                "department": "",
            },
        )
    return len(documents)


def main() -> int:
    parser = argparse.ArgumentParser(description="Crawl tài liệu IT Help Desk cho RAG")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--max-bytes", type=int, default=2_000_000)
    parser.add_argument("--max-chars", type=int, default=1800)
    parser.add_argument("--max-chunks-per-source", type=int, default=8)
    parser.add_argument("--delay", type=float, default=0.5)
    parser.add_argument("--index", action="store_true", help="Upsert kết quả vào ChromaDB")
    parser.add_argument(
        "--index-only",
        action="store_true",
        help="Không crawl; index file --output đã có vào ChromaDB",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if args.index_only:
        existing = json.loads(args.output.read_text(encoding="utf-8"))
        indexed = index_documents(existing.get("documents", []))
        logger.info("Đã upsert %d tài liệu từ %s vào ChromaDB", indexed, args.output)
        return 0

    sources = load_sources(args.manifest)
    result = crawl(
        sources,
        timeout=args.timeout,
        max_bytes=args.max_bytes,
        max_chars=args.max_chars,
        max_chunks_per_source=args.max_chunks_per_source,
        delay=args.delay,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Đã ghi %d tài liệu vào %s", result["document_count"], args.output)

    if args.index and result["documents"]:
        indexed = index_documents(result["documents"])
        logger.info("Đã upsert %d tài liệu vào ChromaDB", indexed)
    return 1 if result["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
