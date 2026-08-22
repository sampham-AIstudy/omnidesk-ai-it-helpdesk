"""Unit tests for _RemoteOnnxEmbedder in src.services.rag_service."""
from unittest.mock import MagicMock, patch
import httpx
import pytest

from src.services.rag_service import _RemoteOnnxEmbedder, EmbeddingInitializationError


def test_remote_onnx_embedder_success():
    embedder = _RemoteOnnxEmbedder()
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


def test_remote_onnx_embedder_empty_input():
    embedder = _RemoteOnnxEmbedder()
    assert embedder.embed_documents([]) == []


def test_remote_onnx_embedder_data_format():
    embedder = _RemoteOnnxEmbedder()
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    vec = [0.5] * 384
    mock_response.json.return_value = {"data": [{"embedding": vec}]}

    with patch.object(httpx.Client, "post", return_value=mock_response):
        res = embedder.embed_query("test query")
        assert len(res) == 384


def test_remote_onnx_embedder_http_error():
    embedder = _RemoteOnnxEmbedder()
    with patch.object(httpx.Client, "post", side_effect=httpx.ConnectError("Connection refused")):
        with pytest.raises(EmbeddingInitializationError, match="Remote ONNX embedding service unavailable"):
            embedder.embed_query("test query")


def test_remote_onnx_embedder_dimension_mismatch():
    embedder = _RemoteOnnxEmbedder()
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    # Dimension 10 instead of 384
    mock_response.json.return_value = {"embeddings": [[0.1] * 10]}

    with patch.object(httpx.Client, "post", return_value=mock_response):
        with pytest.raises(EmbeddingInitializationError, match="Expected dimension"):
            embedder.embed_query("test query")
