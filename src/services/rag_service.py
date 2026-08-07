"""RAG Service — ChromaDB vector store cho knowledge base."""
from __future__ import annotations

import logging
import re
import unicodedata
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_community.embeddings import HuggingFaceEmbeddings

from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Singleton instances
_chroma_client: chromadb.ClientAPI | None = None
_collection: chromadb.Collection | None = None
_embedder: HuggingFaceEmbeddings | None = None

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


import threading
_embedder_lock = threading.Lock()


def _get_embedder() -> HuggingFaceEmbeddings:
    global _embedder
    if _embedder is None:
        with _embedder_lock:
            if _embedder is None:
                logger.info("Loading embedding model (%s)...", settings.embedding_model)
                _embedder = HuggingFaceEmbeddings(
                    model_name=settings.embedding_model,
                    model_kwargs={"device": "cpu"},
                    encode_kwargs={"normalize_embeddings": True},
                )
    return _embedder


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
        _collection = client.get_or_create_collection(
            name=settings.chroma_collection_name,
            metadata={
                "hnsw:space": "cosine",
                "embedding_model": settings.embedding_model,
            },
        )
    return _collection


def embed_texts(texts: list[str]) -> list[list[float]]:
    embedder = _get_embedder()
    return embedder.embed_documents(texts)


from functools import lru_cache
import asyncio


@lru_cache(maxsize=1024)
def embed_query(text: str) -> list[float]:
    embedder = _get_embedder()
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

    collection = get_collection()
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
        return get_collection().count()
    except Exception:
        return 0

