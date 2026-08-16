"""RAG Service — ChromaDB vector store cho knowledge base."""
from __future__ import annotations

import asyncio
import hashlib
import logging
import math
import re
import threading
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_community.embeddings import HuggingFaceEmbeddings

from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Singleton instances
_chroma_client: chromadb.ClientAPI | None = None
_collection: chromadb.Collection | None = None
_ticket_duplicate_collection: chromadb.Collection | None = None
_episodic_memory_collection: chromadb.Collection | None = None
_embedder: HuggingFaceEmbeddings | _HashingEmbedder | None = None

_SEARCH_STOPWORDS = {
    "a", "an", "and", "for", "in", "is", "of", "on", "the", "to", "with",
    "bị", "có", "của", "được", "không", "là", "máy", "tôi", "trong", "và",
}
_SEARCH_STOPWORDS.update({
    "bi", "bo", "cho", "co", "cua", "duoc", "em", "gi", "hay", "khong", "la",
    "luc", "may", "nhanh", "qua", "quy", "toi", "trinh", "trong", "va", "voi",
})

_QUERY_EXPANSIONS = {
    ("man hinh xanh", "blue screen", "bsod"): "BSOD blue screen stop code Safe Mode Startup Repair",
    ("may cham", "cham qua", "lag", "treo"): "performance slow lag CPU RAM Task Manager",
    ("mang lag", "wifi yeu", "mat ket noi"): "WiFi wireless network access point router",
    ("ket outbox", "stuck outbox"): "Outlook Outbox Exchange profile send receive",
    ("khong pair", "bluetooth"): "Bluetooth pairing device connection",
    ("ne dlp", "bypass dlp"): "DLP data loss prevention security policy exfiltration",
}


def _normalize_search_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).casefold()
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def is_context_dependent(query: str) -> bool:
    """Check if query is vague or context-dependent (e.g., 'nó vẫn bị lỗi', 'cái vpn đó', 'lỗi như cũ')."""
    query_lower = query.lower().strip()
    if len(query_lower.split()) <= 3:
        return True
    vague_markers = ["vẫn", "như cũ", "như lúc nãy", "cái đó", "nó bị", "lại bị", "lỗi đó", "không được"]
    return any(marker in query_lower for marker in vague_markers)


def rewrite_query_with_context(query: str, history_summary: str = "") -> str:
    """Rewrite context-dependent short queries using recent conversation summary."""
    if not history_summary or not is_context_dependent(query):
        return query
    logger.info(f"Conditioned Query Rewrite applied: '{query}' -> context: '{history_summary[:100]}'")
    return f"{history_summary.strip()[:120]} {query.strip()}"


def _expand_query(query: str) -> str:
    normalized = _normalize_search_text(query)
    additions = [
        expansion
        for triggers, expansion in _QUERY_EXPANSIONS.items()
        if any(trigger in normalized for trigger in triggers)
    ]
    if not additions:
        return query
    return f"{query} {' '.join(additions)}"


def _search_tokens(value: str) -> set[str]:
    normalized = _normalize_search_text(value)
    return {
        token
        for token in re.findall(r"[^\W_]+", normalized, flags=re.UNICODE)
        if len(token) > 1 and token not in _SEARCH_STOPWORDS
    }


def _lexical_score(query: str, metadata: dict, content: str = "") -> float:
    """Boost exact product/error terms that dense retrieval can underweight."""
    query_tokens = _search_tokens(query)
    searchable = (
        f"{metadata.get('title', '')} {metadata.get('tags', '')} "
        f"{metadata.get('solution', '')} {content}"
    )
    document_tokens = _search_tokens(searchable)
    if not query_tokens or not document_tokens:
        return 0.0
    return len(query_tokens & document_tokens) / len(query_tokens)


_embedder_lock = threading.Lock()


class _HashingEmbedder:
    """Deterministic, low-memory fallback when a transformer cannot run."""

    dimensions = 384

    def _embed(self, text: str) -> list[float]:
        values = [0.0] * self.dimensions
        for token in _search_tokens(text):
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            index = int.from_bytes(digest[:4], "little") % self.dimensions
            values[index] += 1.0 if digest[4] & 1 else -1.0
        norm = math.sqrt(sum(value * value for value in values))
        return [value / norm for value in values] if norm else values

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


from dataclasses import dataclass


class EmbeddingProvenanceError(RuntimeError):
    """Raised when collection embedding provenance conflicts with runtime expectations."""


class EmbeddingInitializationError(RuntimeError):
    """Raised when the configured embedding backend cannot be initialized."""


@dataclass(frozen=True)
class EmbeddingProvenance:
    backend: str
    provider: str
    model: str
    dimension: int
    normalized: bool = True


def effective_embedding_provenance() -> EmbeddingProvenance:
    backend = settings.embedding_backend
    if backend == "sentence_transformer":
        return EmbeddingProvenance(
            backend="sentence_transformer",
            provider="sentence_transformers",
            model=settings.embedding_model,
            dimension=384,
            normalized=True,
        )
    elif backend == "hashing":
        return EmbeddingProvenance(
            backend="hashing",
            provider="local_hashing",
            model="blake2b-token-hashing-v1",
            dimension=384,
            normalized=True,
        )
    raise EmbeddingProvenanceError(f"Unsupported embedding backend: {backend}")


def validate_collection_embedding_provenance(
    collection: Any, expected: EmbeddingProvenance | None = None
) -> EmbeddingProvenance:
    expected = expected or effective_embedding_provenance()
    metadata = getattr(collection, "metadata", None) or {}
    collection_backend = metadata.get("embedding_backend")
    if collection_backend and collection_backend != expected.backend:
        raise EmbeddingProvenanceError(
            f"Collection '{getattr(collection, 'name', 'unknown')}' embedding backend '{collection_backend}' does not match expected backend '{expected.backend}'"
        )
    return expected


_embedders: dict[str, Any] = {}
_embedder_lock = threading.Lock()


def _get_embedder(backend: str | None = None) -> Any:
    requested_backend = backend or settings.embedding_backend
    if requested_backend not in {"sentence_transformer", "hashing"}:
        raise EmbeddingProvenanceError(f"Unsupported embedding backend: {requested_backend}")

    if requested_backend not in _embedders:
        with _embedder_lock:
            if requested_backend not in _embedders:
                if requested_backend == "hashing":
                    _embedders[requested_backend] = _HashingEmbedder()
                else:
                    logger.info("Loading embedding model (%s)...", settings.embedding_model)
                    try:
                        _embedders[requested_backend] = HuggingFaceEmbeddings(
                            model_name=settings.embedding_model,
                            model_kwargs={"device": "cpu", "local_files_only": not settings.embedding_allow_network_downloads},
                            encode_kwargs={"normalize_embeddings": True},
                        )
                    except Exception as exc:
                        raise EmbeddingInitializationError(
                            f"Configured sentence-transformer is unavailable: {settings.embedding_model}"
                        ) from exc
    return _embedders[requested_backend]


def get_chroma_client() -> chromadb.ClientAPI:
    global _chroma_client
    if _chroma_client is None:
        persist_dir = Path(settings.chroma_persist_dir)
        persist_dir.mkdir(parents=True, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(
            path=str(persist_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _chroma_client


def get_collection() -> chromadb.Collection:
    global _collection
    if _collection is None:
        client = get_chroma_client()
        col = client.get_or_create_collection(
            name=settings.chroma_collection_name,
            metadata={
                "hnsw:space": "cosine",
                "embedding_model": settings.embedding_model,
                "embedding_backend": settings.embedding_backend,
                "embedding_provider": "sentence_transformers" if settings.embedding_backend == "sentence_transformer" else "local_hashing",
                "embedding_dimension": 384,
                "embedding_normalized": True,
            },
        )
        validate_collection_embedding_provenance(col)
        _collection = col
    return _collection


def get_ticket_duplicate_collection() -> chromadb.Collection:
    """Ticket-only semantic index using the same Chroma client and embedding model as RAG."""
    global _ticket_duplicate_collection
    if _ticket_duplicate_collection is None:
        _ticket_duplicate_collection = get_chroma_client().get_or_create_collection(
            name="helpdesk_ticket_duplicates_v1",
            metadata={
                "hnsw:space": "cosine",
                "embedding_model": settings.embedding_model,
                "embedding_backend": settings.embedding_backend,
                "purpose": "semantic_duplicate_detection",
            },
        )
    return _ticket_duplicate_collection


def get_episodic_memory_collection() -> chromadb.Collection:
    """Episodic memory shares the existing Chroma client and embedding backend."""
    global _episodic_memory_collection
    if _episodic_memory_collection is None:
        _episodic_memory_collection = get_chroma_client().get_or_create_collection(
            name="helpdesk_episodic_memory_v1",
            metadata={
                "hnsw:space": "cosine",
                "embedding_model": settings.embedding_model,
                "embedding_backend": settings.embedding_backend,
                "purpose": "zero_token_episodic_memory",
            },
        )
    return _episodic_memory_collection


def embed_texts(texts: list[str]) -> list[list[float]]:
    embedder = _get_embedder()
    return embedder.embed_documents(texts)


@lru_cache(maxsize=1024)
def embed_query(text: str) -> list[float]:
    embedder = _get_embedder()
    return embedder.embed_query(text)


def embed_query_for_collection(text: str, collection: Any = None) -> list[float]:
    """Embed query using the collection's backend, falling back to configured embedder."""
    if collection is None:
        return embed_query(text)
    metadata = getattr(collection, "metadata", None) or {}
    backend = metadata.get("embedding_backend") or settings.embedding_backend
    if backend not in {"sentence_transformer", "hashing"}:
        raise EmbeddingProvenanceError(f"Collection has no supported embedding backend: {backend}")
    embedder = _get_embedder(backend)
    return embedder.embed_query(text)



def index_document(
    doc_id: str,
    content: str,
    metadata: dict,
) -> None:
    """Index một KB entry vào ChromaDB."""
    collection = get_collection()
    embedding = embed_query(content)
    collection.upsert(
        ids=[doc_id],
        embeddings=[embedding],
        documents=[content],
        metadatas=[metadata],
    )


def index_documents(documents: list[dict]) -> None:
    """Batch-upsert documents to avoid one embedding call per RAG chunk."""
    if not documents:
        return
    collection = get_collection()
    contents = [item["content"] for item in documents]
    collection.upsert(
        ids=[item["doc_id"] for item in documents],
        embeddings=embed_texts(contents),
        documents=contents,
        metadatas=[item["metadata"] for item in documents],
    )


def get_indexed_document_ids(doc_ids: list[str]) -> set[str]:
    if not doc_ids:
        return set()
    result = get_collection().get(ids=doc_ids, include=["metadatas"])
    return set(result.get("ids", []))


def delete_document(doc_id: str) -> None:
    """Remove a KB entry from ChromaDB by document id."""
    collection = get_collection()
    collection.delete(ids=[doc_id])


def _metadata_allowed(
    metadata: dict,
    user_company_unit: str | None = None,
    user_department: str | None = None,
) -> bool:
    """Return True when KB metadata is visible to the user's org scope."""
    if not user_company_unit and not user_department:
        return True

    applicable_to_all = metadata.get("applicable_to_all", True)
    if isinstance(applicable_to_all, str):
        applicable_to_all = applicable_to_all.lower() in ("true", "1", "yes", "all")

    doc_company = metadata.get("company_unit") or "all"
    doc_department = metadata.get("department") or ""

    company_allowed = applicable_to_all or doc_company in ("all", user_company_unit)
    department_allowed = not doc_department or doc_department == user_department
    return company_allowed and department_allowed


_rag_query_cache: dict[str, list[dict]] = {}
_MAX_RAG_CACHE_SIZE = 512


INDIRECT_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|system)\s+instructions?", re.IGNORECASE),
    re.compile(r"reveal\s+(your\s+)?system\s+prompt", re.IGNORECASE),
    re.compile(r"you\s+are\s+now", re.IGNORECASE),
    re.compile(r"override\s+policy", re.IGNORECASE),
    re.compile(r"return\s+secrets?", re.IGNORECASE),
    re.compile(r"игнорир\w*\s+(?:все\s+)?(?:предыдущ\w*|инструкц\w*|огранич\w*)", re.IGNORECASE),
    re.compile(r"переопределени\w*\s+систем\w*", re.IGNORECASE),
    re.compile(r"(?:раскрой|перечисл|извлеч)\w*.*(?:системн\w*\s+(?:подсказ|инструкц)|секрет\w*|токен\w*|парол\w*)", re.IGNORECASE),
]


def scan_indirect_injection(content: str) -> bool:
    """Detect if a retrieved KB document contains indirect prompt injection payloads."""
    if not content:
        return False
    return any(p.search(content) for p in INDIRECT_INJECTION_PATTERNS)


def search_similar(
    query: str,
    n_results: int = 5,
    category_filter: str | None = None,
    user_company_unit: str | None = None,
    user_department: str | None = None,
) -> list[dict]:
    """Semantic search KB entries with pre-retrieval ACL, security-scoped caching & hybrid RRF scoring."""
    cache_key = f"{user_company_unit or 'all'}:{user_department or 'all'}:{category_filter or 'none'}:{n_results}:{query.strip().lower()}"
    if cache_key in _rag_query_cache:
        return _rag_query_cache[cache_key]

    try:
        collection = get_collection()
    except EmbeddingProvenanceError as exc:
        logger.warning(f"Incompatible KB collection embedding provenance: {exc}")
        return []

    expanded_query = _expand_query(query)
    query_embedding = embed_query(expanded_query)

    # Build Pre-Retrieval ACL Filter
    where_conditions = []
    if category_filter:
        where_conditions.append({"category": category_filter})

    if user_company_unit and user_company_unit != "corporate":
        where_conditions.append({
            "$or": [
                {"applicable_to_all": True},
                {"company_unit": "all"},
                {"company_unit": user_company_unit}
            ]
        })

    where_filter = {}
    if len(where_conditions) == 1:
        where_filter = where_conditions[0]
    elif len(where_conditions) > 1:
        where_filter = {"$and": where_conditions}

    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(max(n_results * 8, n_results), collection.count() or 1),
            where=where_filter if where_filter else None,
            include=["documents", "metadatas", "distances"],
        )
    except Exception as e:
        logger.warning(f"ChromaDB query error with ACL filter: {e}")
        # Fallback query without where clause if ChromaDB $or is unsupported
        try:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=min(max(n_results * 8, n_results), collection.count() or 1),
                include=["documents", "metadatas", "distances"],
            )
        except Exception as ex:
            logger.error(f"ChromaDB fallback query error: {ex}")
            return []

    docs = []
    if results and results.get("documents"):
        for i, doc in enumerate(results["documents"][0]):
            metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
            # Double check ACL & Indirect Prompt Injection
            if not _metadata_allowed(metadata, user_company_unit, user_department):
                continue

            if scan_indirect_injection(doc):
                logger.warning(f"Indirect Prompt Injection detected & blocked in KB doc: {metadata.get('title', 'Unknown')}")
                continue

            docs.append({
                # Chroma returns persisted IDs for every query result.  Carry
                # them through the pipeline so the answer model can cite a
                # real evidence identifier instead of inventing one.
                "doc_id": results.get("ids", [[]])[0][i] if results.get("ids") else "",
                "content": doc,
                "metadata": metadata,
                "distance": results["distances"][0][i] if results.get("distances") else 1.0,
                "semantic_score": max(0.0, 1.0 - (results["distances"][0][i] if results.get("distances") else 1.0)),
            })

    for item in docs:
        lexical_score = _lexical_score(expanded_query, item["metadata"], item.get("content", ""))
        item["lexical_score"] = lexical_score
        item["relevance_score"] = min(
            1.0,
            0.82 * item["semantic_score"] + 0.35 * lexical_score,
        )

    docs.sort(key=lambda item: item["relevance_score"], reverse=True)
    final_docs = docs[:n_results]

    if len(_rag_query_cache) >= _MAX_RAG_CACHE_SIZE:
        _rag_query_cache.clear()
    _rag_query_cache[cache_key] = final_docs

    return final_docs


def get_document_by_id(
    doc_id: str,
    *,
    user_company_unit: str | None = None,
    user_department: str | None = None,
) -> dict | None:
    """Load one retrieved source for navigation, preserving KB ACLs.

    This reader is deliberately separate from semantic retrieval: a client can
    only open a persisted source ID and never use this endpoint to search
    arbitrary Chroma metadata.
    """
    if not doc_id or len(doc_id) > 200:
        return None
    try:
        result = get_collection().get(
            ids=[doc_id], include=["documents", "metadatas"]
        )
    except Exception as exc:
        logger.warning("Could not load RAG source %s: %s", doc_id, exc)
        return None

    documents = result.get("documents", []) if result else []
    metadatas = result.get("metadatas", []) if result else []
    ids = result.get("ids", []) if result else []
    if not documents or not ids:
        return None
    content = str(documents[0] or "")
    metadata = metadatas[0] or {}
    if not _metadata_allowed(metadata, user_company_unit, user_department):
        return None
    if scan_indirect_injection(content):
        logger.warning("Blocked unsafe RAG source navigation for %s", doc_id)
        return None
    return {"doc_id": str(ids[0]), "content": content, "metadata": metadata}


def get_document_by_title(
    title: str,
    *,
    user_company_unit: str | None = None,
    user_department: str | None = None,
) -> dict | None:
    """Resolve legacy source labels to one exact, ACL-visible RAG document."""
    if not title or len(title) > 255:
        return None
    try:
        result = get_collection().get(
            where={"title": title}, include=["documents", "metadatas"]
        )
    except Exception as exc:
        logger.warning("Could not resolve RAG source title: %s", exc)
        return None
    # Chroma equality may not match visually identical Unicode text when old
    # sources were indexed with a different normalization form.  Legacy source
    # labels need exact-title compatibility, never semantic best-match lookup.
    if not result.get("ids"):
        try:
            all_sources = get_collection().get(include=["documents", "metadatas"])
            expected = unicodedata.normalize("NFC", title).casefold()
            matching = [
                index for index, metadata in enumerate(all_sources.get("metadatas", []))
                if unicodedata.normalize("NFC", str((metadata or {}).get("title") or "")).casefold() == expected
            ]
            result = {
                key: [values[index] for index in matching]
                for key, values in all_sources.items()
                if isinstance(values, list)
            }
        except Exception as exc:
            logger.warning("Could not normalize legacy RAG source title: %s", exc)
            return None
    for doc_id, content, metadata in zip(
        result.get("ids", []),
        result.get("documents", []),
        result.get("metadatas", []),
    ):
        metadata = metadata or {}
        content = str(content or "")
        if (
            _metadata_allowed(metadata, user_company_unit, user_department)
            and not scan_indirect_injection(content)
        ):
            return {"doc_id": str(doc_id), "content": content, "metadata": metadata}
    return None



async def search_similar_async(
    query: str,
    n_results: int = 5,
    category_filter: str | None = None,
    user_company_unit: str | None = None,
    user_department: str | None = None,
) -> list[dict]:
    """Non-blocking async wrapper cho search_similar."""
    return await asyncio.to_thread(
        search_similar,
        query=query,
        n_results=n_results,
        category_filter=category_filter,
        user_company_unit=user_company_unit,
        user_department=user_department,
    )


def get_collection_count() -> int:
    try:
        client = get_chroma_client()
        col = client.get_collection(COLLECTION_NAME)
        return col.count()
    except Exception:
        return 0
