import json

import pytest

from scripts.rebuild_rag_index import (
    crawled_documents,
    deduplicate_documents,
    historical_documents,
)


def test_loads_crawled_document_with_provenance(tmp_path):
    source = tmp_path / "crawled.json"
    source.write_text(
        json.dumps(
            {
                "documents": [
                    {
                        "doc_id": "web-test-001",
                        "title": "Khắc phục Wi-Fi",
                        "content": "Run the network troubleshooter.",
                        "category": "network",
                        "tags": "wifi,network",
                        "source_url": "https://support.example.test/wifi",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    document = crawled_documents(source)[0]

    assert document["doc_id"] == "web-test-001"
    assert "Khắc phục Wi-Fi" in document["content"]
    assert document["metadata"]["source_url"] == "https://support.example.test/wifi"


def test_loads_historical_document(tmp_path):
    source = tmp_path / "historical.json"
    source.write_text(
        json.dumps(
            [
                {
                    "doc_id": "mem-1",
                    "title": "VPN timeout",
                    "content": "VPN could not connect.",
                    "solution": "Check the network.",
                    "category": "network",
                }
            ]
        ),
        encoding="utf-8",
    )

    document = historical_documents(source)[0]

    assert document["metadata"]["source"] == "historical_resolved_ticket"
    assert "Check the network" in document["content"]


def test_rejects_conflicting_duplicate_ids():
    with pytest.raises(ValueError, match="Trùng doc_id"):
        deduplicate_documents(
            [
                {"doc_id": "same", "content": "first", "metadata": {}},
                {"doc_id": "same", "content": "second", "metadata": {}},
            ]
        )
