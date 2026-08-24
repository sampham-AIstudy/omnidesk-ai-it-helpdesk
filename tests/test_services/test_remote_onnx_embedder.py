"""Unit tests for _RemoteOnnxEmbedder in src.services.rag_service."""
from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.services.rag_service import (
    EmbeddingInitializationError,
    _embedders,
    _RemoteOnnxEmbedder,
    reset_rag_singletons,
)


def test_remote_onnx_embedder_success():
    embedder = _RemoteOnnxEmbedder()
    try:
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        # 384 dimensions normalized
        vec = [0.1] * 384
        mock_response.json.return_value = {"embeddings": [vec, vec]}

        with patch.object(httpx.Client, "post", return_value=mock_response) as mock_post:
            result = embedder.embed_documents(["hello", "world"])
            assert len(result) == 2
            assert len(result[0]) == 384
            assert mock_post.called
    finally:
        embedder.close()


def test_remote_onnx_embedder_empty_input():
    embedder = _RemoteOnnxEmbedder()
    try:
        assert embedder.embed_documents([]) == []
    finally:
        embedder.close()


def test_remote_onnx_embedder_data_format():
    embedder = _RemoteOnnxEmbedder()
    try:
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        vec = [0.5] * 384
        mock_response.json.return_value = {"data": [{"embedding": vec}]}

        with patch.object(httpx.Client, "post", return_value=mock_response):
            res = embedder.embed_query("test query")
            assert len(res) == 384
    finally:
        embedder.close()


def test_remote_onnx_embedder_http_error():
    embedder = _RemoteOnnxEmbedder()
    try:
        with patch.object(httpx.Client, "post", side_effect=httpx.ConnectError("Connection refused")):
            with pytest.raises(EmbeddingInitializationError, match="Remote ONNX embedding service unavailable"):
                embedder.embed_query("test query")
    finally:
        embedder.close()


def test_remote_onnx_embedder_dimension_mismatch():
    embedder = _RemoteOnnxEmbedder()
    try:
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        # Dimension 10 instead of 384
        mock_response.json.return_value = {"embeddings": [[0.1] * 10]}

        with patch.object(httpx.Client, "post", return_value=mock_response):
            with pytest.raises(EmbeddingInitializationError, match="Expected dimension"):
                embedder.embed_query("test query")
    finally:
        embedder.close()


def test_remote_onnx_embedder_zero_vector_rejected():
    embedder = _RemoteOnnxEmbedder()
    try:
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        # All zeros
        mock_response.json.return_value = {"embeddings": [[0.0] * 384]}

        with patch.object(httpx.Client, "post", return_value=mock_response):
            with pytest.raises(EmbeddingInitializationError, match="invalid or zero vector"):
                embedder.embed_query("test query")
    finally:
        embedder.close()


def test_remote_onnx_embedder_close_and_reset():
    embedder = _RemoteOnnxEmbedder()
    # Call _get_client to initialize _client
    client = embedder._get_client()
    assert not client.is_closed
    assert embedder._client is not None

    _embedders["remote_onnx"] = embedder
    reset_rag_singletons()

    assert embedder._client is None
    assert client.is_closed
    assert len(_embedders) == 0
