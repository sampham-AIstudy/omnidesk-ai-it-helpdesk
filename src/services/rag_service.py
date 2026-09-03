"""RAG Service — ChromaDB vector store cho knowledge base."""
from __future__ import annotations

import asyncio
import hashlib
import logging
import math
import os
import re
import sys
import threading

# Mitigate native SentenceTransformer / safetensors async loader race conditions on Windows.
if sys.platform == "win32":
    os.environ.setdefault("HF_DEACTIVATE_ASYNC_LOAD", "1")
import unicodedata
import urllib.parse
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import chromadb
import httpx
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

# Source Authority Hierarchy for deterministic bounded ranking
SOURCE_AUTHORITY_FACTORS: dict[str, float] = {
    "internal_curated_kb": 1.40,        # Tier 1: Canonical Internal KB / Runbooks
    "approved_internal_source": 1.20,   # Tier 1.5: Approved Internal Policies
    "official_web_documentation": 1.00, # Tier 2: External Vendor Documentation
    "historical_resolved_ticket": 0.95, # Tier 3: Episodic Ticket Resolutions
    "NO_SOURCE_KEY": 0.90,              # Tier 4: Uncategorized / Auto KB
}


def get_canonical_source_id(doc_id: str, metadata: dict[str, Any] | None = None) -> str:
    """Derive canonical logical document ID for deduplication and grouping."""
    meta = metadata or {}
    source_url = meta.get("source_url", "").strip()
    if source_url:
        try:
            parsed = urllib.parse.urlparse(source_url)
            norm_url = f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{parsed.path.lower().rstrip('/')}"
            if parsed.query:
                norm_url = f"{norm_url}?{parsed.query}"
            return f"url:{norm_url}"
        except Exception:
            return f"url:{source_url.lower().rstrip('/')}"

    if meta.get("parent_id"):
        return f"parent:{meta['parent_id']}"
    if meta.get("canonical_source_id"):
        return f"canon:{meta['canonical_source_id']}"

    if doc_id.startswith("web-"):
        m = re.match(r"^(web-.+)-\d{3,}$", doc_id)
        if m:
            return f"web_base:{m.group(1)}"

    if doc_id.startswith("kb-"):
        m = re.match(r"^(kb-\d+)[_-](?:chunk|part|c)[_-]?\d+$", doc_id, re.IGNORECASE)
        if m:
            return f"kb_base:{m.group(1)}"
        return f"kb:{doc_id}"

    return doc_id


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
    vague_markers = [
        "vẫn", "như cũ", "như lúc nãy", "cái đó", "nó bị", "lại bị", "lỗi đó", "không được",
        "còn cách nào", "khác không", "còn không", "thế nào nữa", "thêm không", "ngoài ra", "còn gì",
    ]
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


class _RemoteOnnxEmbedder:
    """Embeds texts by calling the remote ONNX microservice with strict response validation."""

    def __init__(self):
        self.url = settings.embedding_service_url.rstrip("/") + "/v1/embeddings"
        self.token = settings.embedding_service_token
        self.timeout = settings.embedding_service_timeout_seconds
        self.dimensions = settings.embedding_dimensions
        self._client: httpx.Client | None = None
        self._lock = threading.Lock()

    def _get_client(self) -> httpx.Client:
        with self._lock:
            if self._client is None or self._client.is_closed:
                self._client = httpx.Client(timeout=self.timeout)
            return self._client

    def close(self) -> None:
        """Close the underlying HTTP client and release connection pool resources."""
        with self._lock:
            if self._client is not None:
                if not self._client.is_closed:
                    try:
                        self._client.close()
                    except Exception as exc:
                        logger.warning("Error closing _RemoteOnnxEmbedder client: %s", exc)
                self._client = None

    def _call_api(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        try:
            client = self._get_client()
            response = client.post(
                self.url,
                json={"texts": texts},
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
            raw_embeddings: list[Any] = []
            if "embeddings" in data and isinstance(data["embeddings"], list):
                raw_embeddings = data["embeddings"]
            elif "data" in data and isinstance(data["data"], list):
                raw_embeddings = [item["embedding"] for item in data["data"]]
            else:
                raise ValueError(f"Unexpected response format from embedding service: {data}")

            if len(raw_embeddings) != len(texts):
                raise ValueError(f"Expected {len(texts)} embeddings, got {len(raw_embeddings)}")

            validated_embeddings: list[list[float]] = []
            for emb in raw_embeddings:
                if len(emb) != self.dimensions:
                    raise ValueError(f"Expected dimension {self.dimensions}, got {len(emb)}")
                if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in emb):
                    raise ValueError("Embedding contains non-finite values (NaN/Inf)")
                norm = math.sqrt(sum(v * v for v in emb))
                if not math.isfinite(norm) or norm < 1e-12:
                    raise ValueError(f"Embedding service returned invalid or zero vector (norm={norm})")
                validated_embeddings.append([v / norm for v in emb])
            return validated_embeddings
        except Exception as exc:
            logger.error("Remote ONNX embedding service call failed (%s): %s", self.url, exc)
            raise EmbeddingInitializationError(
                f"Remote ONNX embedding service unavailable or invalid response: {exc}"
            ) from exc

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        batch_size = 16
        results = []
        for i in range(0, len(texts), batch_size):
            chunk = texts[i : i + batch_size]
            results.extend(self._call_api(chunk))
        return results

    def embed_query(self, text: str) -> list[float]:
        batch = self._call_api([text])
        if not batch:
            raise EmbeddingInitializationError("Empty embedding returned from remote service")
        return batch[0]


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
    elif backend == "remote_onnx":
        return EmbeddingProvenance(
            backend="remote_onnx",
            provider="remote_onnx",
            model="paraphrase-multilingual-MiniLM-L12-v2-int8",
            dimension=settings.embedding_dimensions,
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


def reset_rag_singletons() -> None:
    global _chroma_client, _collection, _ticket_duplicate_collection, _episodic_memory_collection, _embedders
    _chroma_client = None
    _collection = None
    _ticket_duplicate_collection = None
    _episodic_memory_collection = None
    for embedder in list(_embedders.values()):
        if hasattr(embedder, "close") and callable(embedder.close):
            try:
                embedder.close()
            except Exception as exc:
                logger.warning("Error closing embedder on reset: %s", exc)
    _embedders.clear()
    embed_query.cache_clear()


_embedders: dict[str, Any] = {}
_embedder_lock = threading.Lock()


def _get_embedder(backend: str | None = None) -> Any:
    requested_backend = backend or settings.embedding_backend
    if requested_backend not in {"sentence_transformer", "hashing", "remote_onnx"}:
        raise EmbeddingProvenanceError(f"Unsupported embedding backend: {requested_backend}")

    if requested_backend not in _embedders:
        with _embedder_lock:
            if requested_backend not in _embedders:
                if requested_backend == "hashing":
                    _embedders[requested_backend] = _HashingEmbedder()
                elif requested_backend == "remote_onnx":
                    _embedders[requested_backend] = _RemoteOnnxEmbedder()
                else:
                    from src.services.reranker_service import get_torch_device
                    target_device = get_torch_device()
                    logger.info("Loading embedding model (%s) on device (%s)...", settings.embedding_model, target_device)
                    try:
                        _embedders[requested_backend] = HuggingFaceEmbeddings(
                            model_name=settings.embedding_model,
                            model_kwargs={"device": target_device, "local_files_only": not settings.embedding_allow_network_downloads},
                            encode_kwargs={"normalize_embeddings": True},
                        )
                    except Exception as exc:
                        if not settings.embedding_allow_network_downloads:
                            try:
                                logger.info("Local cache missed for %s; attempting download from Hugging Face Hub...", settings.embedding_model)
                                _embedders[requested_backend] = HuggingFaceEmbeddings(
                                    model_name=settings.embedding_model,
                                    model_kwargs={"device": target_device, "local_files_only": False},
                                    encode_kwargs={"normalize_embeddings": True},
                                )
                            except Exception:
                                raise EmbeddingInitializationError(
                                    f"Configured sentence-transformer is unavailable: {settings.embedding_model}"
                                ) from exc
                        else:
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
        provider_name = (
            "sentence_transformers"
            if settings.embedding_backend == "sentence_transformer"
            else ("remote_onnx" if settings.embedding_backend == "remote_onnx" else "local_hashing")
        )
        col = client.get_or_create_collection(
            name=settings.chroma_collection_name,
            metadata={
                "hnsw:space": "cosine",
                "embedding_model": settings.embedding_model if settings.embedding_backend != "remote_onnx" else "paraphrase-multilingual-MiniLM-L12-v2-int8",
                "embedding_backend": settings.embedding_backend,
                "embedding_provider": provider_name,
                "embedding_dimension": settings.embedding_dimensions if settings.embedding_backend == "remote_onnx" else 384,
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
    if backend not in {"sentence_transformer", "hashing", "remote_onnx"}:
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
    _rag_query_cache.clear()
    from src.services.bm25_retriever import invalidate_bm25_index
    invalidate_bm25_index()


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
    _rag_query_cache.clear()
    from src.services.bm25_retriever import invalidate_bm25_index
    invalidate_bm25_index()


def get_indexed_document_ids(doc_ids: list[str]) -> set[str]:
    if not doc_ids:
        return set()
    result = get_collection().get(ids=doc_ids, include=["metadatas"])
    return set(result.get("ids", []))


def delete_document(doc_id: str) -> None:
    """Remove a KB entry from ChromaDB by document id."""
    collection = get_collection()
    collection.delete(ids=[doc_id])
    _rag_query_cache.clear()
    from src.services.bm25_retriever import invalidate_bm25_index
    invalidate_bm25_index()


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
    *,
    use_reranker: bool | None = None,
) -> list[dict]:
    """Hybrid search KB entries with Query Normalization, BM25 Lexical + Dense Embedding, RRF Fusion & optional Reranker."""
    rerank_flag = use_reranker if use_reranker is not None else get_settings().reranker_enabled
    cache_key = f"{user_company_unit or 'all'}:{user_department or 'all'}:{category_filter or 'none'}:{n_results}:{rerank_flag}:{query.strip().lower()}"
    if cache_key in _rag_query_cache:
        return _rag_query_cache[cache_key]

    try:
        collection = get_collection()
    except EmbeddingProvenanceError as exc:
        logger.warning(f"Incompatible KB collection embedding provenance: {exc}")
        return []

    from src.services.bm25_retriever import get_bm25_index
    from src.services.query_normalization_service import (
        extract_exact_technical_tokens,
        normalize_informal_query,
    )
    from src.services.technical_intent_service import infer_technical_facets, topic_compatibility

    # 1. Query Normalization & Technical Token Extraction
    norm_query = normalize_informal_query(query)
    exact_tokens = extract_exact_technical_tokens(query) | extract_exact_technical_tokens(norm_query)
    technical_facets = infer_technical_facets(norm_query)

    # 2. Dense Embedding Retrieval Channel
    expanded_query = _expand_query(norm_query if norm_query != query else query)
    query_embedding = embed_query(expanded_query)

    # Build Pre-Retrieval ACL Filter for Dense Query
    where_conditions = []
    if category_filter:
        where_conditions.append({"category": category_filter})

    if user_company_unit and user_company_unit != "corporate":
        where_conditions.append({
            "$or": [
                {"applicable_to_all": True},
                {"company_unit": "all"},
                {"company_unit": user_company_unit},
            ]
        })

    where_filter = {}
    if len(where_conditions) == 1:
        where_filter = where_conditions[0]
    elif len(where_conditions) > 1:
        where_filter = {"$and": where_conditions}

    try:
        dense_results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(max(n_results * 8, n_results), collection.count() or 1),
            where=where_filter if where_filter else None,
            include=["documents", "metadatas", "distances"],
        )
    except Exception as e:
        logger.warning(f"ChromaDB query error with ACL filter: {e}")
        try:
            dense_results = collection.query(
                query_embeddings=[query_embedding],
                n_results=min(max(n_results * 8, n_results), collection.count() or 1),
                include=["documents", "metadatas", "distances"],
            )
        except Exception as ex:
            logger.error(f"ChromaDB fallback query error: {ex}")
            dense_results = {}

    dense_ranks: dict[str, int] = {}
    dense_docs: dict[str, dict[str, Any]] = {}
    if dense_results and dense_results.get("documents"):
        rank_idx = 1
        for i, doc in enumerate(dense_results["documents"][0]):
            metadata = dense_results["metadatas"][0][i] if dense_results.get("metadatas") else {}
            if not _metadata_allowed(metadata, user_company_unit, user_department):
                continue
            if scan_indirect_injection(doc):
                logger.warning(f"Indirect Prompt Injection detected & blocked in KB doc: {metadata.get('title', 'Unknown')}")
                continue

            doc_id = str(dense_results.get("ids", [[]])[0][i])
            dist = float(dense_results["distances"][0][i]) if dense_results.get("distances") else 1.0
            sem_score = max(0.0, 1.0 - dist)

            dense_ranks[doc_id] = rank_idx
            dense_docs[doc_id] = {
                "doc_id": doc_id,
                "content": doc,
                "metadata": metadata,
                "distance": dist,
                "semantic_score": sem_score,
                "dense_rank": rank_idx,
            }
            rank_idx += 1

    # 3. Independent Lexical BM25 Retrieval Channel
    bm25_results = get_bm25_index().search(
        query=norm_query,
        top_n=60,
        category_filter=category_filter,
        user_company_unit=user_company_unit,
        user_department=user_department,
    )
    bm25_ranks: dict[str, int] = {item["doc_id"]: item["lexical_rank"] for item in bm25_results}
    bm25_docs: dict[str, dict[str, Any]] = {item["doc_id"]: item for item in bm25_results}

    # 4. Reciprocal Rank Fusion (RRF, k=60), then bounded topic relevance and authority.
    k_rrf = 60
    all_candidate_ids = set(dense_ranks.keys()) | set(bm25_ranks.keys())
    if not all_candidate_ids:
        return []

    candidates: list[dict[str, Any]] = []
    for doc_id in all_candidate_ids:
        dense_r = dense_ranks.get(doc_id)
        bm25_r = bm25_ranks.get(doc_id)

        dense_rrf = (1.0 / (k_rrf + dense_r)) if dense_r else 0.0
        bm25_rrf = (1.0 / (k_rrf + bm25_r)) if bm25_r else 0.0

        if doc_id in dense_docs:
            d_info = dict(dense_docs[doc_id])
        else:
            b_item = bm25_docs[doc_id]
            d_info = {
                "doc_id": doc_id,
                "content": b_item["content"],
                "metadata": b_item["metadata"],
                "distance": 1.0,
                "semantic_score": 0.0,
                "dense_rank": None,
            }

        d_info["lexical_rank"] = bm25_r

        # Exact technical token match bonus
        meta = d_info["metadata"]
        searchable_text = f"{meta.get('title', '')} {meta.get('tags', '')} {meta.get('solution', '')} {d_info.get('content', '')}".lower()
        exact_matches = sum(1 for token in exact_tokens if token in searchable_text)
        exact_boost = 0.005 * exact_matches

        # Source authority preference based on deterministic authority hierarchy
        source_type = meta.get("source", "NO_SOURCE_KEY")
        auth_factor = SOURCE_AUTHORITY_FACTORS.get(source_type, 1.0)

        # Authority remains exactly the existing factor, but is applied only
        # after a deterministic technical-topic relevance adjustment.
        rrf_score = dense_rrf * 1.0 + bm25_rrf * 1.2 + exact_boost
        compatibility, compatibility_reason = topic_compatibility(technical_facets, meta)
        topic_adjusted_score = rrf_score * compatibility
        fusion_score = topic_adjusted_score * auth_factor
        d_info["dense_rrf"] = dense_rrf
        d_info["lexical_rrf"] = bm25_rrf
        d_info["exact_contribution"] = exact_boost
        d_info["rrf_score"] = rrf_score
        d_info["topic_compatibility"] = compatibility
        d_info["topic_compatibility_reason"] = compatibility_reason
        d_info["authority_factor"] = auth_factor
        d_info["topic_adjusted_score"] = topic_adjusted_score
        d_info["final_score"] = fusion_score
        d_info["fusion_score"] = fusion_score

        # Traditional lexical score for compatibility
        lexical_overlap = _lexical_score(expanded_query, meta, d_info.get("content", ""))
        d_info["lexical_score"] = lexical_overlap

        candidates.append(d_info)

    # 5. Deterministic Ranking & Downstream Score Calibration
    candidates.sort(key=lambda x: (-x["fusion_score"], x["doc_id"]))
    max_fusion = candidates[0]["fusion_score"] if candidates else 1.0

    for item in candidates:
        # Calibrate relevance_score to [0.0, 1.0] scale expected by downstream consumers
        confidence_base = max(
            item.get("semantic_score", 0.0),
            item.get("lexical_score", 0.0),
            0.75 if item.get("fusion_score", 0.0) == max_fusion else 0.50,
        )
        relative_rrf = (item["fusion_score"] / max_fusion) if max_fusion > 0 else 0.0
        item["relevance_score"] = min(1.0, confidence_base * relative_rrf)

    # Secondary sort by calibrated score and doc_id for complete determinism
    candidates.sort(key=lambda x: (-x["relevance_score"], -x["fusion_score"], x["doc_id"]))

    # 6. Canonical Source Deduplication / Source Diversity
    seen_canonical: set[str] = set()
    primary_candidates: list[dict] = []
    secondary_candidates: list[dict] = []

    for item in candidates:
        canon_id = get_canonical_source_id(item["doc_id"], item.get("metadata", {}))
        if canon_id not in seen_canonical:
            seen_canonical.add(canon_id)
            primary_candidates.append(item)
        else:
            secondary_candidates.append(item)

    deduped_candidates = primary_candidates + secondary_candidates

    # 7. Optional Cross-Encoder Second-Stage Reranking
    if rerank_flag:
        from src.services.reranker_service import rerank_candidates

        final_docs = rerank_candidates(
            query=norm_query,
            candidates=deduped_candidates,
            top_k=n_results,
            enabled=True,
        )
    else:
        final_docs = deduped_candidates[:n_results]

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
    *,
    use_reranker: bool | None = None,
) -> list[dict]:
    """Non-blocking async wrapper cho search_similar."""
    return await asyncio.to_thread(
        search_similar,
        query=query,
        n_results=n_results,
        category_filter=category_filter,
        user_company_unit=user_company_unit,
        user_department=user_department,
        use_reranker=use_reranker,
    )


def get_collection_count() -> int:
    try:
        col = get_collection()
        return col.count()
    except Exception:
        return 0
