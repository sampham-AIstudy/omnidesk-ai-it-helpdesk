"""Guards the frozen evaluation split and its deterministic input contract."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_evaluation_manifest_covers_the_full_golden_dataset() -> None:
    manifest = json.loads((ROOT / "eval" / "evaluation_manifest.json").read_text(encoding="utf-8"))
    dataset = json.loads((ROOT / manifest["golden_dataset"]).read_text(encoding="utf-8"))
    case_ids = {case["id"] for case in dataset}
    layers = manifest["layers"]

    assert manifest["golden_case_count"] == 300
    assert len(dataset) == 300
    assert len(case_ids) == 300
    routing = set(layers["routing_contract"]["case_ids"])
    assert len(routing) == 21
    assert routing <= case_ids
    assert layers["generation_quality"]["all_cases"] is True
    assert {"knowledge_base_fixture", "ticket_fixture", "retriever", "generation"} <= set(manifest["snapshot"])


def test_routing_cases_have_one_unambiguous_gate_contract() -> None:
    manifest = json.loads((ROOT / "eval" / "evaluation_manifest.json").read_text(encoding="utf-8"))
    dataset = json.loads((ROOT / manifest["golden_dataset"]).read_text(encoding="utf-8"))
    cases = {case["id"]: case for case in dataset}
    required = manifest["layers"]["routing_contract"]["required_fields"]

    for case_id in manifest["layers"]["routing_contract"]["case_ids"]:
        case = cases[case_id]
        assert all(field in case for field in required), case_id
        assert isinstance(case["should_retrieve"], bool), case_id
        assert isinstance(case["should_use_memory"], bool), case_id
        assert isinstance(case["should_search_web"], bool), case_id
