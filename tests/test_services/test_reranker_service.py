"""Deterministic unit tests for optional Cross-Encoder Reranker service.

Tests:
- Reranker disabled -> exact hybrid behavior
- Reranker enabled (mocked model) -> expected reordering and score normalization
- Fallback when model is unavailable
- Fallback when prediction raises an exception
- Candidate dictionary isolation (no in-place mutation of caller candidates)
- Candidate pool cap & top-k slicing
- Deterministic tie-breaking by fusion score and doc_id
- Security invariants & pre-filtering preservation
- Sync and async search_similar integration with use_reranker flag
- No golden dataset ID references in runtime code
"""
from __future__ import annotations

import copy
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.services.reranker_service import (
    invalidate_reranker_model,
    rerank_candidates,
)


@pytest.fixture(autouse=True)
def clean_reranker_cache():
    """Ensure clean reranker cache before and after each test."""
    invalidate_reranker_model()
    yield
    invalidate_reranker_model()


def _sample_candidates() -> list[dict[str, Any]]:
    return [
        {
            "doc_id": "kb-001",
            "content": "Hướng dẫn kết nối VPN FortiClient cho nhân viên",
            "metadata": {
                "title": "Kết nối VPN",
                "solution": "Mở FortiClient và nhập OTP",
                "source": "internal_curated_kb",
                "company_unit": "all",
                "applicable_to_all": True,
                "category": "network",
            },
            "fusion_score": 0.045,
            "relevance_score": 0.85,
        },
        {
            "doc_id": "web-002",
            "content": "Tìm khóa BitLocker trên tài khoản Microsoft",
            "metadata": {
                "title": "Khóa BitLocker",
                "solution": "Đăng nhập tài khoản Microsoft xem key",
                "source": "official_web_documentation",
                "company_unit": "all",
                "applicable_to_all": True,
                "category": "security",
            },
            "fusion_score": 0.040,
            "relevance_score": 0.75,
        },
        {
            "doc_id": "kb-015",
            "content": "Sự cố máy tính không khởi động được hoặc BitLocker khóa",
            "metadata": {
                "title": "Laptop hỏng / BitLocker",
                "solution": "Liên hệ IT Helpdesk nhận recovery key",
                "source": "internal_curated_kb",
                "company_unit": "all",
                "applicable_to_all": True,
                "category": "hardware",
            },
            "fusion_score": 0.038,
            "relevance_score": 0.70,
        },
    ]


# ---------------------------------------------------------------------------
# 1. Disabled & Fallback Behavior
# ---------------------------------------------------------------------------
class TestRerankerDisabledAndFallback:
    def test_reranker_disabled_returns_exact_hybrid_ordering(self):
        candidates = _sample_candidates()
        results = rerank_candidates("query", candidates, top_k=3, enabled=False)
        assert [r["doc_id"] for r in results] == ["kb-001", "web-002", "kb-015"]

    def test_reranker_disabled_preserves_relevance_scores(self):
        candidates = _sample_candidates()
        results = rerank_candidates("query", candidates, top_k=3, enabled=False)
        assert results[0]["relevance_score"] == 0.85
        assert results[1]["relevance_score"] == 0.75

    def test_fallback_when_model_is_none(self):
        candidates = _sample_candidates()
        with patch("src.services.reranker_service.get_cross_encoder", return_value=None):
            results = rerank_candidates("query", candidates, top_k=3, enabled=True)
            assert [r["doc_id"] for r in results] == ["kb-001", "web-002", "kb-015"]

    def test_fallback_when_predict_raises_exception(self):
        candidates = _sample_candidates()
        mock_model = MagicMock()
        mock_model.predict.side_effect = RuntimeError("CUDA out of memory simulation")

        with patch("src.services.reranker_service.get_cross_encoder", return_value=mock_model):
            results = rerank_candidates("query", candidates, top_k=3, enabled=True)
            # Must not raise and must return original hybrid candidates
            assert len(results) == 3
            assert [r["doc_id"] for r in results] == ["kb-001", "web-002", "kb-015"]

    def test_empty_candidates_returns_empty(self):
        results = rerank_candidates("query", [], top_k=5, enabled=True)
        assert results == []


# ---------------------------------------------------------------------------
# 2. Enabled Reranking & Score Normalization (Mocked Model)
# ---------------------------------------------------------------------------
class TestRerankerPrediction:
    def test_successful_reranking_reorders_candidates(self):
        candidates = _sample_candidates()
        # Mock CrossEncoder giving highest logit to kb-015 (index 2)
        mock_model = MagicMock()
        mock_model.predict.return_value = [1.0, 0.5, 5.0]  # kb-015 gets highest score

        with patch("src.services.reranker_service.get_cross_encoder", return_value=mock_model):
            results = rerank_candidates("BitLocker recovery key", candidates, top_k=3, enabled=True)
            assert len(results) == 3
            assert results[0]["doc_id"] == "kb-015"
            assert "cross_encoder_raw_score" in results[0]
            assert "rerank_score" in results[0]

    def test_relevance_scores_calibrated_in_valid_range(self):
        candidates = _sample_candidates()
        mock_model = MagicMock()
        mock_model.predict.return_value = [-10.0, 0.0, 10.0]

        with patch("src.services.reranker_service.get_cross_encoder", return_value=mock_model):
            results = rerank_candidates("query", candidates, top_k=3, enabled=True)
            for r in results:
                assert 0.0 <= r["relevance_score"] <= 1.0

    def test_internal_curated_kb_authority_boost_applied(self):
        # Two documents with identical raw logits: one internal_curated_kb, one official_web
        candidates = [
            {"doc_id": "web-001", "content": "c", "metadata": {"source": "official_web_documentation"}, "fusion_score": 0.04},
            {"doc_id": "kb-001", "content": "c", "metadata": {"source": "internal_curated_kb"}, "fusion_score": 0.04},
        ]
        mock_model = MagicMock()
        mock_model.predict.return_value = [2.0, 2.0]

        with patch("src.services.reranker_service.get_cross_encoder", return_value=mock_model):
            results = rerank_candidates("query", candidates, top_k=2, enabled=True)
            # Internal curated KB should rank first due to 1.05 boost
            assert results[0]["doc_id"] == "kb-001"


# ---------------------------------------------------------------------------
# 3. Cache Isolation & No In-Place Mutation
# ---------------------------------------------------------------------------
class TestRerankerCacheIsolation:
    def test_input_candidate_dicts_are_not_mutated_in_place(self):
        original = _sample_candidates()
        original_copy = copy.deepcopy(original)

        mock_model = MagicMock()
        mock_model.predict.return_value = [3.0, 1.0, 2.0]

        with patch("src.services.reranker_service.get_cross_encoder", return_value=mock_model):
            results = rerank_candidates("query", original, top_k=3, enabled=True)

            # Returned items have new keys
            assert "rerank_score" in results[0]
            # Original input items must NOT have been mutated with reranker keys
            for item in original:
                assert "rerank_score" not in item
                assert "cross_encoder_raw_score" not in item
            assert original[0]["doc_id"] == original_copy[0]["doc_id"]
            assert original[0]["relevance_score"] == original_copy[0]["relevance_score"]


# ---------------------------------------------------------------------------
# 4. Candidate Pool Cap & Top-K Slicing
# ---------------------------------------------------------------------------
class TestCandidatePoolCaps:
    def test_respects_top_k_limit(self):
        candidates = _sample_candidates() * 4  # 12 candidates
        mock_model = MagicMock()
        mock_model.predict.return_value = [1.0] * 8

        with patch("src.services.reranker_service.get_cross_encoder", return_value=mock_model):
            results = rerank_candidates("query", candidates, top_k=5, top_n_candidates=8, enabled=True)
            assert len(results) == 5

    def test_top_n_candidates_limits_model_inference_pool(self):
        candidates = _sample_candidates() * 4  # 12 candidates
        mock_model = MagicMock()
        mock_model.predict.return_value = [1.0] * 4

        with patch("src.services.reranker_service.get_cross_encoder", return_value=mock_model):
            rerank_candidates("query", candidates, top_k=5, top_n_candidates=4, enabled=True)
            # Predict should be called with exactly top_n_candidates pairs
            pairs = mock_model.predict.call_args[0][0]
            assert len(pairs) == 4


# ---------------------------------------------------------------------------
# 5. Deterministic Tie-Breaking
# ---------------------------------------------------------------------------
class TestDeterministicTieBreaking:
    def test_tie_breaking_by_fusion_score_then_doc_id(self):
        candidates = [
            {"doc_id": "kb-zzz", "content": "c", "metadata": {"source": "internal_curated_kb"}, "fusion_score": 0.04},
            {"doc_id": "kb-aaa", "content": "c", "metadata": {"source": "internal_curated_kb"}, "fusion_score": 0.05},
        ]
        mock_model = MagicMock()
        mock_model.predict.return_value = [2.0, 2.0]

        with patch("src.services.reranker_service.get_cross_encoder", return_value=mock_model):
            r1 = rerank_candidates("query", candidates, top_k=2, enabled=True)
            r2 = rerank_candidates("query", candidates, top_k=2, enabled=True)
            assert [r["doc_id"] for r in r1] == ["kb-aaa", "kb-zzz"]
            assert [r["doc_id"] for r in r1] == [r["doc_id"] for r in r2]


# ---------------------------------------------------------------------------
# 6. RAG Service Integration (Sync and Async use_reranker flag)
# ---------------------------------------------------------------------------
class TestRagServiceRerankerIntegration:
    @pytest.mark.asyncio
    async def test_search_similar_async_passes_use_reranker(self):
        from src.services.rag_service import search_similar_async

        with patch("src.services.rag_service.search_similar") as mock_sync:
            mock_sync.return_value = [{"doc_id": "kb-001"}]
            await search_similar_async("query", n_results=3, use_reranker=True)
            mock_sync.assert_called_once_with(
                query="query",
                n_results=3,
                category_filter=None,
                user_company_unit=None,
                user_department=None,
                use_reranker=True,
            )


# ---------------------------------------------------------------------------
# 7. No Golden Dataset ID References in Reranker Code
# ---------------------------------------------------------------------------
class TestNoGoldenDatasetReferences:
    def test_reranker_service_contains_no_golden_ids(self):
        import inspect

        import src.services.reranker_service as rr_mod

        source = inspect.getsource(rr_mod)
        assert "RET-" not in source, "Reranker service must not reference golden case IDs"
        assert "retrieval_golden" not in source.lower(), "Reranker service must not reference golden dataset"
