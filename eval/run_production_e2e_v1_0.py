"""Run the deterministic production workflow E2E suite and write frozen-style artifacts."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).parent.parent
RESULTS = ROOT / "eval" / "results"
JUNIT_PATH = RESULTS / "production_e2e_v1_0.junit.xml"
JSON_PATH = RESULTS / "production_e2e_v1_0.json"
MD_PATH = RESULTS / "production_e2e_v1_0.md"

WORKFLOW_CASES = {
    "test_e2e_create_incident_persists_ticket_and_audit": ["workflow", "db_persistence", "audit"],
    "test_e2e_ai_followup_persists_messages_without_duplicate_ticket": ["workflow", "db_persistence"],
    "test_e2e_escalation_waits_for_human_without_fake_acceptance": ["workflow", "tool_grounding", "audit"],
    "test_e2e_takeover_requires_role_and_persists_assignment_and_audit": ["authorization", "state_transition", "db_persistence", "audit"],
    "test_e2e_status_close_reopen_and_rating_follow_db_state_machine": ["workflow", "state_transition", "db_persistence", "audit"],
    "test_e2e_service_request_is_not_incident_and_multi_intent_does_not_fake_secondary_action": ["workflow", "db_persistence"],
    "test_e2e_idempotency_and_db_failure_do_not_fabricate_mutations": ["workflow", "db_persistence", "tool_grounding"],
    "test_e2e_tool_failure_renderer_never_confirms_success": ["tool_grounding"],
    "test_e2e_cross_user_cross_tenant_and_fake_role_do_not_bypass_rbac": ["authorization", "db_persistence"],
    "test_e2e_concurrent_takeover_leaves_one_persisted_state": ["state_transition", "db_persistence", "audit"],
    "test_e2e_streaming_completion_and_reconnect_do_not_duplicate_messages": ["streaming", "db_persistence", "tool_grounding"],
}

CASE_CONTRACT = {
    "test_e2e_create_incident_persists_ticket_and_audit": "Ticket OPEN is persisted with a TICKET_CREATED audit actor/timestamp.",
    "test_e2e_ai_followup_persists_messages_without_duplicate_ticket": "One ticket retains exactly one user and one assistant message for the follow-up.",
    "test_e2e_escalation_waits_for_human_without_fake_acceptance": "Ticket is WAITING_FOR_AGENT without an assignee or human-mode claim.",
    "test_e2e_takeover_requires_role_and_persists_assignment_and_audit": "Only an authorized actor assigns the ticket and records the state transition.",
    "test_e2e_status_close_reopen_and_rating_follow_db_state_machine": "API status, closed/reopened DB state and rating agree; invalid transition is rejected.",
    "test_e2e_service_request_is_not_incident_and_multi_intent_does_not_fake_secondary_action": "Service request is persisted separately from Incident and uses catalog routing.",
    "test_e2e_idempotency_and_db_failure_do_not_fabricate_mutations": "Retry creates one ticket; DB timeout creates no ticket and leaks no internal error.",
    "test_e2e_tool_failure_renderer_never_confirms_success": "Failed tool state never renders a completion claim.",
    "test_e2e_cross_user_cross_tenant_and_fake_role_do_not_bypass_rbac": "Cross-user/tenant access and user-provided role claims do not grant access.",
    "test_e2e_concurrent_takeover_leaves_one_persisted_state": "Conflicting takeovers leave one consistent human-owned persisted state.",
    "test_e2e_streaming_completion_and_reconnect_do_not_duplicate_messages": "Completed stream persists one message pair; reconnect is read-only.",
}


def parse_results(path: Path) -> dict[str, object]:
    root = ElementTree.parse(path).getroot()
    nodes = root.findall(".//testcase")
    cases = []
    failure_details = []
    for node in nodes:
        name = node.attrib["name"]
        failure_node = node.find("failure") or node.find("error")
        if node.find("skipped") is not None:
            outcome = "SKIPPED"
        elif node.find("failure") is not None:
            outcome = "FAILED"
        elif node.find("error") is not None:
            outcome = "INFRA_ERROR"
        else:
            outcome = "PASSED"
        case = {
            "case": name,
            "outcome": outcome,
            "duration_seconds": float(node.attrib.get("time", 0)),
            "expected_state": CASE_CONTRACT.get(name, "See test contract."),
        }
        cases.append(case)
        if outcome in {"FAILED", "INFRA_ERROR"}:
            failure_details.append({
                "case": name,
                "expected_state": case["expected_state"],
                "actual_http_api_result": "Captured in pytest/JUnit failure text.",
                "actual_db_result": "Captured in the DB assertion failure text.",
                "suspected_layer": "product" if outcome == "FAILED" else "test_or_product_infrastructure",
                "details": (failure_node.text or "").strip() if failure_node is not None else "",
            })
    outcomes = Counter(item["outcome"] for item in cases)
    categories: dict[str, list[str]] = {}
    for case in cases:
        for category in WORKFLOW_CASES.get(case["case"], []):
            categories.setdefault(category, []).append(case["outcome"])
    return {
        "suite": "production_e2e_v1_0",
        "execution": {
            "total_tests": len(cases), "passed": outcomes["PASSED"], "failed": outcomes["FAILED"],
            "skipped": outcomes["SKIPPED"], "infra_errors": outcomes["INFRA_ERROR"],
        },
        "capabilities": {
            category: "PASS" if all(outcome == "PASSED" for outcome in outcomes) else "FAIL"
            for category, outcomes in categories.items()
        },
        "external_provider_policy": "No external LLM/vector provider is called; provider boundaries are mocked and any test error is product/test infrastructure, not an external-provider result.",
        "cases": cases,
        "failure_details": failure_details,
    }


def write_report(result: dict[str, object]) -> None:
    JSON_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    execution = result["execution"]
    lines = ["# production_e2e_v1_0", "", "## Execution", ""]
    lines.extend(f"- {key}: {value}" for key, value in execution.items())
    lines.extend(["", "## Capability status", "", "| Capability | Status |", "| --- | --- |"])
    lines.extend(f"| {key} | {value} |" for key, value in result["capabilities"].items())
    lines.extend(["", "## External-provider policy", "", result["external_provider_policy"]])
    if result["failure_details"]:
        lines.extend(["", "## Failures", ""])
        for failure in result["failure_details"]:
            lines.append(f"- {failure['case']}: expected {failure['expected_state']} (layer: {failure['suspected_layer']}).")
    else:
        lines.extend(["", "## Failures", "", "None."])
    MD_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pytest-args", nargs="*", default=[])
    args = parser.parse_args()
    RESULTS.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, "-m", "pytest", "tests/e2e", "-q", f"--junitxml={JUNIT_PATH}", *args.pytest_args]
    completed = subprocess.run(command, cwd=ROOT, check=False)
    result = parse_results(JUNIT_PATH)
    write_report(result)
    print(json.dumps({"artifact": str(JSON_PATH.relative_to(ROOT)), **result["execution"]}))
    raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
