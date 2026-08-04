"""RAG Service — ChromaDB vector store cho knowledge base."""
from __future__ import annotations

import logging
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


def _get_embedder() -> HuggingFaceEmbeddings:
    global _embedder
    if _embedder is None:
        logger.info("Loading embedding model (all-MiniLM-L6-v2)...")
        _embedder = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2",
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
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def embed_texts(texts: list[str]) -> list[list[float]]:
    embedder = _get_embedder()
    return embedder.embed_documents(texts)


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


def search_similar(
    query: str,
    n_results: int = 5,
    category_filter: str | None = None,
    user_company_unit: str | None = None,
    user_department: str | None = None,
) -> list[dict]:
    """Semantic search KB entries. Returns list of {content, metadata, distance}."""
    collection = get_collection()
    query_embedding = embed_query(query)

    where_filter = {}
    if category_filter:
        where_filter = {"category": category_filter}

    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(max(n_results * 3, n_results), collection.count() or 1),
            where=where_filter if where_filter else None,
            include=["documents", "metadatas", "distances"],
        )
    except Exception as e:
        logger.warning(f"ChromaDB query error: {e}")
        return []

    docs = []
    if results and results.get("documents"):
        for i, doc in enumerate(results["documents"][0]):
            metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
            if not _metadata_allowed(metadata, user_company_unit, user_department):
                continue
            docs.append({
                "content": doc,
                "metadata": metadata,
                "distance": results["distances"][0][i] if results.get("distances") else 1.0,
                "relevance_score": max(0.0, 1.0 - (results["distances"][0][i] if results.get("distances") else 1.0)),
            })
    return docs[:n_results]


def get_collection_count() -> int:
    try:
        return get_collection().count()
    except Exception:
        return 0
