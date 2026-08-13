"""Publish crawled, public RAG documents to the employee-facing KB catalogue.

The crawler writes chunks into ChromaDB-ready JSON.  The web catalogue reads
SQLite, so this explicit sync keeps the two stores aligned without publishing
historical incident memories to every employee.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path


def build_entries(payload: dict) -> list[dict]:
    entries: list[dict] = []
    for item in payload.get("documents", []):
        doc_id = item["doc_id"]
        chunk = doc_id.rsplit("-", 1)[-1]
        source_url = item.get("source_url", "")
        content = item["content"].strip()
        if source_url:
            content = f"{content}\n\nNguồn tham khảo: {source_url}"
        entries.append(
            {
                "chroma_id": doc_id,
                "title": f"{item['title']} — phần {int(chunk)}",
                "content": content,
                "category": item.get("category", "other"),
                "tags": item.get("tags", ""),
            }
        )
    return entries


def sync(database: Path, source: Path) -> tuple[int, int]:
    payload = json.loads(source.read_text(encoding="utf-8"))
    entries = build_entries(payload)
    inserted = updated = 0
    with sqlite3.connect(database) as connection:
        for entry in entries:
            exists = connection.execute(
                "SELECT id FROM knowledge_base WHERE chroma_id = ?", (entry["chroma_id"],)
            ).fetchone()
            if exists:
                connection.execute(
                    """UPDATE knowledge_base
                       SET title = ?, content = ?, category = ?, tags = ?,
                           applicable_to_all = 1, is_active = 1
                       WHERE chroma_id = ?""",
                    (entry["title"], entry["content"], entry["category"], entry["tags"], entry["chroma_id"]),
                )
                updated += 1
            else:
                connection.execute(
                    """INSERT INTO knowledge_base
                       (chroma_id, title, content, category, tags, applicable_to_all,
                        usage_count, helpful_votes, is_active)
                       VALUES (?, ?, ?, ?, ?, 1, 0, 0, 1)""",
                    (entry["chroma_id"], entry["title"], entry["content"], entry["category"], entry["tags"]),
                )
                inserted += 1
    return inserted, updated


def main() -> int:
    parser = argparse.ArgumentParser(description="Đồng bộ tài liệu crawl vào catalogue KB")
    parser.add_argument("--database", type=Path, default=Path("data/helpdesk.db"))
    parser.add_argument("--source", type=Path, default=Path("data/enriched_helpdesk_kb.json"))
    args = parser.parse_args()
    inserted, updated = sync(args.database, args.source)
    print(f"Inserted {inserted}, updated {updated} KB catalogue entries.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
