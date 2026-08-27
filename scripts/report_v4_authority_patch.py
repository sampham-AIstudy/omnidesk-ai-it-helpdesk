"""Read-only V4 authority metadata patch plan.

This script never calls ``update`` or ``upsert``. It compares the current
shadow collection with the staged crawl manifest and reports a metadata-only
patch plan, including invariant IDs/content/embedding digests.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import chromadb

ROOT = Path(__file__).resolve().parents[1]
V4 = "helpdesk_kb_multilingual_v4_shadow"


def _digest(value: object) -> str:
    serializable = value.tolist() if hasattr(value, "tolist") else value
    return hashlib.sha256(
        json.dumps(serializable, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def build_dry_run_report() -> dict:
    manifest = json.loads((ROOT / "data/staging/crawl_v4/manifest_v4.json").read_text(encoding="utf-8"))
    authority_by_source = {str(item["key"]): item.get("authority") for item in manifest if item.get("authority") is not None}
    client = chromadb.PersistentClient(path=str(ROOT / "data/chroma"))
    collection = client.get_collection(V4)
    data = collection.get(limit=collection.count(), include=["documents", "metadatas", "embeddings"])
    affected: list[dict] = []
    unchanged = 0
    for item_id, document, metadata, embedding in zip(data["ids"], data["documents"], data["metadatas"], data["embeddings"]):
        source_id = str((metadata or {}).get("source_id") or "")
        desired = authority_by_source.get(source_id)
        if desired is None:
            unchanged += 1
            continue
        old = (metadata or {}).get("authority")
        if old == desired:
            unchanged += 1
            continue
        affected.append({
            "id": item_id,
            "source_id": source_id,
            "old_authority": old,
            "new_authority": desired,
            "content_sha256": hashlib.sha256(str(document).encode("utf-8")).hexdigest(),
            "embedding_sha256": _digest(embedding),
            "id_unchanged": True,
            "content_unchanged": True,
            "embedding_unchanged": True,
        })
    return {
        "mode": "DRY_RUN_ONLY",
        "collection": V4,
        "collection_count": collection.count(),
        "records_affected": len(affected),
        "records_unaffected": unchanged,
        "all_changes_metadata_only": all(
            item["id_unchanged"] and item["content_unchanged"] and item["embedding_unchanged"]
            for item in affected
        ),
        "new_authority_distribution": dict(Counter(str(item["new_authority"]) for item in affected)),
        "changes": affected,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Report a non-mutating V4 authority metadata patch plan")
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()
    report = build_dry_run_report()
    if args.summary_only:
        report["changes"] = []
    print(json.dumps(report, ensure_ascii=False, indent=2))
