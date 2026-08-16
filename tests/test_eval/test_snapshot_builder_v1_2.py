from __future__ import annotations

import json
from pathlib import Path

import pytest

from eval.fixture_integrity import EvidenceMode, validate_case_fixture
from eval.snapshot_builder_v1_2 import build_snapshot, resolve_source

ROOT = Path(__file__).resolve().parents[2]


def test_stable_id_resolution_precedes_title_fallback() -> None:
    kb = {"kb-001": {"id": "kb-001", "title": "Không kết nối được VPN công ty", "content": "vpn", "solution": ""}}
    resolved = resolve_source("kb-001", kb, {}, acceptable_titles=["wrong title"])
    assert resolved is not None
    assert resolved[0] == "kb-001"


def test_normalized_title_is_only_fallback_for_stale_id() -> None:
    kb = {"kb-001": {"id": "kb-001", "title": "Không kết nối được VPN công ty", "content": "vpn", "solution": ""}}
    resolved = resolve_source("stale-id", kb, {}, acceptable_titles=["khong ket noi duoc vpn cong ty"])
    assert resolved is not None
    assert resolved[0] == "kb-001"


def test_full_snapshot_has_reproducible_provenance_and_valid_integrity() -> None:
    golden = json.loads((ROOT / "eval" / "golden_testset_enterprise.json").read_text(encoding="utf-8"))
    mapping = json.loads((ROOT / "eval" / "source_mappings_enterprise_v1_2.json").read_text(encoding="utf-8"))
    first = build_snapshot(golden, mapping)
    second = build_snapshot(golden, mapping)
    assert first == second
    assert first["__metadata__"]["fixture_integrity"]["eval_fixture_error_count"] == 0
    source = first["GT-048"][0]
    assert source["metadata"]["source_id"] == "eval-gt048-replacement-conditions"
    assert source["metadata"]["content_hash"]
    case = next(item for item in golden if item["id"] == "GT-048")
    assert validate_case_fixture(case, first["GT-048"], mode=EvidenceMode.PARTIALLY_SUPPORTED, requirements=mapping["entries"]["GT-048"])["integrity"] == "PASS"


def test_snapshot_builder_fails_loudly_for_unresolved_mapping() -> None:
    golden = [{"id": "GT-X", "type": "knowledge_query"}]
    mapping = {"evaluation_fixtures": {}, "entries": {"GT-X": {"expected_evidence_mode": "SUPPORTED", "acceptable_source_ids": ["missing"]}}}
    with pytest.raises(ValueError, match="EVAL_FIXTURE_ERROR"):
        build_snapshot(golden, mapping)
