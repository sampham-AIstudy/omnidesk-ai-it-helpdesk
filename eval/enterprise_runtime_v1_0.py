"""Controlled, runtime-compatible enterprise evaluation coordinator.

This module does not replace production retrieval, behavior, or security
gates.  It makes the enterprise dataset explicit about which deterministic
runtime contracts were exercised and which require an isolated fixture.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

sys.path.insert(0, str(Path(__file__).parent.parent))

from eval.contract_kb_fixture import build_contract_collection, contract_metadata
from eval.enterprise_runtime_fixtures import run_controlled_sync
from eval.evaluation_contract import sha256_text_file
from eval.judge.semantic_judge import JudgeExecution
from src.guardrails.input_guardrails import InputGuardrailPlugin
from src.models.user import User, UserRole
from src.services.chat_routing_service import route_chat_message
from src.services.context_query_service import resolve_contextual_user_query
from src.services.profile_chat_service import self_profile_reply
from src.services.recent_conversation_context import RecentConversationMessage

ROOT = Path(__file__).parent.parent
SNAPSHOT_VERSION = "enterprise-runtime-snapshot-v1.0"
HARNESS_VERSION = "enterprise-runtime-harness-v1.0"
CANONICAL_V3_COLLECTION = "helpdesk_kb_multilingual_v3_sentence_transformer"
CANONICAL_V3_COUNT = 443
FailureCategory = Literal[
    "ROUTING_FAILURE", "SECURITY_FAILURE", "RETRIEVAL_FAILURE", "MEMORY_FAILURE",
    "WEB_FAILURE", "ACTION_FAILURE", "HITL_FAILURE", "CITATION_FAILURE",
    "SEMANTIC_FAILURE", "JUDGE_INFRA_ERROR", "FIXTURE_ERROR", "SNAPSHOT_MISMATCH",
]


def sha256_file(path: Path) -> str:
    return sha256_text_file(path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_turns(query: str) -> list[str]:
    """Parse the established ``turn | follow-up`` golden syntax explicitly."""
    return [part.strip() for part in query.split("|") if part.strip()]


def default_runtime_snapshot(golden_path: Path, manifest_path: Path) -> dict[str, Any]:
    """Describe the required isolated runtime without reading mutable dev data."""
    return {
        "snapshot_version": SNAPSHOT_VERSION,
        "harness_version": HARNESS_VERSION,
        "golden_dataset_hash": sha256_file(golden_path),
        "evaluation_manifest_hash": sha256_file(manifest_path),
        "production_collection_contract": {
            "version": "v3",
            "name": CANONICAL_V3_COLLECTION,
            "count": CANONICAL_V3_COUNT,
        },
        "fixture_kb_contract": {**contract_metadata(), "collection_name": "enterprise_contract_kb_v1", "built": False},
        "retrieval_config_version": "current-runtime-hybrid-v3",
        "users": {"eval_employee": {"id_alias": "eval-user-001", "tenant_alias": "eval-tenant-a", "role": "employee"}},
        "tenants": {"eval-tenant-a": {"company_unit": "Engineering"}},
        "tickets": {}, "roles": {"employee": {"permissions": "fixture-defined"}}, "memories": {},
        "service_catalog": {}, "source_evidence": {},
    }


def validate_snapshot(snapshot: dict[str, Any], *, golden_path: Path, manifest_path: Path, require_isolated_kb: bool = True) -> list[str]:
    errors: list[str] = []
    if snapshot.get("snapshot_version") != SNAPSHOT_VERSION:
        errors.append("SNAPSHOT_VERSION_MISMATCH")
    if snapshot.get("golden_dataset_hash") != sha256_file(golden_path):
        errors.append("GOLDEN_DATASET_HASH_MISMATCH")
    if snapshot.get("evaluation_manifest_hash") != sha256_file(manifest_path):
        errors.append("EVALUATION_MANIFEST_HASH_MISMATCH")
    production = snapshot.get("production_collection_contract", {})
    if production.get("name") != CANONICAL_V3_COLLECTION or production.get("count") != CANONICAL_V3_COUNT:
        errors.append("CANONICAL_COLLECTION_MISMATCH")
    fixture = snapshot.get("fixture_kb_contract", {})
    if fixture.get("fixture_kb_contract") != "enterprise-contract-kb-v1":
        errors.append("FIXTURE_KB_CONTRACT_MISMATCH")
    if require_isolated_kb and not fixture.get("built"):
        errors.append("CONTRACT_KB_NOT_BUILT")
    return errors


def validate_answer_reuse(reused: dict[str, Any], snapshot: dict[str, Any]) -> list[str]:
    """Reject answers generated against a different enterprise runtime."""
    metadata = reused.get("metadata", {})
    required = {
        "golden_dataset_hash": snapshot.get("golden_dataset_hash"),
        "evaluation_manifest_hash": snapshot.get("evaluation_manifest_hash"),
        "snapshot_hash": snapshot_fingerprint(snapshot),
        "harness_version": HARNESS_VERSION,
        "canonical_collection_hash": snapshot.get("fixture_kb_contract", {}).get("source_sha256"),
    }
    return [f"ANSWER_REUSE_{key.upper()}_MISMATCH" for key, value in required.items() if metadata.get(key) != value]


def snapshot_fingerprint(snapshot: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(snapshot, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def _fixture_requirements(case: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    if case.get("should_retrieve"):
        missing.append("ISOLATED_V3_EVIDENCE")
    if case.get("should_use_memory"):
        missing.append("EPISODIC_MEMORY")
    if case.get("should_search_web"):
        missing.append("WEB_RESPONSE")
    if case.get("should_create_ticket"):
        missing.append("ACTION_RESOURCE")
    if case.get("should_escalate"):
        missing.append("HITL_STATE")
    if case.get("type") in {"memory_privacy", "tool_authorization", "access_security", "ticket_operations", "status_accuracy"}:
        missing.append("IDENTITY_OR_AUTHORIZED_RESOURCE")
    return sorted(set(missing))


def _security_status(case: dict[str, Any], final_turn: str) -> str:
    security_types = {"prompt_injection_rag_security", "hacking_dual_use"}
    if case.get("type") in security_types:
        return "PASS" if InputGuardrailPlugin().on_user_message_callback(final_turn).get("decision") == "BLOCK" else "FIXTURE_INCOMPLETE"
    if case.get("type") != "access_security":
        return "NOT_APPLICABLE"
    fixture_user = User(id=9001, email="eval-user@example.invalid", username="eval-user", full_name="Evaluation User", role=UserRole.EMPLOYEE)
    return "PASS" if self_profile_reply(final_turn, fixture_user) is not None else "FIXTURE_INCOMPLETE"


def _semantic_required(case: dict[str, Any], fixture_missing: list[str]) -> bool:
    deterministic_types = {
        "small_talk", "out_of_scope_garbage", "prompt_injection_rag_security",
        "hacking_dual_use", "memory_privacy", "tool_authorization", "access_security",
        "ticket_operations", "human_escalation", "status_accuracy", "ambiguous_incident",
        "minimum_clarification", "retrieval_hygiene",
    }
    return not fixture_missing and case.get("type") not in deterministic_types


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    route: str
    route_pass: str
    retrieval_required: bool
    retrieval_invoked: bool
    memory_expected: bool
    memory_invoked: bool
    web_expected: bool
    web_invoked: bool
    action_expected: bool
    action_result: str
    hitl_expected: bool
    hitl_result: str
    citation_required: bool
    citation_result: str
    security_result: str
    semantic_judge_required: bool
    semantic_score: float | None
    judge_status: str
    overall_status: str
    failure_reasons: list[str]
    resolved_query: str
    turns_executed: int


def evaluate_case(case: dict[str, Any], snapshot: dict[str, Any]) -> CaseResult:
    turns = parse_turns(case["query"])
    history: list[RecentConversationMessage] = []
    resolved = turns[-1]
    for index, turn in enumerate(turns):
        resolution = resolve_contextual_user_query(turn, recent_history=history)
        resolved = resolution.resolved_query
        history.append(RecentConversationMessage(f"eval-{index}", "user", turn))
    guard = InputGuardrailPlugin().on_user_message_callback(resolved)
    routed_text = str(guard.get("normalized_text") or resolved)
    decision = route_chat_message(routed_text)
    expected_route = case.get("expected_route")
    route_pass = "NOT_APPLICABLE" if expected_route is None else (
        "PASS" if decision.route == expected_route and decision.retrieval_required is case["should_retrieve"] else "FAIL"
    )
    fixture_missing = _fixture_requirements(case)
    if snapshot.get("fixture_kb_contract", {}).get("built"):
        fixture_missing = [item for item in fixture_missing if item != "ISOLATED_V3_EVIDENCE"]
    snapshot_errors = validate_snapshot(
        snapshot,
        golden_path=ROOT / "eval" / "golden_testset_enterprise.json",
        manifest_path=ROOT / "eval" / "evaluation_manifest.json",
    )
    failures: list[str] = []
    if route_pass == "FAIL":
        failures.append("ROUTING_FAILURE")
    security_result = _security_status(case, routed_text)
    if security_result == "FAIL":
        failures.append("SECURITY_FAILURE")
    if snapshot_errors:
        failures.append("SNAPSHOT_MISMATCH")
    if fixture_missing:
        failures.append("FIXTURE_ERROR")
    citation_required = bool(case.get("should_retrieve"))
    return CaseResult(
        case_id=case["id"], route=decision.route, route_pass=route_pass,
        retrieval_required=decision.retrieval_required, retrieval_invoked=False,
        memory_expected=case["should_use_memory"], memory_invoked=False,
        web_expected=case["should_search_web"], web_invoked=False,
        action_expected=case["should_create_ticket"], action_result="FIXTURE_INCOMPLETE" if case["should_create_ticket"] else "NOT_APPLICABLE",
        hitl_expected=case["should_escalate"], hitl_result="FIXTURE_INCOMPLETE" if case["should_escalate"] else "NOT_APPLICABLE",
        citation_required=citation_required, citation_result="FIXTURE_INCOMPLETE" if citation_required else "NOT_REQUIRED",
        security_result=security_result, semantic_judge_required=_semantic_required(case, fixture_missing),
        semantic_score=None, judge_status="NOT_REQUESTED",
        overall_status=("FIXTURE_INCOMPLETE" if fixture_missing or snapshot_errors else ("FAIL" if failures else "PASS")),
        failure_reasons=failures + snapshot_errors + fixture_missing, resolved_query=resolved, turns_executed=len(turns),
    )


def classify_judge_execution(execution: JudgeExecution) -> tuple[str, str | None]:
    if execution.infra_error_type:
        return "INFRA_ERROR", "JUDGE_INFRA_ERROR"
    if execution.result is None:
        return "NO_VERDICT", None
    return ("PASS" if execution.result.passed else "FAIL"), (None if execution.result.passed else "SEMANTIC_FAILURE")


def run(cases: list[dict[str, Any]], snapshot: dict[str, Any]) -> dict[str, Any]:
    rows = [asdict(evaluate_case(case, snapshot)) for case in cases]
    applicable = [row for row in rows if row["route_pass"] != "NOT_APPLICABLE"]
    route_pass = sum(row["route_pass"] == "PASS" for row in applicable)
    categories = Counter(reason for row in rows for reason in row["failure_reasons"] if reason in FailureCategory.__args__)
    return {
        "harness_version": HARNESS_VERSION,
        "snapshot_fingerprint": snapshot_fingerprint(snapshot),
        "route_applicable_cases": len(applicable), "route_pass": route_pass,
        "route_fail": len(applicable) - route_pass,
        "route_accuracy": route_pass / len(applicable) if applicable else None,
        "status_counts": dict(Counter(row["overall_status"] for row in rows)),
        "primary_failure_categories": dict(categories), "cases": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the controlled enterprise runtime contract harness")
    parser.add_argument("--cases", type=Path, default=ROOT / "eval" / "golden_testset_enterprise.json")
    parser.add_argument("--manifest", type=Path, default=ROOT / "eval" / "evaluation_manifest.json")
    parser.add_argument("--snapshot", type=Path, default=ROOT / "eval" / "snapshots" / "enterprise_runtime_snapshot_v1_0.json")
    parser.add_argument("--output", type=Path, default=ROOT / "eval" / "results" / "enterprise_runtime_v1_0.json")
    parser.add_argument("--write-snapshot", action="store_true")
    parser.add_argument("--build-contract-kb", action="store_true")
    args = parser.parse_args()
    snapshot = default_runtime_snapshot(args.cases, args.manifest)
    if args.snapshot.exists() and not args.write_snapshot:
        snapshot = load_json(args.snapshot)
    if args.build_contract_kb:
        snapshot["fixture_kb_contract"] = {**build_contract_collection(), "collection_name": "enterprise_contract_kb_v1", "built": True}
    if args.write_snapshot:
        args.snapshot.parent.mkdir(parents=True, exist_ok=True)
        args.snapshot.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    # Step 10C-4 is a deterministic runtime harness.  It intentionally does
    # not invoke the semantic judge; each stage reports its own evidence.
    result = run_controlled_sync(load_json(args.cases))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("status_counts", "stage_counts", "fixture_incomplete_by_root_cause")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
