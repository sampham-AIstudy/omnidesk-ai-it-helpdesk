"""Deterministic regression coverage for C4.3 embedding provenance safety."""

from types import SimpleNamespace

import pytest

from src.services import rag_service


class _Embedder:
    def embed_query(self, text: str) -> list[float]:
        return [0.1] * 384

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(text) for text in texts]


def _collection(metadata: dict) -> SimpleNamespace:
    return SimpleNamespace(name="kb_test", metadata=metadata)


def _sentence_metadata() -> dict:
    return {
        "embedding_backend": "sentence_transformer",
        "embedding_provider": "sentence_transformers",
        "embedding_model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        "embedding_dimension": 384,
        "embedding_normalized": True,
    }


def test_effective_embedder_reports_configured_sentence_transformer(monkeypatch):
    monkeypatch.setattr(rag_service.settings, "embedding_backend", "sentence_transformer")
    monkeypatch.setattr(
        rag_service.settings,
        "embedding_model",
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    )
    monkeypatch.setattr(rag_service, "_get_embedder", lambda backend: _Embedder())

    provenance = rag_service.effective_embedding_provenance()

    assert provenance.backend == "sentence_transformer"
    assert provenance.provider == "sentence_transformers"
    assert provenance.dimension == 384


def test_collection_metadata_matches_effective_embedder(monkeypatch):
    expected = rag_service.EmbeddingProvenance(
        backend="sentence_transformer",
        provider="sentence_transformers",
        model="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        dimension=384,
        normalized=True,
    )
    monkeypatch.setattr(rag_service, "effective_embedding_provenance", lambda: expected)

    assert rag_service.validate_collection_embedding_provenance(_collection(_sentence_metadata())) == expected


def test_embedding_provenance_mismatch_is_detected():
    metadata = _sentence_metadata() | {"embedding_backend": "hashing"}

    with pytest.raises(rag_service.EmbeddingProvenanceError, match="backend"):
        rag_service.validate_collection_embedding_provenance(
            _collection(metadata),
            expected=rag_service.EmbeddingProvenance(
                backend="sentence_transformer",
                provider="sentence_transformers",
                model="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                dimension=384,
                normalized=True,
            ),
        )


def test_incompatible_kb_collection_is_not_queried(monkeypatch):
    monkeypatch.setattr(
        rag_service,
        "get_collection",
        lambda: (_ for _ in ()).throw(rag_service.EmbeddingProvenanceError("mismatch")),
    )
    rag_service._rag_query_cache.clear()

    assert rag_service.search_similar("VPN") == []


def test_collection_specific_embedding_uses_recorded_backend(monkeypatch):
    requested_backends: list[str] = []

    def get_embedder(backend: str):
        requested_backends.append(backend)
        return _Embedder()

    monkeypatch.setattr(rag_service, "_get_embedder", get_embedder)
    legacy_collection = _collection({"embedding_backend": "hashing"})

    vector = rag_service.embed_query_for_collection("duplicate ticket", legacy_collection)

    assert requested_backends == ["hashing"]
    assert len(vector) == 384


def test_collection_specific_embedding_rejects_unknown_backend():
    with pytest.raises(rag_service.EmbeddingProvenanceError, match="no supported embedding backend"):
        rag_service.embed_query_for_collection("unsafe", _collection({"embedding_backend": "unknown"}))


def test_hashing_configuration_cannot_open_sentence_transformer_collection(monkeypatch):
    sentence_collection = _collection(_sentence_metadata())
    monkeypatch.setattr(rag_service.settings, "embedding_backend", "hashing")
    monkeypatch.setattr(rag_service, "_collection", None)
    monkeypatch.setattr(rag_service, "get_chroma_client", lambda: SimpleNamespace(
        get_or_create_collection=lambda **_kwargs: sentence_collection
    ))

    with pytest.raises(rag_service.EmbeddingProvenanceError, match="backend"):
        rag_service.get_collection()


def test_kb_index_update_delete_use_the_one_configured_collection(monkeypatch):
    calls: list[tuple[str, dict]] = []

    class Collection:
        name = "configured-kb"
        metadata = _sentence_metadata()

        def upsert(self, **kwargs):
            calls.append(("upsert", kwargs))

        def delete(self, **kwargs):
            calls.append(("delete", kwargs))

    collection = Collection()
    monkeypatch.setattr(rag_service, "get_collection", lambda: collection)
    monkeypatch.setattr(rag_service, "embed_query", lambda _content: [0.2] * 384)

    rag_service.index_document("temporary-admin-kb", "first", {"title": "First"})
    rag_service.index_document("temporary-admin-kb", "updated", {"title": "Updated"})
    rag_service.delete_document("temporary-admin-kb")

    assert [name for name, _ in calls] == ["upsert", "upsert", "delete"]
    assert calls[0][1]["ids"] == ["temporary-admin-kb"]
    assert calls[1][1]["documents"] == ["updated"]
    assert calls[2][1]["ids"] == ["temporary-admin-kb"]
