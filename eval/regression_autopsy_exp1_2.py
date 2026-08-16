"""Artifact-only regression autopsy for Response Planner Exp1.2.

This module deliberately reads the frozen clean A/B artifacts and writes an
audit report.  It has no production imports and does not invoke a model.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parent.parent
RESULTS = ROOT / "eval" / "results"
CONTROL_PATH = RESULTS / "baseline_control_context_v1_2.json"
TREATMENT_PATH = RESULTS / "response_planner_exp1_2_context_v1_2.json"
AB_PATH = RESULTS / "response_planner_exp1_2_ab.json"
GOLDEN_PATH = ROOT / "eval" / "golden_testset_enterprise.json"
SNAPSHOT_PATH = ROOT / "eval" / "snapshots" / "enterprise_context_snapshot_v1_2.json"
OUTPUT_JSON = RESULTS / "response_planner_exp1_2_autopsy.json"
OUTPUT_MD = RESULTS / "response_planner_exp1_2_autopsy.md"


# These classifications are evidence-based reviews of every regression.  They
# are intentionally controlled vocabulary rather than an LLM-generated label.
REGRESSION_REVIEW: dict[str, dict[str, str]] = {
    "GT-004": {
        "first_divergence": "WORKFLOW_MODE",
        "primary_cause": "WRONG_WORKFLOW_MODE",
        "error_class": "PLAN_STATE_ERROR",
        "reason": "Acknowledgement was converted into KNOWLEDGE + ABSTAIN instead of a direct acknowledgement.",
    },
    "GT-010": {
        "first_divergence": "GENERATOR_INTERPRETATION",
        "primary_cause": "GENERATOR_PLAN_NONCOMPLIANCE",
        "error_class": "PLAN_COMPLIANCE_ERROR",
        "reason": "The plan selected INCIDENT + FULL_ANSWER with available support, but generation collapsed to a generic insufficient-information refusal.",
    },
    "GT-011": {
        "first_divergence": "COVERAGE_MODE",
        "primary_cause": "WRONG_COVERAGE_MODE",
        "error_class": "PLAN_STATE_ERROR",
        "reason": "A vague incident needs targeted clarification; the plan selected ABSTAIN.",
    },
    "GT-014": {
        "first_divergence": "COVERAGE_MODE",
        "primary_cause": "WRONG_COVERAGE_MODE",
        "error_class": "PLAN_STATE_ERROR",
        "reason": "An unspecified application problem needs clarification, not a knowledge abstention.",
    },
    "GT-019": {
        "first_divergence": "WORKFLOW_MODE",
        "primary_cause": "WRONG_WORKFLOW_MODE",
        "error_class": "PLAN_STATE_ERROR",
        "reason": "Out-of-scope emotional text was treated as KNOWLEDGE + ABSTAIN, suppressing the existing contextual direct response.",
    },
    "GT-024": {
        "first_divergence": "REQUEST_DECOMPOSITION",
        "primary_cause": "PART_UNDER_DECOMPOSITION",
        "error_class": "PLAN_STATE_ERROR",
        "reason": "One broad SUPPORTED part did not encode the evidence boundary that forbids asserting a wrong password or unrelated remediation steps.",
    },
    "GT-030": {
        "first_divergence": "WORKFLOW_MODE",
        "primary_cause": "WRONG_WORKFLOW_MODE",
        "error_class": "PLAN_STATE_ERROR",
        "reason": "A hardware service request was reduced to KNOWLEDGE + ABSTAIN rather than the existing service-request intake behavior.",
    },
    "GT-031": {
        "first_divergence": "COVERAGE_MODE",
        "primary_cause": "WRONG_COVERAGE_MODE",
        "error_class": "PLAN_STATE_ERROR",
        "reason": "The plan claimed FULL_ANSWER for an underspecified hardware incident; targeted clarification was needed.",
    },
    "GT-034": {
        "first_divergence": "WORKFLOW_MODE",
        "primary_cause": "WRONG_WORKFLOW_MODE",
        "error_class": "PLAN_STATE_ERROR",
        "reason": "A Microsoft 365 license request was reduced to KNOWLEDGE + ABSTAIN rather than service-request intake.",
    },
    "GT-058": {
        "first_divergence": "WORKFLOW_MODE",
        "primary_cause": "WRONG_WORKFLOW_MODE",
        "error_class": "PLAN_STATE_ERROR",
        "reason": "Credential-exfiltration text did not receive SECURITY mode, so the answer lost the safe explanation and recovery path.",
    },
    "GT-060": {
        "first_divergence": "WORKFLOW_MODE",
        "primary_cause": "WRONG_WORKFLOW_MODE",
        "error_class": "PLAN_STATE_ERROR",
        "reason": "A fake-admin credential request did not receive SECURITY mode; the plan supplied no trusted-RBAC framing.",
    },
    "GT-061": {
        "first_divergence": "WORKFLOW_MODE",
        "primary_cause": "WRONG_WORKFLOW_MODE",
        "error_class": "PLAN_STATE_ERROR",
        "reason": "A ticket-creation action request was incorrectly treated as a knowledge abstention rather than an unexecuted action workflow.",
    },
    "GT-062": {
        "first_divergence": "WORKFLOW_MODE",
        "primary_cause": "WRONG_WORKFLOW_MODE",
        "error_class": "PLAN_STATE_ERROR",
        "reason": "A password-reset action request was incorrectly treated as a knowledge abstention rather than action intake.",
    },
    "GT-066": {
        "first_divergence": "SUPPORT_CLASSIFICATION",
        "primary_cause": "NEEDS_USER_INPUT_MISCLASSIFIED",
        "error_class": "PLAN_STATE_ERROR",
        "reason": "The input already supplied application, error code, time, and platform, but the plan marked the whole request NEEDS_USER_INPUT and lost known facts.",
    },
    "GT-069": {
        "first_divergence": "COVERAGE_MODE",
        "primary_cause": "WRONG_COVERAGE_MODE",
        "error_class": "PLAN_STATE_ERROR",
        "reason": "Frustrated but non-security IT text needs a short clarification; the plan selected ABSTAIN.",
    },
    "GT-082": {
        "first_divergence": "WORKFLOW_MODE",
        "primary_cause": "WRONG_WORKFLOW_MODE",
        "error_class": "PLAN_STATE_ERROR",
        "reason": "Cross-user ticket access did not receive SECURITY/AUTHORIZATION handling and lost the safe, explanatory refusal.",
    },
}

HELPFUL_PRIMITIVES = [
    {
        "primitive": "Preserve explicit physical-incident facts for concise triage",
        "improved_cases": ["GT-070"],
        "regression_risk": "Safe only when a trusted incident extractor already establishes the facts; do not infer missing incident facts.",
    },
    {
        "primitive": "State a precise evidence boundary instead of inventing a broader policy",
        "improved_cases": ["GT-021", "GT-086"],
        "regression_risk": "Keep as a generator/evidence instruction, not as global requested-part classification.",
    },
    {
        "primitive": "Short acknowledgement for social turns",
        "improved_cases": ["GT-053"],
        "regression_risk": "The plan itself was wrong (KNOWLEDGE + ABSTAIN); retain only the existing direct-response route, not this planner behavior.",
    },
    {
        "primitive": "Use trusted VPN incident facts to avoid restarting the conversation",
        "improved_cases": ["GT-090"],
        "regression_risk": "Do not retain the treatment's request for a password; only preserve trusted prior facts and targeted diagnostics.",
    },
]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cases_by_id(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {case["id"]: case for case in data["cases"]}


def golden_by_id(data: Any) -> dict[str, dict[str, Any]]:
    rows = data["cases"] if isinstance(data, dict) else data
    return {case["id"]: case for case in rows}


def source_summary(snapshot: dict[str, Any], case_id: str) -> list[dict[str, str]]:
    rows = snapshot.get(case_id, [])
    return [
        {
            "source_id": str(row.get("source_id", "unknown")),
            "source_type": str(row.get("source_type", "unknown")),
            "title": str(row.get("title", "")),
            "content_summary": str(row.get("content", ""))[:240],
        }
        for row in rows
    ]


def status(case: dict[str, Any]) -> str:
    return str(case.get("status") or ("PASS" if case.get("judge", {}).get("passed") else "FAIL"))


def transition(control: dict[str, Any], treatment: dict[str, Any]) -> str:
    control_state = "PASS" if not control.get("judge", {}).get("failure_types") else " + ".join(control["judge"]["failure_types"])
    treatment_state = "PASS" if not treatment.get("judge", {}).get("failure_types") else " + ".join(treatment["judge"]["failure_types"])
    return f"{control_state} -> {treatment_state}"


def main() -> None:
    ab = load_json(AB_PATH)
    control = cases_by_id(load_json(CONTROL_PATH))
    treatment = cases_by_id(load_json(TREATMENT_PATH))
    golden = golden_by_id(load_json(GOLDEN_PATH))
    snapshot = load_json(SNAPSHOT_PATH)
    regressed = [row["id"] for row in ab["case_movement"] if row["delta"] == "REGRESSED"]
    improved = [row["id"] for row in ab["case_movement"] if row["delta"] == "IMPROVED"]

    if set(regressed) != set(REGRESSION_REVIEW):
        raise RuntimeError("Regression artifact and reviewed-case list differ")

    reviewed: list[dict[str, Any]] = []
    for case_id in regressed:
        control_case = control[case_id]
        treatment_case = treatment[case_id]
        golden_case = golden[case_id]
        review = REGRESSION_REVIEW[case_id]
        reviewed.append(
            {
                "case_id": case_id,
                "question": treatment_case.get("question") or golden_case.get("question") or golden_case.get("input"),
                "test_type": golden_case.get("test_type"),
                "expected_behavior": golden_case.get("expected_behavior"),
                "expected_route": golden_case.get("expected_route"),
                "evidence_mode": golden_case.get("expected_evidence_mode"),
                "authorized_context": source_summary(snapshot, case_id),
                "control": {
                    "status": status(control_case),
                    "answer": control_case.get("answer"),
                    "failure_types": control_case.get("judge", {}).get("failure_types", []),
                    "brief_rationale": control_case.get("judge", {}).get("brief_rationale", ""),
                },
                "treatment": {
                    "status": status(treatment_case),
                    "plan": treatment_case.get("plan"),
                    "answer": treatment_case.get("answer"),
                    "failure_types": treatment_case.get("judge", {}).get("failure_types", []),
                    "brief_rationale": treatment_case.get("judge", {}).get("brief_rationale", ""),
                    "generator_calls": treatment_case.get("generator_calls"),
                },
                "transition": transition(control_case, treatment_case),
                **review,
            }
        )

    root_causes = Counter(row["primary_cause"] for row in reviewed)
    error_classes = Counter(row["error_class"] for row in reviewed)
    transitions = Counter(row["transition"] for row in reviewed)
    plan_lengths = [len(json.dumps(row["treatment"]["plan"], ensure_ascii=False, separators=(",", ":"))) for row in reviewed]
    improved_records = []
    for case_id in improved:
        control_case = control[case_id]
        treatment_case = treatment[case_id]
        improved_records.append(
            {
                "case_id": case_id,
                "question": treatment_case.get("question"),
                "transition": transition(control_case, treatment_case),
                "treatment_plan": treatment_case.get("plan"),
                "control_failure_types": control_case.get("judge", {}).get("failure_types", []),
                "treatment_failure_types": treatment_case.get("judge", {}).get("failure_types", []),
            }
        )

    report = {
        "experiment": "response_planner_exp1_2_regression_autopsy",
        "scope": "artifact_only_no_runtime_or_model_calls",
        "input_artifacts": {str(path.relative_to(ROOT)): sha256(path) for path in (CONTROL_PATH, TREATMENT_PATH, AB_PATH, GOLDEN_PATH, SNAPSHOT_PATH)},
        "case_movement": {"regressed": regressed, "improved": improved, "unchanged": 69},
        "regressions": reviewed,
        "root_cause_distribution": dict(sorted(root_causes.items())),
        "error_class_distribution": dict(sorted(error_classes.items())),
        "transition_matrix": dict(sorted(transitions.items())),
        "payload_findings": {
            "all_regressed_cases_used_one_generator_call": all(row["treatment"]["generator_calls"] == 1 for row in reviewed),
            "serialized_plan_chars_excluding_common_prompt_and_evidence": {
                "mean": round(sum(plan_lengths) / len(plan_lengths), 1),
                "min": min(plan_lengths),
                "max": max(plan_lengths),
            },
            "finding": "The payload was not exceptionally large, but it duplicated routing and coverage policy in every call. The harmful instruction pattern was semantic: broad KNOWLEDGE + ABSTAIN state suppressed direct, action, security, and clarification behavior.",
        },
        "helpful_primitives": HELPFUL_PRIMITIVES,
        "minimal_plan_micro_test": {
            "run": False,
            "reason": "Autopsy already establishes 15/16 regressions as plan-state errors. A new generation micro-test cannot determine whether a minimal serialization repairs incorrect state, so it would not be decision-useful before changing the state source.",
        },
        "decision": {
            "outcome": "ABANDON_PLANNER",
            "reason": "The dominant failures arise before generation: 15/16 regressions are plan-state errors across direct, clarification, service/action, security, authorization, and incident semantics. Repair would require a second route/security/action classifier or duplicating trusted orchestration state, increasing coupling rather than making an isolated small fix.",
            "next_experiment": "A narrow generator-policy canary that consumes only already-trusted router/security/tool state for non-KB response modes. Do not infer requested parts or evidence support in a second planner; evaluate it separately from evidence-binding.",
        },
    }
    OUTPUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Response Planner Exp1.2 — Regression Autopsy",
        "",
        "## Decision",
        "",
        "**ABANDON_PLANNER.** This is an artifact-only review; production code, evaluation fixtures, Judge v1.3, and model outputs were not changed.",
        "",
        "## Case movement",
        "",
        f"- Regressed (16): {', '.join(regressed)}",
        f"- Improved (5): {', '.join(improved)}",
        "- Unchanged: 69",
        "",
        "## Root causes",
        "",
        "| Primary root cause | Count | % of 16 | Error class |",
        "| --- | ---: | ---: | --- |",
    ]
    for cause, count in sorted(root_causes.items(), key=lambda item: (-item[1], item[0])):
        classes = ", ".join(sorted({row["error_class"] for row in reviewed if row["primary_cause"] == cause}))
        lines.append(f"| {cause} | {count} | {count / len(reviewed):.1%} | {classes} |")
    lines += [
        "",
        "Plan-state vs plan-compliance: " + ", ".join(f"{key}={value}" for key, value in sorted(error_classes.items())),
        "",
        "## Failure transitions",
        "",
        "| Control state | Treatment state | Count |",
        "| --- | --- | ---: |",
    ]
    for state, count in sorted(transitions.items()):
        before, after = state.split(" -> ", 1)
        lines.append(f"| {before} | {after} | {count} |")
    lines += [
        "",
        "## Per-case autopsy",
        "",
        "| ID | First divergence | Primary cause | Class | Transition |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in reviewed:
        lines.append(f"| {row['case_id']} | {row['first_divergence']} | {row['primary_cause']} | {row['error_class']} | {row['transition']} |")
    lines += [
        "",
        "## Payload finding",
        "",
        f"Every regressed case invoked the generator once. The serialized plan averaged {sum(plan_lengths) / len(plan_lengths):.1f} characters (range {min(plan_lengths)}–{max(plan_lengths)}), excluding shared evidence and instructions. The primary issue is semantic duplication, not token volume.",
        "",
        "## Useful primitives to retain independently",
        "",
        "| Primitive | Improved cases | Regression risk |",
        "| --- | --- | --- |",
    ]
    for primitive in HELPFUL_PRIMITIVES:
        lines.append(f"| {primitive['primitive']} | {', '.join(primitive['improved_cases'])} | {primitive['regression_risk']} |")
    lines += [
        "",
        "## Recommended next experiment (not implemented)",
        "",
        "Run a small generator-policy canary for non-KB modes using only trusted existing routing, authorization, and tool state. It must not create a second requested-parts/support classifier. Keep evidence-binding as a separate later experiment.",
    ]
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT_JSON.relative_to(ROOT)} and {OUTPUT_MD.relative_to(ROOT)}")
    print(f"Decision: {report['decision']['outcome']}; regressions={len(regressed)}; improved={len(improved)}")


if __name__ == "__main__":
    main()
