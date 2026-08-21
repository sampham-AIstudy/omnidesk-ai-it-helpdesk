"""Create a metadata-only Step 6B shadow without changing canonical v3.

The experiment is deliberately conservative: relationship fields are added only
where the authoritative staging manifest proves the source/chunk structure.
It never re-chunks text, derives adjacency from Chroma order, or overwrites an
existing collection.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ingest_p0_shadow_kb import chunk_source, validate_and_prepare  # noqa: E402
from src.config import get_settings  # noqa: E402

ACTIVE_V3_COLLECTION = "helpdesk_kb_multilingual_v3_sentence_transformer"
DEFAULT_TARGET = "helpdesk_kb_multilingual_v3_hierarchical_shadow"
_HEADING = re.compile(r"(?m)^#{1,6}\s|^\d+[.)]\s|^[A-Z][^\n]{1,80}:\s*$")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def classify_raw_source(source: dict[str, Any]) -> dict[str, Any]:
    """Classify only structure evidenced by the authoritative raw manifest."""
    chunks = chunk_source(source)
    content = str(source["content"])
    heading_count = len(_HEADING.findall(content))
    if len(chunks) == 1:
        classification = "SINGLE_CHUNK"
    elif heading_count:
        classification = "MULTI_CHUNK_HIERARCHICAL"
    else:
        classification = "MULTI_CHUNK_FLAT"
    return {
        "source_id": source["source_id"],
        "canonical_url_or_path": source["canonical_url_or_path"],
        "content_chars": len(content),
        "deterministic_chunk_count": len(chunks),
        "heading_count": heading_count,
        "classification": classification,
        "document_id": source["source_id"],
    }


def load_manifest_structure(manifest_path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    accepted, rejected, duplicates = validate_and_prepare(payload["sources"])
    if rejected or duplicates:
        raise ValueError("raw manifest has rejected or duplicate sources")
    return accepted, [classify_raw_source(source) for source in accepted]


def metadata_for_proven_single_chunk(source: dict[str, Any]) -> dict[str, Any]:
    """Return only facts proved by a single authoritative source record."""
    return {
        "document_id": source["source_id"],
        "canonical_source_id": source["source_id"],
        "chunk_index": 0,
        "total_chunks": 1,
        "document_type": "support_article",
        "expansion_eligible": False,
        "hierarchical_classification": "SINGLE_CHUNK",
        "content_hash": source["content_hash"],
    }


def _records(collection: Any, batch_size: int = 64) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for offset in range(0, collection.count(), batch_size):
        batch = collection.get(
            limit=batch_size,
            offset=offset,
            include=["documents", "metadatas", "embeddings"],
        )
        records.extend(
            {
                "id": item_id,
                "document": document,
                "metadata": metadata or {},
                "embedding": embedding,
            }
            for item_id, document, metadata, embedding in zip(
                batch["ids"], batch["documents"], batch["metadatas"], batch["embeddings"]
            )
        )
    return records


def create_shadow(
    *, source_name: str, target_name: str, manifest_path: Path, report_path: Path
) -> dict[str, Any]:
    """Copy v3 exactly and annotate only manifest-proven single chunks."""
    settings = get_settings()
    if source_name != ACTIVE_V3_COLLECTION or target_name == source_name:
        raise ValueError("the Step 6B experiment may only copy active v3 into a distinct shadow")
    client = chromadb.PersistentClient(
        path=str(Path(settings.chroma_persist_dir)), settings=ChromaSettings(anonymized_telemetry=False)
    )
    names = {item.name for item in client.list_collections()}
    if source_name not in names:
        raise ValueError(f"source collection does not exist: {source_name}")
    if target_name in names:
        raise FileExistsError(f"refusing to overwrite existing shadow collection: {target_name}")

    sources, structure = load_manifest_structure(manifest_path)
    by_source_id = {str(source["source_id"]): source for source in sources}
    source = client.get_collection(source_name)
    records = _records(source)
    target_metadata = dict(source.metadata or {})
    target_metadata.update(
        {
            "shadow_only": True,
            "shadow_experiment": "step6b_hierarchical_metadata_v1",
            "source_collection": source_name,
            "relationship_policy": "authoritative_manifest_only",
            "created_at": datetime.now(UTC).isoformat(),
        }
    )
    target = client.create_collection(
        name=target_name,
        metadata={"hnsw:space": "cosine", **target_metadata},
    )

    annotated_ids: list[str] = []
    for start in range(0, len(records), 64):
        batch = records[start:start + 64]
        metadatas: list[dict[str, Any]] = []
        for item in batch:
            metadata = dict(item["metadata"])
            raw_source = by_source_id.get(str(metadata.get("source_id") or ""))
            if raw_source is not None:
                metadata.update(metadata_for_proven_single_chunk(raw_source))
                annotated_ids.append(str(item["id"]))
            metadatas.append(metadata)
        target.add(
            ids=[str(item["id"]) for item in batch],
            documents=[str(item["document"] or "") for item in batch],
            metadatas=metadatas,
            embeddings=[item["embedding"] for item in batch],
        )

    expected_ids = {f"{source['source_id'].lower()}-c001" for source in sources}
    if target.count() != source.count() or set(annotated_ids) != expected_ids:
        raise RuntimeError("shadow integrity failed: source count or manifest-proven record mapping differs")

    report = {
        "experiment": "step6b_hierarchical_metadata_v1",
        "source_collection": source_name,
        "shadow_collection": target_name,
        "source_count": source.count(),
        "shadow_count": target.count(),
        "content_or_embedding_rechunked": False,
        "relationship_policy": "authoritative_manifest_only",
        "metadata_contract": {
            "required_for_eligible": [
                "document_id", "canonical_source_id", "parent_document_id", "section_id",
                "section_heading", "chunk_index", "total_chunks", "document_type",
                "expansion_eligible", "source_type", "topic", "authority", "content_hash",
            ],
            "acl_fields_preserved": ["company_unit", "department", "applicable_to_all"],
        },
        "raw_source_structure": structure,
        "annotated_single_chunk_ids": sorted(annotated_ids),
        "eligible_hierarchical_source_count": 0,
        "created_at": datetime.now(UTC).isoformat(),
        "manifest_sha256": _sha256(manifest_path.read_bytes()),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=ACTIVE_V3_COLLECTION)
    parser.add_argument("--target", default=DEFAULT_TARGET)
    parser.add_argument("--manifest", type=Path, default=ROOT / "data" / "p0_shadow_v3_sources.json")
    parser.add_argument("--report", type=Path, default=ROOT / "eval" / "results" / "hierarchical_metadata_shadow_v1.json")
    args = parser.parse_args()
    print(json.dumps(create_shadow(source_name=args.source, target_name=args.target, manifest_path=args.manifest, report_path=args.report), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
