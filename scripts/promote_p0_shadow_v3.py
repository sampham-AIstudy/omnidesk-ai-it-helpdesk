"""Guarded, one-way copy of the verified P0 shadow collection into canonical v3.

This script never changes v2 or the source shadow collection.  It refuses to
overwrite an existing target and emits a rollback record that selects v2 by
configuration only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.ingest_p0_shadow_kb import REQUIRED_FIELDS, validate_and_prepare  # noqa: E402
from src.config import get_settings  # noqa: E402

V2_COLLECTION = "helpdesk_kb_multilingual_v2_sentence_transformer"
SHADOW_COLLECTION = "helpdesk_kb_multilingual_v3_shadow"
V3_COLLECTION = "helpdesk_kb_multilingual_v3_sentence_transformer"


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _json_hash(value: Any) -> str:
    def _json_default(item: Any) -> Any:
        if hasattr(item, "tolist"):
            return item.tolist()
        raise TypeError(f"unsupported digest value: {type(item)!r}")

    return _sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=_json_default).encode("utf-8")
    )


def _records(collection: Any, batch_size: int = 64) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for offset in range(0, collection.count(), batch_size):
        batch = collection.get(limit=batch_size, offset=offset, include=["documents", "metadatas", "embeddings"])
        records.extend(
            {"id": item_id, "document": document, "metadata": metadata, "embedding": embedding}
            for item_id, document, metadata, embedding in zip(
                batch["ids"], batch["documents"], batch["metadatas"], batch["embeddings"]
            )
        )
    return sorted(records, key=lambda item: item["id"])


def _record_digest(records: list[dict[str, Any]]) -> str:
    return _json_hash(
        [
            {
                "id": item["id"],
                "document": item["document"],
                "metadata": item["metadata"],
                "embedding": item["embedding"],
            }
            for item in records
        ]
    )


def _collection_summary(collection: Any) -> dict[str, Any]:
    records = _records(collection)
    metadata = collection.metadata or {}
    source_counts = Counter(
        str((item["metadata"] or {}).get("source_type") or (item["metadata"] or {}).get("source") or "unknown")
        for item in records
    )
    return {
        "name": collection.name,
        "chunk_count": collection.count(),
        "collection_metadata": metadata,
        "embedding_model": metadata.get("embedding_model"),
        "embedding_backend": metadata.get("embedding_backend"),
        "embedding_dimension": metadata.get("embedding_dimension"),
        "distance_metric": metadata.get("hnsw:space"),
        "source_counts": dict(sorted(source_counts.items())),
        "record_digest": _record_digest(records),
    }


def _manifest_summary(manifest_path: Path) -> dict[str, Any]:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    accepted, rejected, duplicates = validate_and_prepare(payload["sources"])
    if rejected or duplicates or len(accepted) != len(payload["sources"]):
        raise ValueError("P0 manifest provenance is incomplete or has rejected/duplicate sources")
    missing = [source["source_id"] for source in accepted if any(not source.get(field) for field in REQUIRED_FIELDS)]
    if missing:
        raise ValueError(f"P0 manifest has empty required fields: {', '.join(missing)}")
    return {
        "manifest_path": str(manifest_path),
        "manifest_sha256": _sha256(manifest_path.read_bytes()),
        "batch_id": payload.get("batch_id"),
        "internal_procedure_status": payload.get("internal_procedure_status"),
        "source_count": len(accepted),
        "source_content_hashes": {source["source_id"]: source["content_hash"] for source in accepted},
        "source_types": sorted({source["source_type"] for source in accepted}),
    }


def _integrity(source: Any, target: Any) -> dict[str, Any]:
    source_records, target_records = _records(source), _records(target)
    source_ids = [item["id"] for item in source_records]
    target_ids = [item["id"] for item in target_records]
    source_metadata = {item["id"]: item["metadata"] for item in source_records}
    target_metadata = {item["id"]: item["metadata"] for item in target_records}
    content_hashes_equal = all(
        (source_metadata[item_id] or {}).get("content_hash") == (target_metadata[item_id] or {}).get("content_hash")
        for item_id in source_ids
    )
    metadata_equal = source_metadata == target_metadata
    document_ids_preserved = source_ids == target_ids
    source_by_id = {item["id"]: item for item in source_records}
    target_by_id = {item["id"]: item for item in target_records}
    max_embedding_delta = 0.0
    embedding_dimensions_preserved = True
    for item_id in source_ids:
        source_embedding = source_by_id[item_id]["embedding"]
        target_embedding = target_by_id[item_id]["embedding"]
        if len(source_embedding) != len(target_embedding):
            embedding_dimensions_preserved = False
            continue
        for before, after in zip(source_embedding, target_embedding):
            max_embedding_delta = max(max_embedding_delta, abs(float(before) - float(after)))
    checks = {
        "same_count": source.count() == target.count(),
        "same_expected_ids": document_ids_preserved,
        "document_ids_preserved": document_ids_preserved,
        "document_content_preserved": all(
            source_by_id[item_id]["document"] == target_by_id[item_id]["document"] for item_id in source_ids
        ),
        "embeddings_preserved_within_float32_roundtrip_tolerance": embedding_dimensions_preserved and max_embedding_delta <= 1e-7,
        "content_hashes_preserved": content_hashes_equal,
        "source_metadata_preserved": metadata_equal,
        "topic_metadata_preserved": all(
            (source_metadata[item_id] or {}).get("topic") == (target_metadata[item_id] or {}).get("topic")
            for item_id in source_ids
        ),
        "tenant_acl_metadata_preserved": all(
            all((source_metadata[item_id] or {}).get(key) == (target_metadata[item_id] or {}).get(key)
                for key in ("company_unit", "department", "applicable_to_all"))
            for item_id in source_ids
        ),
        "authority_metadata_preserved": all(
            all((source_metadata[item_id] or {}).get(key) == (target_metadata[item_id] or {}).get(key)
                for key in ("source", "source_type", "authority"))
            for item_id in source_ids
        ),
        "embedding_dimension_preserved": (source.metadata or {}).get("embedding_dimension") == (target.metadata or {}).get("embedding_dimension"),
        "distance_metric_preserved": (source.metadata or {}).get("hnsw:space") == (target.metadata or {}).get("hnsw:space"),
        "no_duplicate_chunks": len(target_ids) == len(set(target_ids)),
    }
    result = {**checks, "max_abs_embedding_delta": max_embedding_delta}
    result["pass"] = all(checks.values())
    return result


def promote(
    *, source_name: str, target_name: str, manifest_path: Path, report_path: Path, verify_existing: bool = False
) -> dict[str, Any]:
    """Create canonical v3 from the verified shadow collection exactly once."""
    settings = get_settings()
    client = chromadb.PersistentClient(
        path=str(Path(settings.chroma_persist_dir)), settings=ChromaSettings(anonymized_telemetry=False)
    )
    names = {collection.name for collection in client.list_collections()}
    if source_name not in names:
        raise ValueError(f"verified shadow collection does not exist: {source_name}")
    if target_name in names and not verify_existing:
        raise FileExistsError(f"refusing to overwrite existing canonical target: {target_name}")

    manifest = _manifest_summary(manifest_path)
    source = client.get_collection(source_name)
    source_records = _records(source)
    source_summary = _collection_summary(source)
    if target_name in names:
        target = client.get_collection(target_name)
    else:
        target_metadata = dict(source.metadata or {})
        target_metadata.update(
            {
                "canonical_version": "v3",
                "promotion_source_collection": source_name,
                "promoted_at": datetime.now(UTC).isoformat(),
                "shadow_only": False,
            }
        )
        target = client.create_collection(name=target_name, metadata=target_metadata)
        for start in range(0, len(source_records), 64):
            batch = source_records[start:start + 64]
            target.add(
                ids=[item["id"] for item in batch],
                documents=[item["document"] for item in batch],
                metadatas=[item["metadata"] for item in batch],
                embeddings=[item["embedding"] for item in batch],
            )
    integrity = _integrity(source, target)
    if not integrity["pass"]:
        raise RuntimeError("canonical v3 integrity check failed; runtime configuration must not be switched")
    report = {
        "created_at": datetime.now(UTC).isoformat(),
        "pre_promotion": {
            "active_runtime_collection": settings.chroma_collection_name,
            "v2": _collection_summary(client.get_collection(V2_COLLECTION)),
            "shadow": source_summary,
            "manifest": manifest,
        },
        "canonical_v3": _collection_summary(target),
        "collection_integrity": integrity,
        "rollback": {
            "collection_name": V2_COLLECTION,
            "configuration": {"CHROMA_COLLECTION_NAME": V2_COLLECTION},
            "procedure": "Set CHROMA_COLLECTION_NAME to the v2 collection and restart/reload the application.",
        },
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=SHADOW_COLLECTION)
    parser.add_argument("--target", default=V3_COLLECTION)
    parser.add_argument("--manifest", type=Path, default=ROOT / "data" / "p0_shadow_v3_sources.json")
    parser.add_argument("--report", type=Path, default=ROOT / "eval" / "results" / "p0_v3_promotion.json")
    parser.add_argument("--verify-existing", action="store_true", help="Verify an already-created target without mutating it.")
    args = parser.parse_args()
    print(json.dumps(promote(source_name=args.source, target_name=args.target, manifest_path=args.manifest,
                             report_path=args.report, verify_existing=args.verify_existing), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
