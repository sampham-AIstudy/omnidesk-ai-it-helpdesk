"""Deterministic In-Memory BM25 Lexical Retriever for Help Desk Knowledge Base.

Implements pure-Python BM25Okapi indexing and search over the canonical Chroma
knowledge base documents with pre-retrieval ACL, category, and prompt-injection
filtering.
"""
from __future__ import annotations

import logging
import math
import re
import threading
import unicodedata
from collections import Counter
from typing import Any

logger = logging.getLogger(__name__)

_bm25_lock = threading.Lock()
_cached_bm25_index: InvertedBM25Index | None = None


def _normalize_text(text: str) -> str:
    """Strip accents and lowercase for robust BM25 tokenization."""
    norm = unicodedata.normalize("NFKD", text).casefold()
    return "".join(ch for ch in norm if not unicodedata.combining(ch))


def tokenize_lexical(text: str) -> list[str]:
    """Tokenize text into alphanumeric words for lexical matching."""
    norm = _normalize_text(text)
    tokens = re.findall(r"[^\W_]+", norm, flags=re.UNICODE)
    return [t for t in tokens if len(t) > 1]


class InvertedBM25Index:
    """In-memory BM25Okapi inverted index over the knowledge base chunks."""

    def __init__(
        self,
        doc_ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, Any]],
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        self.doc_ids = doc_ids
        self.documents = documents
        self.metadatas = metadatas
        self.N = len(doc_ids)
        self.k1 = k1
        self.b = b

        self.doc_tokens: list[list[str]] = []
        self.doc_lengths: list[int] = []
        self.df: Counter[str] = Counter()

        for content, meta in zip(documents, metadatas):
            title = str(meta.get("title", ""))
            tags = str(meta.get("tags", ""))
            solution = str(meta.get("solution", ""))
            category = str(meta.get("category", ""))
            # Boost title (3x) and tags/category (2x) in token stream
            searchable = f"{title} {title} {title} {tags} {tags} {category} {solution} {content}"
            tokens = tokenize_lexical(searchable)
            self.doc_tokens.append(tokens)
            self.doc_lengths.append(len(tokens))
            for t in set(tokens):
                self.df[t] += 1

        self.avg_doc_len = sum(self.doc_lengths) / self.N if self.N else 1.0

    def search(
        self,
        query: str,
        top_n: int = 60,
        category_filter: str | None = None,
        user_company_unit: str | None = None,
        user_department: str | None = None,
    ) -> list[dict[str, Any]]:
        """Perform BM25 search with pre-filtering against category, ACL, and injection."""
        from src.services.rag_service import _metadata_allowed, scan_indirect_injection

        q_tokens = tokenize_lexical(query)
        if not q_tokens or self.N == 0:
            return []

        scores = [0.0] * self.N

        for t in q_tokens:
            if t not in self.df:
                continue
            n_t = self.df[t]
            # Robertson-Spärck Jones IDF
            idf = math.log((self.N - n_t + 0.5) / (n_t + 0.5) + 1.0)
            for i in range(self.N):
                f = self.doc_tokens[i].count(t)
                if f == 0:
                    continue
                doc_len = self.doc_lengths[i]
                tf = (f * (self.k1 + 1.0)) / (f + self.k1 * (1.0 - self.b + self.b * (doc_len / self.avg_doc_len)))
                scores[i] += idf * tf

        candidates: list[tuple[int, float]] = []
        for i, score in enumerate(scores):
            if score <= 0.0:
                continue
            meta = self.metadatas[i]
            # Category pre-filter
            if category_filter and meta.get("category") != category_filter:
                continue
            # ACL & Tenant / Department pre-filter
            if not _metadata_allowed(meta, user_company_unit, user_department):
                continue
            # Indirect prompt injection exclusion
            if scan_indirect_injection(self.documents[i]):
                continue

            candidates.append((i, score))

        # Sort descending by score, tie-break by doc_id ascending for 100% determinism
        candidates.sort(key=lambda x: (-x[1], self.doc_ids[x[0]]))

        results: list[dict[str, Any]] = []
        for rank, (i, score) in enumerate(candidates[:top_n]):
            results.append(
                {
                    "doc_id": self.doc_ids[i],
                    "content": self.documents[i],
                    "metadata": self.metadatas[i],
                    "bm25_score": score,
                    "lexical_rank": rank + 1,
                }
            )

        return results


def get_bm25_index() -> InvertedBM25Index:
    """Thread-safe singleton accessor for the in-memory BM25 index."""
    global _cached_bm25_index
    if _cached_bm25_index is not None:
        return _cached_bm25_index

    with _bm25_lock:
        if _cached_bm25_index is not None:
            return _cached_bm25_index

        from src.services.rag_service import get_collection

        try:
            col = get_collection()
            data = col.get(include=["metadatas", "documents"])
            doc_ids = list(data.get("ids", []))
            documents = list(data.get("documents", []))
            metadatas = list(data.get("metadatas", []))
            _cached_bm25_index = InvertedBM25Index(doc_ids, documents, metadatas)
            logger.info(f"Initialized in-memory BM25 index over {len(doc_ids)} KB documents")
        except Exception as exc:
            logger.error(f"Failed to initialize BM25 index from Chroma: {exc}")
            _cached_bm25_index = InvertedBM25Index([], [], [])

        return _cached_bm25_index


def invalidate_bm25_index() -> None:
    """Invalidate the cached BM25 index so it is rebuilt on the next search."""
    global _cached_bm25_index
    with _bm25_lock:
        _cached_bm25_index = None
        logger.info("Invalidated BM25 in-memory index cache")
