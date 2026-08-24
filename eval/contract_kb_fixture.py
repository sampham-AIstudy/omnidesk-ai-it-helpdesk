"""Deterministic, evaluation-only Contract KB builder; never reads data/chroma."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from eval.evaluation_contract import sha256_text_file

ROOT = Path(__file__).parent.parent
SOURCE_PATH = ROOT / "eval" / "fixtures" / "enterprise_contract_kb_v1.json"
EVAL_DIR = ROOT / "data" / "eval_chroma"
COLLECTION = "enterprise_contract_kb_v1"
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def load_documents(source_path: Path = SOURCE_PATH) -> list[dict[str, Any]]:
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "enterprise-contract-kb-v1":
        raise ValueError("unsupported contract KB schema")
    docs = payload["documents"]
    ids = [item["fixture_source_id"] for item in docs]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate contract source ID")
    return sorted(docs, key=lambda item: item["fixture_source_id"])


def contract_metadata(source_path: Path = SOURCE_PATH) -> dict[str, Any]:
    docs = load_documents(source_path)
    records = [{"id": item["fixture_source_id"], "content": item["content"], "metadata": {key: value for key, value in item.items() if key not in {"fixture_source_id", "title", "content"}}} for item in docs]
    return {
        "fixture_kb_contract": "enterprise-contract-kb-v1", "evaluation_only": True,
        "source_sha256": sha256_text_file(source_path), "document_count": len(docs),
        "chunk_count": len(docs), "chunk_id_digest": _hash([item["fixture_source_id"] for item in docs]),
        "metadata_digest": _hash(records), "embedding_model": EMBEDDING_MODEL,
        "embedding_dimension": 384, "distance_metric": "cosine",
    }


def build_contract_collection(*, path: Path = EVAL_DIR, source_path: Path = SOURCE_PATH, replace_mismatch: bool = False) -> dict[str, Any]:
    """Build once in an evaluation-owned directory; existing content must match."""
    docs, metadata = load_documents(source_path), contract_metadata(source_path)
    client = chromadb.PersistentClient(path=str(path), settings=ChromaSettings(anonymized_telemetry=False))
    names = {item.name for item in client.list_collections()}
    if COLLECTION in names:
        collection = client.get_collection(COLLECTION)
        if collection.count() != len(docs) or dict(collection.metadata or {}).get("source_sha256") != metadata["source_sha256"]:
            if not replace_mismatch:
                raise RuntimeError("existing eval contract collection does not match source")
            # The named target is under ``data/eval_chroma`` and is exclusively
            # evaluation-owned.  Replacing it is safe and makes the persisted
            # fixture precisely match its recorded schema hash.
            client.delete_collection(COLLECTION)
        else:
            return metadata
    from src.services.rag_service import embed_texts

    collection = client.create_collection(COLLECTION, metadata={"hnsw:space": "cosine", **metadata})
    collection.add(
        ids=[item["fixture_source_id"] for item in docs], documents=[item["content"] for item in docs],
        metadatas=[{"title": item["title"], "source_id": item["fixture_source_id"], "content_hash": hashlib.sha256(item["content"].encode()).hexdigest(), **{key: value for key, value in item.items() if key not in {"fixture_source_id", "title", "content"}}} for item in docs],
        embeddings=embed_texts([item["content"] for item in docs]),
    )
    if collection.count() != len(docs):
        raise RuntimeError("eval collection count mismatch")
    return metadata
