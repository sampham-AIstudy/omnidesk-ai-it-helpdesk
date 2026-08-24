from __future__ import annotations

import json
from pathlib import Path

from scripts.create_hierarchical_metadata_shadow import (
    classify_raw_source,
    metadata_for_proven_single_chunk,
)
from scripts.ingest_p0_shadow_kb import validate_and_prepare

MANIFEST = Path(__file__).resolve().parents[2] / "data" / "p0_shadow_v3_sources.json"


def test_p0_manifest_contains_no_fabricated_hierarchical_relationships() -> None:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    sources, rejected, duplicates = validate_and_prepare(payload["sources"])

    assert not rejected
    assert duplicates == 0
    assert len(sources) == 10
    assert {classify_raw_source(source)["classification"] for source in sources} == {"SINGLE_CHUNK"}


def test_single_chunk_metadata_is_explicitly_ineligible_and_has_no_parent() -> None:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    source = validate_and_prepare(payload["sources"])[0][0]

    metadata = metadata_for_proven_single_chunk(source)

    assert metadata["document_id"] == source["source_id"]
    assert metadata["canonical_source_id"] == source["source_id"]
    assert metadata["chunk_index"] == 0
    assert metadata["total_chunks"] == 1
    assert metadata["expansion_eligible"] is False
    assert "parent_document_id" not in metadata
