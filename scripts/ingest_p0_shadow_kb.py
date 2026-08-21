"""Create a guarded P0 shadow collection without changing the canonical KB."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import chromadb
from chromadb.config import Settings as ChromaSettings

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import get_settings  # noqa: E402
from src.services.rag_service import embed_texts, scan_indirect_injection  # noqa: E402

ALLOWED_SOURCE_TYPES = {
    "internal_curated_kb",
    "approved_internal_source",
    "official_vendor_documentation",
}
REQUIRED_FIELDS = {
    "source_id", "source_type", "authority", "canonical_url_or_path", "vendor",
    "product", "version", "topic", "owner", "approval_status", "reviewed_at",
    "expires_at", "content_hash",
}
OFFICIAL_HOSTS = {
    "Fortinet": {"docs.fortinet.com"},
    "Microsoft": {"learn.microsoft.com", "support.microsoft.com"},
    "Mozilla": {"developer.mozilla.org"},
}
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", re.I),
    re.compile(r"\b(?:api[_ -]?key|access[_ -]?token|secret)\s*[:=]\s*[^\s]{8,}", re.I),
)
PII_PATTERNS = (re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b"),)


def canonicalize_url_or_path(value: str) -> str:
    value = value.strip()
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"}:
        return str(Path(value).as_posix())
    query = urlencode(sorted((key, val) for key, val in parse_qsl(parsed.query) if not key.startswith("utm_")))
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path.rstrip("/"), query, ""))


def sanitize_content(value: str) -> str:
    value = value.replace("\x00", "")
    value = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f]", "", value)
    return re.sub(r"[ \t]+", " ", value).strip()


def content_sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _source_rejection(source: dict, reason: str) -> dict:
    return {"source_id": source.get("source_id", "UNKNOWN"), "reason": reason}


def validate_and_prepare(sources: list[dict]) -> tuple[list[dict], list[dict], int]:
    """Validate the staging manifest and return safe unique source records."""
    accepted: list[dict] = []
    rejected: list[dict] = []
    seen_ids: set[str] = set()
    seen_hashes: set[str] = set()
    duplicates = 0
    for raw in sources:
        missing = sorted(field for field in REQUIRED_FIELDS if field not in raw)
        if missing:
            rejected.append(_source_rejection(raw, f"missing required manifest fields: {', '.join(missing)}"))
            continue
        if raw["source_type"] not in ALLOWED_SOURCE_TYPES:
            rejected.append(_source_rejection(raw, "source type is not approved for P0"))
            continue
        source = deepcopy(raw)
        source["canonical_url_or_path"] = canonicalize_url_or_path(source["canonical_url_or_path"])
        parsed = urlsplit(source["canonical_url_or_path"])
        if source["source_type"] == "official_vendor_documentation":
            allowed_hosts = OFFICIAL_HOSTS.get(source["vendor"], set())
            if parsed.scheme != "https" or parsed.hostname not in allowed_hosts:
                rejected.append(_source_rejection(source, "not an allowlisted official vendor documentation URL"))
                continue
        source["content"] = sanitize_content(str(source.get("content", "")))
        if not source["content"]:
            rejected.append(_source_rejection(source, "empty content"))
            continue
        if scan_indirect_injection(source["content"]):
            rejected.append(_source_rejection(source, "prompt-injection indicator detected"))
            continue
        if any(pattern.search(source["content"]) for pattern in SECRET_PATTERNS):
            rejected.append(_source_rejection(source, "secret indicator detected"))
            continue
        if any(pattern.search(source["content"]) for pattern in PII_PATTERNS):
            rejected.append(_source_rejection(source, "PII indicator detected"))
            continue
        source["content_hash"] = content_sha256(source["content"])
        if source["source_id"] in seen_ids or source["content_hash"] in seen_hashes:
            duplicates += 1
            continue
        seen_ids.add(source["source_id"])
        seen_hashes.add(source["content_hash"])
        accepted.append(source)
    return accepted, rejected, duplicates


def chunk_source(source: dict, chunk_size: int = 1100) -> list[dict]:
    """Chunk deterministically, retaining topic-specific document identities."""
    content = source["content"]
    parts = [content[index:index + chunk_size] for index in range(0, len(content), chunk_size)]
    documents = []
    for index, part in enumerate(parts, start=1):
        doc_id = f"{source['source_id'].lower()}-c{index:03d}"
        documents.append({
            "doc_id": doc_id,
            "content": part,
            "metadata": {
                "title": source["title"], "category": "network", "tags": source["tags"],
                # Retain the existing ranking source value; source_type preserves the manifest class.
                "source": "official_web_documentation" if source["source_type"] == "official_vendor_documentation" else source["source_type"],
                "source_type": source["source_type"], "source_id": source["source_id"],
                "source_url": source["canonical_url_or_path"], "canonical_source_id": source["source_id"],
                "authority": source["authority"], "vendor": source["vendor"], "product": source["product"],
                "version": source["version"], "topic": source["topic"], "owner": source["owner"],
                "approval_status": source["approval_status"], "reviewed_at": source["reviewed_at"],
                "expires_at": source["expires_at"], "content_hash": source["content_hash"],
                "company_unit": "all", "department": "", "applicable_to_all": True,
            },
        })
    return documents


def _source_records(collection, batch_size: int) -> list[dict]:
    records: list[dict] = []
    for offset in range(0, collection.count(), batch_size):
        batch = collection.get(limit=batch_size, offset=offset, include=["documents", "metadatas", "embeddings"])
        records.extend({"id": item_id, "document": document, "metadata": metadata, "embedding": embedding}
                       for item_id, document, metadata, embedding in zip(batch["ids"], batch["documents"], batch["metadatas"], batch["embeddings"]))
    return records


def create_shadow(*, source_name: str, target_name: str, manifest_path: Path, report_path: Path, batch_size: int = 64) -> dict:
    """Copy canonical records exactly, then add validated P0 chunks to a new collection only."""
    settings = get_settings()
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    accepted, rejected, duplicates = validate_and_prepare(payload["sources"])
    chunks = [chunk for source in accepted for chunk in chunk_source(source)]
    client = chromadb.PersistentClient(path=str(Path(settings.chroma_persist_dir)), settings=ChromaSettings(anonymized_telemetry=False))
    names = {collection.name for collection in client.list_collections()}
    if source_name not in names:
        raise ValueError(f"canonical source collection does not exist: {source_name}")
    if target_name in names:
        raise FileExistsError(f"refusing to mutate existing shadow collection: {target_name}")
    source = client.get_collection(source_name)
    source_records = _source_records(source, batch_size)
    source_metadata = dict(source.metadata or {})
    target_metadata = {key: value for key, value in source_metadata.items() if key != "hnsw:space"}
    target_metadata.update({"shadow_version": "v3", "shadow_only": True, "source_collection": source_name,
                            "p0_batch_id": payload["batch_id"], "created_at": datetime.now(UTC).isoformat()})
    target = client.create_collection(name=target_name, metadata={"hnsw:space": "cosine", **target_metadata})
    for start in range(0, len(source_records), batch_size):
        batch = source_records[start:start + batch_size]
        target.add(ids=[item["id"] for item in batch], documents=[item["document"] for item in batch],
                   metadatas=[item["metadata"] for item in batch], embeddings=[item["embedding"] for item in batch])
    if chunks:
        target.add(ids=[item["doc_id"] for item in chunks], documents=[item["content"] for item in chunks],
                   metadatas=[item["metadata"] for item in chunks], embeddings=embed_texts([item["content"] for item in chunks]))
    if source.count() != len(source_records) or target.count() != source.count() + len(chunks):
        raise RuntimeError("shadow count verification failed")
    receipt = {"batch_id": payload["batch_id"], "internal_procedure_status": payload["internal_procedure_status"],
               "canonical_collection": source_name, "shadow_collection": target_name,
               "documents": len(accepted), "chunks": len(chunks),
               "canonical_sources": len({item["canonical_url_or_path"] for item in accepted}),
               "duplicates_removed": duplicates, "rejected_sources": rejected,
               "source_count_before": source.count(), "shadow_count_after": target.count(),
               "embedding_model": target.metadata.get("embedding_model"), "embedding_backend": target.metadata.get("embedding_backend"),
               "manifest": [{field: source[field] for field in REQUIRED_FIELDS} for source in accepted]}
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="helpdesk_kb_multilingual_v2_sentence_transformer")
    parser.add_argument("--target", default="helpdesk_kb_multilingual_v3_shadow")
    parser.add_argument("--manifest", type=Path, default=ROOT / "data" / "p0_shadow_v3_sources.json")
    parser.add_argument("--report", type=Path, default=ROOT / "eval" / "results" / "p0_shadow_v3_ingestion.json")
    args = parser.parse_args()
    print(json.dumps(create_shadow(source_name=args.source, target_name=args.target, manifest_path=args.manifest, report_path=args.report), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
