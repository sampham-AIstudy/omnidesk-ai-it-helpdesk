"""Optional second-stage Cross-Encoder reranking service for P-236 Help Desk AI.

Operates as a second-stage reranker on top of the Step 2 Hybrid Retriever.
Takes already ACL/tenant/department-filtered and injection-scanned candidates,
computes cross-encoder query-document relevance logits, and produces a
reranked candidate list.

Features:
- Optional & default-disabled (preserves Step 2 Hybrid baseline performance)
- Fail-safe: falls back to hybrid candidate ordering if model load or prediction fails
- Lazy-loaded: never imports or loads model weights until explicitly enabled
- Clean isolation: copies candidates before score assignment to avoid mutating cached results
- Deterministic tie-breaking by fusion score and doc_id
"""
from __future__ import annotations

import copy
import logging
import math
import threading
from typing import Any

from src.config import get_settings

logger = logging.getLogger(__name__)

_reranker_lock = threading.Lock()
_cached_cross_encoder: Any = None
_model_load_attempted: bool = False


def get_torch_device() -> str:
    """Tự động phát hiện GPU (CUDA), nếu không khả dụng sẽ tự động fallback về CPU."""
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
    except Exception:
        pass
    return "cpu"


def get_cross_encoder(model_name: str | None = None) -> Any:
    """Thread-safe lazy initialization of the local CrossEncoder model.

    Returns the loaded model instance or None if loading failed or local files unavailable.
    """
    global _cached_cross_encoder, _model_load_attempted

    with _reranker_lock:
        if _cached_cross_encoder is not None:
            return _cached_cross_encoder
        if _model_load_attempted:
            return _cached_cross_encoder

        _model_load_attempted = True
        target_model = model_name or get_settings().reranker_model_name

        try:
            from sentence_transformers import CrossEncoder

            device = get_torch_device()
            _cached_cross_encoder = CrossEncoder(target_model, device=device, local_files_only=True)
            logger.info(f"Loaded local CrossEncoder model: {target_model} on device: {device}")
        except Exception as exc:
            logger.warning(
                f"Could not load local CrossEncoder '{target_model}' (local_files_only=True): {exc}. "
                "Retrieval will fall back to hybrid candidate ranking."
            )
            _cached_cross_encoder = None

        return _cached_cross_encoder


def invalidate_reranker_model() -> None:
    """Reset cached CrossEncoder instance (useful for testing or configuration changes)."""
    global _cached_cross_encoder, _model_load_attempted
    with _reranker_lock:
        _cached_cross_encoder = None
        _model_load_attempted = False
        logger.info("Invalidated CrossEncoder model cache")


def rerank_candidates(
    query: str,
    candidates: list[dict[str, Any]],
    top_k: int = 5,
    top_n_candidates: int | None = None,
    enabled: bool | None = None,
    model_name: str | None = None,
) -> list[dict[str, Any]]:
    """Rerank pre-filtered hybrid candidates using a CrossEncoder model.

    Args:
        query: User search query text.
        candidates: List of candidate dictionaries already filtered for ACL,
            tenant isolation, department scope, and indirect injection.
        top_k: Final number of documents to return.
        top_n_candidates: Maximum number of top hybrid candidates to evaluate
            with the cross-encoder (default from settings, typically 8-12).
        enabled: Explicit enable flag (defaults to settings.reranker_enabled).
        model_name: Optional override for model identifier.

    Returns:
        Reranked list of candidate dictionaries (up to top_k).
    """
    if not candidates:
        return []

    settings = get_settings()
    is_enabled = enabled if enabled is not None else settings.reranker_enabled

    # If disabled, return clean copy of hybrid candidates
    if not is_enabled:
        return [dict(c) for c in candidates[:top_k]]

    n_pool = top_n_candidates or settings.reranker_top_n
    n_pool = max(2, min(n_pool, len(candidates)))

    model = get_cross_encoder(model_name)
    if model is None:
        # Fail-safe: model unavailable -> preserve exact hybrid ordering
        return [dict(c) for c in candidates[:top_k]]

    # Copy candidate dictionaries to avoid mutating caller / query-cache data
    rerank_pool = [copy.deepcopy(c) for c in candidates[:n_pool]]
    remaining_pool = [dict(c) for c in candidates[n_pool:]]

    # Build (query, document) text pairs
    pairs: list[tuple[str, str]] = []
    for c in rerank_pool:
        meta = c.get("metadata", {}) or {}
        title = meta.get("title", "")
        solution = meta.get("solution", "")
        content = c.get("content", "")
        doc_text = f"{title}. {solution} {content}".strip()[:512]
        pairs.append((query, doc_text))

    try:
        raw_scores = model.predict(pairs)
        for idx, item in enumerate(rerank_pool):
            raw_logit = float(raw_scores[idx])
            # Sigmoid normalization to [0.0, 1.0]
            sig_score = 1.0 / (1.0 + math.exp(-raw_logit)) if -50.0 < raw_logit < 50.0 else (0.0 if raw_logit <= -50.0 else 1.0)
            item["cross_encoder_raw_score"] = raw_logit
            item["cross_encoder_norm_score"] = sig_score

            meta = item.get("metadata", {}) or {}
            source_type = meta.get("source", "")
            auth_factor = 1.05 if source_type == "internal_curated_kb" else 1.0

            item["rerank_score"] = sig_score * auth_factor
            # Update relevance_score for downstream callers (bounded in [0.0, 1.0])
            item["relevance_score"] = min(1.0, max(0.0, sig_score * auth_factor))

        # Deterministic sort: descending by rerank_score, then fusion_score, then doc_id
        rerank_pool.sort(
            key=lambda x: (
                -x.get("rerank_score", 0.0),
                -x.get("fusion_score", 0.0),
                x.get("doc_id", ""),
            )
        )
    except Exception as exc:
        logger.warning(f"CrossEncoder reranking failed, falling back to hybrid ranking: {exc}")
        rerank_pool = [dict(c) for c in candidates[:n_pool]]

    final_results = (rerank_pool + remaining_pool)[:top_k]
    return final_results
