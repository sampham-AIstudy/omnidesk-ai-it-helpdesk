"""Safely re-embed one KB collection into a separately named Chroma collection."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import get_settings
from src.services.rag_service import (
    _legacy_hashing_provenance,
    effective_embedding_provenance,
    embed_texts,
)


def _all_records(collection: chromadb.Collection, batch_size: int) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    offset = 0
    while True:
        batch = collection.get(
            limit=batch_size,
            offset=offset,
            include=["documents", "metadatas"],
        )
        ids = batch.get("ids", [])
        if not ids:
            break
        records.extend(
            {
                "id": str(doc_id),
                "document": str(document or ""),
                "metadata": metadata or {},
            }
            for doc_id, document, metadata in zip(
                ids, batch.get("documents", []), batch.get("metadatas", [])
            )
        )
        offset += len(ids)
    return records


def _inventory_digest(records: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for record in sorted(records, key=lambda item: item["id"]):
        digest.update(record["id"].encode("utf-8"))
        digest.update(record["document"].encode("utf-8"))
        digest.update(json.dumps(record["metadata"], ensure_ascii=False, sort_keys=True).encode("utf-8"))
    return digest.hexdigest()


def _normalize_legacy_hashing_metadata(client: chromadb.ClientAPI) -> list[str]:
    normalized: list[str] = []
    provenance = _legacy_hashing_provenance()
    for name in ("helpdesk_ticket_duplicates_v1", "helpdesk_episodic_memory_v1"):
        try:
            collection = client.get_collection(name)
        except Exception:
            continue
        metadata = dict(collection.metadata or {})
        # Chroma forbids passing the immutable HNSW distance metadata through
        # Collection.modify(), even when its value is unchanged.
        metadata.pop("hnsw:space", None)
        metadata.update({
            key: value
            for key, value in provenance.collection_metadata().items()
            if key != "hnsw:space"
        })
        collection.modify(metadata=metadata)
        normalized.append(name)
    return normalized


def migrate(
    *,
    persist_dir: Path,
    source_name: str,
    target_name: str,
    backup_dir: Path,
    batch_size: int,
    resume: bool = False,
) -> dict[str, Any]:
    if source_name == target_name:
        raise ValueError("Source and target collection names must differ")
    if backup_dir.exists() and not resume:
        raise FileExistsError(f"Refusing to overwrite backup: {backup_dir}")

    client = chromadb.PersistentClient(
        path=str(persist_dir), settings=ChromaSettings(anonymized_telemetry=False)
    )
    existing_names = {item.name for item in client.list_collections()}
    if source_name not in existing_names:
        raise ValueError(f"Source collection does not exist: {source_name}")
    if target_name in existing_names and not resume:
        raise ValueError(f"Target collection already exists: {target_name}")

    source = client.get_collection(source_name)
    records = _all_records(source, batch_size)
    if not records:
        raise ValueError("Refusing to migrate an empty source collection")
    source_ids = {record["id"] for record in records}
    source_digest = _inventory_digest(records)

    provenance = effective_embedding_provenance()
    created_at = datetime.now(UTC).isoformat()
    if resume:
        if not backup_dir.exists() or target_name not in existing_names:
            raise ValueError("Resume requires both the original backup and target collection")
        target = client.get_collection(target_name)
    else:
        backup_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(persist_dir, backup_dir)
        target = client.create_collection(
            name=target_name,
            metadata=provenance.collection_metadata(
                embedding_version="c4_3",
                created_at=created_at,
                source_collection=source_name,
                migration="c4_3_reembedding",
            ),
        )
        for start in range(0, len(records), batch_size):
            batch = records[start : start + batch_size]
            vectors = embed_texts([record["document"] for record in batch])
            if any(len(vector) != provenance.dimension for vector in vectors):
                raise RuntimeError("Generated embedding dimension differs from canonical provenance")
            target.add(
                ids=[record["id"] for record in batch],
                documents=[record["document"] for record in batch],
                metadatas=[record["metadata"] for record in batch],
                embeddings=vectors,
            )

    migrated_records = _all_records(target, batch_size)
    target_ids = {record["id"] for record in migrated_records}
    target_digest = _inventory_digest(migrated_records)
    sample = target.get(limit=1, include=["embeddings"])
    sample_embeddings = sample.get("embeddings")
    target_dimension = len(sample_embeddings[0]) if sample_embeddings is not None and len(sample_embeddings) else 0
    if source_ids != target_ids or source_digest != target_digest:
        raise RuntimeError("Migrated collection does not preserve logical document identity/content/metadata")
    if target.count() != source.count() or target_dimension != provenance.dimension:
        raise RuntimeError("Migrated collection failed count or vector-dimension parity")

    legacy_collections = _normalize_legacy_hashing_metadata(client)
    return {
        "timestamp": created_at,
        "persist_dir": str(persist_dir),
        "backup_dir": str(backup_dir),
        "source_collection": source_name,
        "target_collection": target_name,
        "source_count": source.count(),
        "target_count": target.count(),
        "source_digest": source_digest,
        "target_digest": target_digest,
        "missing_ids": sorted(source_ids - target_ids),
        "extra_ids": sorted(target_ids - source_ids),
        "target_metadata": target.metadata,
        "target_dimension": target_dimension,
        "legacy_hashing_metadata_normalized": legacy_collections,
    }


def main() -> int:
    settings = get_settings()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="helpdesk_kb_multilingual_v1")
    parser.add_argument("--target", default="helpdesk_kb_multilingual_v2_sentence_transformer")
    parser.add_argument("--persist-dir", type=Path, default=Path(settings.chroma_persist_dir))
    parser.add_argument("--backup-dir", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    report = migrate(
        persist_dir=args.persist_dir.resolve(),
        source_name=args.source,
        target_name=args.target,
        backup_dir=args.backup_dir.resolve(),
        batch_size=args.batch_size,
        resume=args.resume,
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
