"""Read-only autopsy of clean-control knowledge/RAG generation quality.

This intentionally consumes only immutable v1.2 artifacts.  It does not call
the generator, retriever, or Judge and does not alter production behaviour.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from eval.evaluation_contract import load_lock, validate_lock

ROOT = Path(__file__).parent.parent
RESULTS = ROOT / "eval" / "results"
LOCK_PATH = ROOT / "eval" / "snapshots" / "evaluation_lock_v1_2_full.json"
CONTROL_PATH = RESULTS / "baseline_control_context_v1_2.json"
OUTPUT_JSON = RESULTS / "knowledge_generation_autopsy_v1_2.json"

# This selection follows expected response semantics, not merely non-empty
# context.  It excludes direct/social, security, action/tool, memory-only and
# retrieval-hygiene UI cases even where their evaluator route says knowledge.
KNOWLEDGE_IDS = (
    "GT-020", "GT-021", "GT-022", "GT-023", "GT-024", "GT-025", "GT-026",  # incident + KB guidance
    "GT-027", "GT-029",  # account knowledge (GT-028 is credential safety, not KB generation)
    "GT-045", "GT-046", "GT-047", "GT-048", "GT-049",  # knowledge / partial knowledge
    "GT-067", "GT-071", "GT-072", "GT-073", "GT-076", "GT-077",  # multi-part/source knowledge
    "GT-086", "GT-087", "GT-088",  # citation/abstention/refusal knowledge
)

EVIDENCE_MODE = {
    "GT-020": "SUPPORTED", "GT-021": "SUPPORTED", "GT-022": "SUPPORTED", "GT-023": "SUPPORTED",
    "GT-024": "SUPPORTED", "GT-025": "SUPPORTED", "GT-026": "SUPPORTED", "GT-027": "SUPPORTED",
    "GT-029": "PARTIALLY_SUPPORTED", "GT-045": "SUPPORTED", "GT-046": "UNSUPPORTED",
    "GT-047": "PARTIALLY_SUPPORTED", "GT-048": "PARTIALLY_SUPPORTED", "GT-049": "SUPPORTED_CONFLICT",
    "GT-067": "PARTIALLY_SUPPORTED", "GT-071": "SUPPORTED", "GT-072": "SUPPORTED",
    "GT-073": "SUPPORTED", "GT-076": "UNSUPPORTED", "GT-077": "UNSUPPORTED",
    "GT-086": "SUPPORTED", "GT-087": "UNSUPPORTED", "GT-088": "SUPPORTED",
}

# Each entry is a human-reviewed diagnosis against the frozen context, using
# the controlled vocabulary requested for this autopsy.
FAILURE_DIAGNOSIS = {
    "GT-020": {
        "primary_root_cause": "OVERLY_GENERIC_FALLBACK",
        "failure_side": "GENERATOR",
        "incomplete_subtype": None,
        "bad_abstention_subtype": "FULL_REFUSAL_WITH_SUPPORTED_EVIDENCE",
        "unsupported_subtype": None,
        "claims": [
            ["Outlook sync/outbox repair steps", True, "kb-004", False],
            ["More incident-specific detail is needed", False, None, True],
        ],
    },
    "GT-021": {
        "primary_root_cause": "CONTEXT_FACT_MISREAD",
        "failure_side": "GENERATOR",
        "incomplete_subtype": None,
        "bad_abstention_subtype": "CORRECT_ABSTENTION_BUT_JUDGE_EDGE_CASE",
        "unsupported_subtype": None,
        "claims": [
            ["Supplied KB covers meeting audio/video, not sign-in", True, "kb-033", True],
            ["Authorized evidence establishes a sign-in root cause", False, None, False],
        ],
    },
    "GT-029": {
        "primary_root_cause": "SUPPORTED_FACT_OMITTED",
        "failure_side": "GENERATOR",
        "incomplete_subtype": "SUPPORTED_REQUESTED_FACT_OMITTED",
        "bad_abstention_subtype": None,
        "unsupported_subtype": None,
        "claims": [
            ["Account can be unlocked after repeated failed attempts", True, "kb-010", False],
            ["Exact lockout threshold", False, None, False],
        ],
    },
    "GT-046": {
        "primary_root_cause": "OVERLY_GENERIC_FALLBACK",
        "failure_side": "GENERATOR",
        "incomplete_subtype": "UNSUPPORTED_PART_NOT_EXPLICITLY_ACKNOWLEDGED",
        "bad_abstention_subtype": None,
        "unsupported_subtype": None,
        "claims": [["Password minimum-length threshold", False, None, False]],
    },
    "GT-067": {
        "primary_root_cause": "PARTIAL_ANSWER_COLLAPSED_TO_REFUSAL",
        "failure_side": "GENERATOR",
        "incomplete_subtype": "SECONDARY_QUESTION_IGNORED",
        "bad_abstention_subtype": None,
        "unsupported_subtype": None,
        "claims": [
            ["VPN troubleshooting", True, "kb-001", False],
            ["Account unlock after repeated failures", True, "kb-010", False],
            ["Incident SLA", False, None, False],
        ],
    },
    "GT-073": {
        "primary_root_cause": "UNSUPPORTED_DETAIL_ADDED",
        "failure_side": "GENERATOR",
        "incomplete_subtype": None,
        "bad_abstention_subtype": "JUDGE_LABEL_EDGE_CASE",
        "unsupported_subtype": "PROCEDURAL_STEP_INVENTION",
        "claims": [
            ["Hard reset, Safe Mode, Startup Repair", True, "kb-015", True],
            ["Check adapter/outlet and external monitor", False, None, True],
        ],
    },
    "GT-077": {
        "primary_root_cause": "OVERLY_GENERIC_FALLBACK",
        "failure_side": "GENERATOR",
        "incomplete_subtype": "GENERIC_FALLBACK_REPLACED_CAPABILITY_ABSTENTION",
        "bad_abstention_subtype": None,
        "unsupported_subtype": None,
        "claims": [["Current Teams version", False, None, False]],
    },
    "GT-086": {
        "primary_root_cause": "POLICY_GENERALIZATION",
        "failure_side": "GENERATOR",
        "incomplete_subtype": None,
        "bad_abstention_subtype": None,
        "unsupported_subtype": "POLICY_INVENTION",
        "claims": [
            ["KB-12 does not state a 90-day rotation requirement", True, "eval-kb-12-password-policy", True],
            ["System-wide policy does not require 90-day rotation", False, None, True],
        ],
    },
    "GT-087": {
        "primary_root_cause": "OVERLY_GENERIC_FALLBACK",
        "failure_side": "GENERATOR",
        "incomplete_subtype": "UNSUPPORTED_PART_NOT_EXPLICITLY_ACKNOWLEDGED",
        "bad_abstention_subtype": None,
        "unsupported_subtype": None,
        "claims": [["Account lockout attempt threshold", False, None, False]],
    },
}

POSITIVE_CONTROLS = {
    "GT-027": "Grounded password-reset flow without requesting the old password.",
    "GT-047": "Answers the supported VPN port and names the unsupported lockout threshold.",
    "GT-048": "Lists supported laptop-replacement conditions and abstains on fulfillment time.",
    "GT-049": "Surfaces a source conflict without inventing a single SLA value.",
    "GT-088": "Short, evidence-supported VPN port answer with a real source ID.",
}

GLOBAL_INCOMPLETE_SCOPE = {
    "GT-003": (False, "DIRECT_RESPONSE"), "GT-008": (False, "INCIDENT_NO_KB"),
    "GT-009": (False, "INCIDENT_NO_KB"), "GT-012": (False, "CLARIFICATION"),
    "GT-015": (False, "OUT_OF_SCOPE"), "GT-028": (False, "CREDENTIAL_SAFETY"),
    "GT-029": (True, "KNOWLEDGE"), "GT-039": (False, "ACTION_WORKFLOW"),
    "GT-042": (False, "ACTION_WORKFLOW"), "GT-046": (True, "KNOWLEDGE"),
    "GT-050": (False, "MEMORY_CONVERSATION"), "GT-051": (False, "MEMORY_CONVERSATION"),
    "GT-054": (False, "RETRIEVAL_HYGIENE"), "GT-055": (False, "TOOL_LOOKUP"),
    "GT-063": (False, "CONFIDENCE_UI"), "GT-067": (True, "KNOWLEDGE"),
    "GT-070": (False, "INCIDENT_NO_KB"), "GT-077": (True, "KNOWLEDGE"),
    "GT-083": (False, "ACTION_WORKFLOW"), "GT-087": (True, "KNOWLEDGE"),
    "GT-090": (False, "RAPID_FOLLOWUP"),
}

RECOMMENDED_CANARY = {
    "name": "KNOWLEDGE_COMPLETENESS_CANARY",
    "target_failures": ["GT-020", "GT-029", "GT-046", "GT-067", "GT-077", "GT-087"],
    "positive_controls": ["GT-027", "GT-047", "GT-048", "GT-049", "GT-088"],
    "expected_benefit": "Replace generic fallback with concise evidence-aware coverage or a precise abstention, without introducing unsupported detail.",
    "regression_risk": "A completeness instruction may pressure the model to invent policy, numeric, or procedural details; preserve the five positive controls and keep GT-086/GT-073 as separate evidence-boundary work.",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def source_rows(context: list[dict[str, Any]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for doc in context:
        metadata = doc.get("metadata", {}) or {}
        rows.append({
            "source_id": str(metadata.get("source_id") or doc.get("doc_id") or "unknown"),
            "title": str(metadata.get("title") or "Untitled"),
            "summary": " ".join(str(doc.get("content", "")).split())[:500],
        })
    return rows


def run() -> dict[str, Any]:
    lock = load_lock(LOCK_PATH)
    lock_errors = validate_lock(ROOT, lock)
    if lock_errors:
        raise RuntimeError("Evaluation lock mismatch: " + ", ".join(lock_errors))
    control = {row["id"]: row for row in load_json(CONTROL_PATH)["cases"]}
    golden = {row["id"]: row for row in load_json(ROOT / "eval" / "golden_testset_enterprise.json")}
    contexts = load_json(ROOT / lock["context_snapshot"]["path"])

    rows: list[dict[str, Any]] = []
    for case_id in KNOWLEDGE_IDS:
        source = control[case_id]
        diagnosis = FAILURE_DIAGNOSIS.get(case_id)
        rows.append({
            "id": case_id,
            "test_type": golden[case_id].get("type"),
            "question": source["question"],
            "expected_evidence_mode": EVIDENCE_MODE[case_id],
            "expected_behavior": golden[case_id].get("expected_behavior", []),
            "context_sources": source_rows(contexts[case_id]),
            "control_answer": source["answer"],
            "status": source["status"],
            "failure_types": source["judge"]["failure_types"],
            "judge_rationale": source["judge"]["brief_rationale"],
            "diagnosis": diagnosis,
        })

    failed = [row for row in rows if row["status"] == "FAIL"]
    failures = Counter(failure for row in rows for failure in row["failure_types"])
    combinations = Counter(" + ".join(row["failure_types"]) or "NONE" for row in rows)
    root_causes = Counter(row["diagnosis"]["primary_root_cause"] for row in failed)
    incomplete = Counter(row["diagnosis"]["incomplete_subtype"] for row in failed if row["diagnosis"]["incomplete_subtype"])
    abstention = Counter(row["diagnosis"]["bad_abstention_subtype"] for row in failed if row["diagnosis"]["bad_abstention_subtype"])
    unsupported = Counter(row["diagnosis"]["unsupported_subtype"] for row in failed if row["diagnosis"]["unsupported_subtype"])
    side = Counter(row["diagnosis"]["failure_side"] for row in failed)
    global_incomplete = [
        {"id": case_id, "belongs_to_knowledge_slice": belongs, "classification": classification}
        for case_id, (belongs, classification) in GLOBAL_INCOMPLETE_SCOPE.items()
    ]
    return {
        "analysis": "knowledge_generation_failure_slice_v1_2",
        "scope": "read_only_artifact_analysis",
        "metadata": {
            "evaluation_contract": "enterprise-golden-v1.2",
            "evaluation_lock": str(LOCK_PATH.relative_to(ROOT)),
            "golden_hash": lock["golden"]["sha256"],
            "context_snapshot_hash": lock["context_snapshot"]["sha256"],
            "judge_version": "1.3",
            "action_grounding_contract_version": "1.0",
            "production_changes": False,
        },
        "knowledge_case_ids": list(KNOWLEDGE_IDS),
        "summary": {
            "knowledge_cases": len(rows), "semantic_pass": sum(row["status"] == "PASS" for row in rows),
            "semantic_fail": len(failed), "failure_distribution": dict(failures),
            "failure_combination_distribution": dict(combinations), "root_cause_distribution": dict(root_causes),
            "incomplete_answer_subtypes": dict(incomplete), "bad_abstention_subtypes": dict(abstention),
            "unsupported_claim_subtypes": dict(unsupported), "failure_side_distribution": dict(side),
            "global_incomplete_in_knowledge_slice": sum(belongs for belongs, _ in GLOBAL_INCOMPLETE_SCOPE.values()),
            "global_incomplete_outside_knowledge_slice": sum(not belongs for belongs, _ in GLOBAL_INCOMPLETE_SCOPE.values()),
        },
        "global_incomplete_scope": global_incomplete,
        "failed_cases": failed,
        "positive_controls": POSITIVE_CONTROLS,
        "dominant_mechanism": {
            "name": "OVERLY_GENERIC_FALLBACK",
            "count": root_causes["OVERLY_GENERIC_FALLBACK"],
            "interpretation": "The largest coherent generator-side cluster replaces a precise supported answer or explicit evidence-gap statement with a generic insufficient-information fallback. It is not large enough to justify a global prompt rewrite.",
        },
        "recommended_next_canary": RECOMMENDED_CANARY,
    }


def markdown(result: dict[str, Any]) -> str:
    summary = result["summary"]
    lines = [
        "# Knowledge Generation Failure Slice — clean control v1.2",
        "",
        "Read-only analysis; no production generator, retriever, prompt, snapshot, or Judge change.",
        "",
        "## Scope",
        "",
        f"- Knowledge cases: {summary['knowledge_cases']}",
        f"- Semantic pass/fail: {summary['semantic_pass']}/{summary['semantic_fail']}",
        f"- Global INCOMPLETE_ANSWER inside/outside slice: {summary['global_incomplete_in_knowledge_slice']}/{summary['global_incomplete_outside_knowledge_slice']}",
        "",
        "## Failure distribution",
        "",
        "| Failure | Count |",
        "| --- | ---: |",
    ]
    lines += [f"| {key} | {value} |" for key, value in summary["failure_distribution"].items()] or ["| None | 0 |"]
    lines += ["", "## Failed cases", "", "| ID | Root cause | Side | Judge failure |", "| --- | --- | --- | --- |"]
    lines += [
        f"| {row['id']} | {row['diagnosis']['primary_root_cause']} | {row['diagnosis']['failure_side']} | {', '.join(row['failure_types'])} |"
        for row in result["failed_cases"]
    ]
    lines += ["", "## Positive controls", ""]
    lines += [f"- **{case_id}**: {reason}" for case_id, reason in result["positive_controls"].items()]
    canary = result["recommended_next_canary"]
    lines += ["", "## Recommended next canary", "", f"- **{canary['name']}**", f"- Target failures: {', '.join(canary['target_failures'])}", f"- Positive controls: {', '.join(canary['positive_controls'])}", f"- Expected benefit: {canary['expected_benefit']}", f"- Regression risk: {canary['regression_risk']}"]
    return "\n".join(lines)


def main() -> None:
    result = run()
    OUTPUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    OUTPUT_JSON.with_suffix(".md").write_text(markdown(result), encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
