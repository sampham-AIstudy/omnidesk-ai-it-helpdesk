"""Build the configured Chroma collection from every local help-desk source.

This does not delete older collections. Change CHROMA_COLLECTION_NAME when the
embedding model changes so vectors produced by different models never mix.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_settings
from src.data.knowledge_base import get_all_kb_entries
from src.services.rag_service import get_collection_count, index_documents

logger = logging.getLogger("rag_index_rebuild")


def internal_kb_documents() -> list[dict]:
    documents = []
    for item in get_all_kb_entries():
        tags = item.get("tags", "")
        content = f"{item['title']}. Từ khóa: {tags}. {item['content']}"
        if item.get("solution"):
            content += f" Giải pháp: {item['solution']}"
        documents.append(
            {
                "doc_id": item["id"],
                "content": content,
                "metadata": {
                    "title": item["title"],
                    "category": item["category"],
                    "tags": tags,
                    "solution": item.get("solution", ""),
                    "runbook": item.get("runbook", ""),
                    "source": "internal_curated_kb",
                    "company_unit": item.get("company_unit", "all"),
                    "department": item.get("department", ""),
                    "applicable_to_all": item.get("applicable_to_all", True),
                },
            }
        )
    return documents


def historical_documents(path: Path) -> list[dict]:
    if not path.exists():
        logger.warning("Bỏ qua historical memory vì không có file: %s", path)
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    documents = []
    for index, item in enumerate(payload):
        title = item.get("title", "Sự cố lịch sử")
        solution = item.get("solution", "")
        ticket_number = item.get("ticket_number") or item.get("ticket_id")
        documents.append(
            {
                "doc_id": item.get("doc_id", f"historical-{index:05d}"),
                "content": f"{title}. {item.get('content', '')} Giải pháp: {solution}",
                "metadata": {
                    "title": title,
                    "category": item.get("category", "other"),
                    "tags": item.get("tags", "historical,resolved ticket"),
                    "solution": solution,
                    "runbook": item.get("runbook", ""),
                    "source": "historical_resolved_ticket",
                    "origin_ticket_number": str(ticket_number) if ticket_number else "",
                    "company_unit": "all",
                    "department": "",
                    "applicable_to_all": True,
                },
            }
        )
    return documents


def crawled_documents(path: Path) -> list[dict]:
    if not path.exists():
        logger.warning("Bỏ qua tài liệu crawl vì không có file: %s", path)
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    documents = []
    for item in payload.get("documents", []):
        tags = item.get("tags", "")
        documents.append(
            {
                "doc_id": item["doc_id"],
                "content": f"{item['title']}. Từ khóa: {tags}. {item['content']}",
                "metadata": {
                    "title": item["title"],
                    "category": item["category"],
                    "tags": tags,
                    "source": item.get("source", "official_web_documentation"),
                    "source_title": item.get("source_title", item["title"]),
                    "source_url": item.get("source_url", ""),
                    "retrieved_at": item.get("retrieved_at", ""),
                    "content_sha256": item.get("content_sha256", ""),
                    "company_unit": "all",
                    "department": "",
                    "applicable_to_all": True,
                },
            }
        )
    return documents


def deduplicate_documents(documents: list[dict]) -> list[dict]:
    unique: dict[str, dict] = {}
    for item in documents:
        doc_id = item["doc_id"]
        if doc_id in unique and unique[doc_id]["content"] != item["content"]:
            raise ValueError(f"Trùng doc_id với nội dung khác nhau: {doc_id}")
        unique[doc_id] = item
    return list(unique.values())


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild toàn bộ RAG index")
    parser.add_argument(
        "--historical", type=Path, default=Path("data/historical_ticket_memory.json")
    )
    parser.add_argument(
        "--crawled", type=Path, default=Path("data/enriched_helpdesk_kb.json")
    )
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args()
    if args.batch_size < 1:
        parser.error("--batch-size phải lớn hơn 0")

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    settings = get_settings()
    documents = deduplicate_documents(
        internal_kb_documents()
        + historical_documents(args.historical)
        + crawled_documents(args.crawled)
    )
    logger.info(
        "Indexing %d documents into %s with %s",
        len(documents),
        settings.chroma_collection_name,
        settings.embedding_model,
    )
    for start in range(0, len(documents), args.batch_size):
        batch = documents[start : start + args.batch_size]
        index_documents(batch)
        logger.info("Indexed %d/%d", min(start + len(batch), len(documents)), len(documents))

    logger.info("Collection count: %d", get_collection_count())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
