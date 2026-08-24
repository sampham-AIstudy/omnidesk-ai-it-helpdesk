from __future__ import annotations

from pathlib import Path

from eval.contract_kb_fixture import COLLECTION, build_contract_collection, contract_metadata, load_documents
from eval.enterprise_runtime_v1_0 import default_runtime_snapshot


def test_fix_01_contract_kb_builds_deterministically(tmp_path) -> None:
    first = build_contract_collection(path=tmp_path / "eval_chroma")
    second = build_contract_collection(path=tmp_path / "eval_chroma")
    assert first == second and first["chunk_count"] == len(load_documents())


def test_fix_02_hash_stable_and_fix_03_non_production() -> None:
    metadata = contract_metadata()
    assert metadata["fixture_kb_contract"] == "enterprise-contract-kb-v1"
    assert metadata["source_sha256"] == contract_metadata()["source_sha256"]
    assert COLLECTION != "helpdesk_kb_multilingual_v3_sentence_transformer"


def test_fix_12_missing_fixture_is_not_product_failure() -> None:
    from eval.enterprise_runtime_v1_0 import evaluate_case

    snapshot = default_runtime_snapshot(Path("eval/golden_testset_enterprise.json"), Path("eval/evaluation_manifest.json"))
    row = evaluate_case({"id": "x", "type": "knowledge_query", "query": "VPN", "expected_route": None, "should_retrieve": True, "should_use_memory": False, "should_search_web": False, "should_create_ticket": False, "should_escalate": False}, snapshot)
    assert row.overall_status == "FIXTURE_INCOMPLETE" and "ROUTING_FAILURE" not in row.failure_reasons
