from __future__ import annotations

import json
from pathlib import Path

from eval.evaluation_contract import load_lock, validate_lock
from eval.fixture_integrity import EvidenceMode, audit_fixture_integrity, validate_case_fixture

ROOT = Path(__file__).resolve().parents[2]


def _golden() -> dict[str, dict]:
    rows = json.loads((ROOT / "eval" / "golden_testset_enterprise.json").read_text(encoding="utf-8"))
    return {row["id"]: row for row in rows}


def _canary_context() -> dict[str, list[dict]]:
    return json.loads((ROOT / "eval" / "snapshots" / "canary_contract_v1_2_context_snapshot.json").read_text(encoding="utf-8"))


def test_gt048_partial_fixture_has_conditions_but_no_fulfillment_time() -> None:
    context = _canary_context()["GT-048"]
    row = validate_case_fixture(_golden()["GT-048"], context, mode=EvidenceMode.PARTIALLY_SUPPORTED)
    assert row["integrity"] == "PASS"
    assert row["context_source_ids"] == ["eval-gt048-replacement-conditions"]
    content = context[0]["content"].casefold()
    assert "manager approval" in content
    assert "fulfillment-time" in content


def test_canary_fixture_modes_are_internally_consistent() -> None:
    golden = _golden()
    contexts = _canary_context()
    expected = {
        "GT-006": EvidenceMode.NO_EVIDENCE_REQUIRED,
        "GT-023": EvidenceMode.SUPPORTED,
        "GT-047": EvidenceMode.PARTIALLY_SUPPORTED,
        "GT-048": EvidenceMode.PARTIALLY_SUPPORTED,
        "GT-068": EvidenceMode.NO_EVIDENCE_REQUIRED,
    }
    for case_id, mode in expected.items():
        assert validate_case_fixture(golden[case_id], contexts[case_id], mode=mode)["integrity"] == "PASS"


def test_v11_global_audit_marks_fixture_defects_as_setup_errors() -> None:
    rows = list(_golden().values())
    contexts = json.loads((ROOT / "eval" / "results" / "baseline_v1_1_context_snapshot.json").read_text(encoding="utf-8"))
    audit = audit_fixture_integrity(rows, contexts)
    assert audit["eval_fixture_error_count"] > 0
    assert all(row["integrity"] in {"PASS", "EVAL_FIXTURE_ERROR"} for row in audit["cases"])


def test_evaluation_lock_is_intentionally_fail_fast() -> None:
    lock = load_lock(ROOT / "eval" / "snapshots" / "evaluation_lock_v1_2.json")
    assert validate_lock(ROOT, lock) == []
    assert len(lock["routing_contract_ids"]) == 21


def test_full_v12_lock_isolated_from_legacy_v11_snapshot() -> None:
    lock = load_lock(ROOT / "eval" / "snapshots" / "evaluation_lock_v1_2_full.json")
    assert validate_lock(ROOT, lock) == []
    assert lock["context_snapshot"]["path"] != "eval/results/baseline_v1_1_context_snapshot.json"
    assert lock["source_mapping"]["path"] == "eval/source_mappings_enterprise_v1_2.json"
