"""Apply the reviewed V4 authority metadata patch only with explicit consent.

The default is a read-only dry run.  ``--apply`` is intentionally required so
normal evaluation and test commands cannot mutate the shadow collection.
"""
from __future__ import annotations

import argparse
import hashlib
import json

import chromadb
from report_v4_authority_patch import ROOT, V4, _digest, build_dry_run_report


def _document_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def apply_verified_metadata_patch(report: dict) -> dict:
    """Update authority only after proving every affected record is unchanged."""
    if report.get("mode") != "DRY_RUN_ONLY" or not report.get("all_changes_metadata_only"):
        raise RuntimeError("Refusing a patch without a clean metadata-only dry run")
    changes = report.get("changes", [])
    if not changes:
        return {"patched": 0, "collection_count": report["collection_count"]}

    client = chromadb.PersistentClient(path=str(ROOT / "data/chroma"))
    collection = client.get_collection(V4)
    if collection.count() != report["collection_count"]:
        raise RuntimeError("Collection count changed after the dry run")
    ids = [item["id"] for item in changes]
    current = collection.get(ids=ids, include=["documents", "metadatas", "embeddings"])
    rows = {
        item_id: (document, metadata or {}, embedding)
        for item_id, document, metadata, embedding in zip(
            current["ids"], current["documents"], current["metadatas"], current["embeddings"]
        )
    }
    if set(rows) != set(ids):
        raise RuntimeError("Affected IDs changed after the dry run")

    replacement_metadata: list[dict] = []
    for change in changes:
        document, metadata, embedding = rows[change["id"]]
        if (
            _document_hash(document) != change["content_sha256"]
            or _digest(embedding) != change["embedding_sha256"]
            or metadata.get("authority") != change["old_authority"]
        ):
            raise RuntimeError(f"Invariant failed for {change['id']}; no update was attempted")
        updated = dict(metadata)
        updated["authority"] = change["new_authority"]
        replacement_metadata.append(updated)

    for start in range(0, len(ids), 100):
        collection.update(
            ids=ids[start:start + 100],
            metadatas=replacement_metadata[start:start + 100],
        )

    verified = collection.get(ids=ids, include=["documents", "metadatas", "embeddings"])
    verified_rows = {
        item_id: (document, metadata or {}, embedding)
        for item_id, document, metadata, embedding in zip(
            verified["ids"], verified["documents"], verified["metadatas"], verified["embeddings"]
        )
    }
    for change in changes:
        document, metadata, embedding = verified_rows.get(change["id"], (None, {}, None))
        if (
            document is None
            or _document_hash(document) != change["content_sha256"]
            or _digest(embedding) != change["embedding_sha256"]
            or metadata.get("authority") != change["new_authority"]
        ):
            raise RuntimeError(f"Post-update invariant failed for {change['id']}")
    if collection.count() != report["collection_count"]:
        raise RuntimeError("Collection count changed during metadata patch")
    return {"patched": len(changes), "collection_count": collection.count()}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Explicitly permit metadata-only update")
    args = parser.parse_args()
    dry_run = build_dry_run_report()
    if not args.apply:
        print(json.dumps(dry_run, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(apply_verified_metadata_patch(dry_run), ensure_ascii=False, indent=2))
