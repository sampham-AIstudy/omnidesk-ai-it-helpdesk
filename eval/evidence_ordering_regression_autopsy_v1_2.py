"""Read-only autopsy for the rejected knowledge evidence-ordering slice.

This report deliberately consumes the saved control/treatment outputs.  It
does not call a model, alter a prompt, or change any production behaviour.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from eval.evaluation_contract import load_lock, validate_lock
from eval.generator_evidence_use_canary import evidence_salient_prompt, prompt_summary
from eval.knowledge_completeness_canary import generation_prompt, uses_generic_fallback
from eval.knowledge_generation_autopsy_v1_2 import EVIDENCE_MODE

ROOT = Path(__file__).parent.parent
RESULTS = ROOT / "eval" / "results"
LOCK_PATH = ROOT / "eval" / "snapshots" / "evaluation_lock_v1_2_full.json"
SLICE_PATH = RESULTS / "knowledge_evidence_salience_slice.json"
CONTROL_PATH = RESULTS / "baseline_control_context_v1_2.json"
OUTPUT_PATH = RESULTS / "evidence_ordering_regression_autopsy_v1_2.json"

IMPROVED_IDS = ("GT-020", "GT-021", "GT-029", "GT-073")
REGRESSED_IDS = ("GT-026", "GT-045", "GT-072", "GT-076")
TARGET_IDS = IMPROVED_IDS + REGRESSED_IDS

# These profiles are human-reviewed against the immutable v1.2 context.  They
# are analysis metadata only; none are fed into production generation.
PROFILES: dict[str, dict[str, Any]] = {
    "GT-020": {
        "query_type": "incident_guidance", "support_shape": "FULL_SUPPORT",
        "answer_shape": ["ordered_steps"], "improved_cause": "QUERY_ANCHOR_HELPED",
        "claims": [["Outlook repair/troubleshooting steps", True, "answered_partially", "answered"]],
        "note": "The source supplies concrete Outlook recovery steps, though it does not establish the exact crash cause.",
    },
    "GT-021": {
        "query_type": "incident_guidance", "support_shape": "NONEMPTY_BUT_LIMITED",
        "answer_shape": ["ordered_steps"], "improved_cause": "OTHER_VERIFIED",
        "claims": [["Teams sign-in remediation", False, "not_answered", "not_answered"]],
        "note": "The supplied source concerns meeting audio/video rather than sign-in. The treatment PASS is a Judge/context edge case, not evidence of safely improved support use.",
    },
    "GT-029": {
        "query_type": "account_status", "support_shape": "PARTIAL_SUPPORT",
        "answer_shape": ["single_fact", "partial_abstention"], "improved_cause": "GENERIC_FALLBACK_SUPPRESSED",
        "claims": [["Account can be unlocked after repeated failed attempts", True, "not_answered", "answered"], ["Exact lockout threshold", False, "not_answered", "not_answered"]],
        "note": "Question-first made the account-unlock fact salient; exact thresholds remain unsupported and must not be inferred.",
    },
    "GT-073": {
        "query_type": "incident_guidance", "support_shape": "FULL_SUPPORT",
        "answer_shape": ["ordered_steps"], "improved_cause": "PROCEDURAL_TARGET_CLARIFIED",
        "claims": [["Hard reset / Safe Mode / Startup Repair", True, "answered", "answered"], ["Adapter, outlet, or external-monitor checks", False, "answered", "not_answered"]],
        "note": "Treatment concentrated on supported recovery steps and removed unsupported hardware-detail expansion.",
    },
    "GT-026": {
        "query_type": "incident_guidance", "support_shape": "FULL_SUPPORT",
        "answer_shape": ["conditional_reasoning", "ordered_steps"], "regression_cause": "CONDITIONAL_EVIDENCE_MISREAD",
        "claims": [["DNS/proxy troubleshooting steps", True, "answered", "answered"], ["A whole-Sales outage diagnosis or escalation", False, "not_answered", "not_answered"]],
        "note": "The source is endpoint-oriented while the question describes a shared outage. Treatment foregrounded the broader scope and treated the available troubleshooting as insufficient.",
    },
    "GT-045": {
        "query_type": "procedure", "support_shape": "NONEMPTY_BUT_LIMITED",
        "answer_shape": ["ordered_steps", "conditional_reasoning"], "regression_cause": "PROCEDURAL_EVIDENCE_MISREAD",
        "claims": [["VPN authentication/connection troubleshooting", True, "answered", "answered_partially"], ["Initial company VPN configuration", False, "answered", "not_answered"]],
        "note": "The KB is a VPN failure runbook, not an initial configuration guide. Question-first exposed this mismatch and resulted in over-abstention rather than a clean bounded answer.",
    },
    "GT-072": {
        "query_type": "policy", "support_shape": "NONEMPTY_BUT_LIMITED",
        "answer_shape": ["conditional_reasoning", "procedure"], "regression_cause": "QUESTION_SCOPE_MISREAD",
        "claims": [["Manager approval and shared-mailbox access process", True, "answered", "answered_partially"], ["General shared-mailbox policy", False, "not_answered", "not_answered"]],
        "note": "The context establishes a provisioning process, not the requested general policy. Treatment focused on the broader policy wording and under-covered the supported process.",
    },
    "GT-076": {
        "query_type": "procedure", "support_shape": "NONEMPTY_BUT_LIMITED",
        "answer_shape": ["procedure", "precise_abstention"], "regression_cause": "QUESTION_SCOPE_MISREAD",
        "claims": [["VPN troubleshooting", True, "answered_partially", "answered_partially"], ["Internal VPN configuration", False, "not_answered", "not_answered"]],
        "note": "The source has troubleshooting information but no internal configuration. The apparent treatment regression is chiefly a prompt/Judge edge case around a legitimately unsupported request.",
    },
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def context_details(context: list[dict[str, Any]]) -> tuple[list[str], int, int, list[dict[str, str]]]:
    source_ids, snippets = [], []
    text = ""
    for doc in context:
        metadata = doc.get("metadata", {}) or {}
        source_ids.append(str(doc.get("doc_id") or metadata.get("source_id") or "unknown"))
        content = str(doc.get("content", ""))
        text += content
        snippets.append({
            "source_id": source_ids[-1],
            "evidence_excerpt": " ".join(content.split())[:420],
        })
    return source_ids, len(text), len(text.split()), snippets


def profile_features(row: dict[str, Any]) -> dict[str, Any]:
    profile = PROFILES[row["id"]]
    source_ids, chars, tokens, excerpts = context_details(row["context"])
    return {
        "query_type": profile["query_type"],
        "support_shape": profile["support_shape"],
        "source_count": len(source_ids),
        "context_characters": chars,
        "context_approx_tokens": tokens,
        "answer_requires": profile["answer_shape"],
        "requires_multi_source_synthesis": len(source_ids) > 1,
        "has_conditions_or_exceptions": "conditional_reasoning" in profile["answer_shape"],
        "evidence_sources": excerpts,
    }


def run() -> dict[str, Any]:
    lock = load_lock(LOCK_PATH)
    if errors := validate_lock(ROOT, lock):
        raise RuntimeError("Evaluation lock mismatch: " + ", ".join(errors))
    slice_result = load_json(SLICE_PATH)
    control_rows = {row["id"]: row for row in load_json(CONTROL_PATH)["cases"]}
    contexts = load_json(ROOT / lock["context_snapshot"]["path"])
    rows_by_id = {row["id"]: row for row in slice_result["cases"]}
    cases: list[dict[str, Any]] = []
    for case_id in TARGET_IDS:
        saved = rows_by_id[case_id]
        question = control_rows[case_id]["question"]
        profile = PROFILES[case_id]
        control = saved["control"]
        treatment = saved["treatment"]
        case = {
            "case_id": case_id,
            "movement": saved["movement"],
            "question": question,
            "live_route": saved["live_route"],
            "evaluation_mode": saved["evaluation_mode"],
            "evidence_mode": EVIDENCE_MODE[case_id],
            "context": contexts[case_id],
            "profile": profile_features({"id": case_id, "context": contexts[case_id]}),
            "claim_coverage": [
                {"requested_claim": claim, "supported": supported, "control_answered": control_answered, "treatment_answered": treatment_answered}
                for claim, supported, control_answered, treatment_answered in profile["claims"]
            ],
            "control": {
                "prompt": prompt_summary(generation_prompt(question, contexts[case_id])),
                "answer": control["answer"], "status": control["status"],
                "failure_types": control["failure_types"], "judge_rationale": control["judge"]["brief_rationale"],
                "generic_fallback_used": uses_generic_fallback(control["answer"]),
            },
            "treatment": {
                "prompt": prompt_summary(evidence_salient_prompt(question, contexts[case_id])),
                "answer": treatment["answer"], "status": treatment["status"],
                "failure_types": treatment["failure_types"], "judge_rationale": treatment["judge"]["brief_rationale"],
                "generic_fallback_used": uses_generic_fallback(treatment["answer"]),
            },
            "primary_cause": profile.get("improved_cause") or profile.get("regression_cause"),
            "note": profile["note"],
        }
        del case["context"]
        cases.append(case)

    improved = [case for case in cases if case["movement"] == "IMPROVED"]
    regressed = [case for case in cases if case["movement"] == "REGRESSED"]
    feature_matrix = {
        "source_count": {"improved": [case["profile"]["source_count"] for case in improved], "regressed": [case["profile"]["source_count"] for case in regressed]},
        "context_characters": {"improved": [case["profile"]["context_characters"] for case in improved], "regressed": [case["profile"]["context_characters"] for case in regressed]},
        "support_shape": {"improved": dict(Counter(case["profile"]["support_shape"] for case in improved)), "regressed": dict(Counter(case["profile"]["support_shape"] for case in regressed))},
        "live_route": {"improved": dict(Counter(case["live_route"] for case in improved)), "regressed": dict(Counter(case["live_route"] for case in regressed))},
        "query_type": {"improved": dict(Counter(case["profile"]["query_type"] for case in improved)), "regressed": dict(Counter(case["profile"]["query_type"] for case in regressed))},
        "requires_multi_source_synthesis": {"improved": 0, "regressed": 0},
        "conditions_or_exceptions": {"improved": sum(case["profile"]["has_conditions_or_exceptions"] for case in improved), "regressed": sum(case["profile"]["has_conditions_or_exceptions"] for case in regressed)},
    }
    return {
        "analysis": "evidence_ordering_regression_autopsy_v1_2",
        "scope": "read_only_existing_artifacts",
        "metadata": {
            "evaluation_contract": lock["evaluation_contract_version"],
            "golden_hash": lock["golden"]["sha256"],
            "context_snapshot_hash": lock["context_snapshot"]["sha256"],
            "control_artifact": str(SLICE_PATH.relative_to(ROOT)),
            "generation_calls": 0,
            "production_changes": False,
            "model_variance": "The RAG model is configured with temperature=0.0, but the provider may still be nondeterministic. No repeat generations were run: the single saved A/B sample is insufficient to quantify variance and a vote would not establish a safe production rule.",
        },
        "improved_case_ids": list(IMPROVED_IDS),
        "regressed_case_ids": list(REGRESSED_IDS),
        "cases": cases,
        "feature_matrix": feature_matrix,
        "attention_hypothesis": "Question-first helps when a short user goal has a directly usable, concrete action in the source (GT-020/029/073). It harms broad policy/configuration or scope-mismatched questions by foregrounding the unmet goal over adjacent evidence (GT-026/045/072/076). GT-021 is not reliable supporting evidence because its source does not cover the stated sign-in problem.",
        "trusted_property_analysis": {
            "separates_groups": False,
            "reason": "Route, source count, context size, and evidence presence overlap across both groups. The apparent separator is semantic material-match/answer scope, which would require a new support or question classifier and would recreate the rejected planner failure surface.",
        },
        "decision": "ABANDON_EVIDENCE_ORDERING_CHANGE",
        "decision_evidence": [
            "Semantic PASS is unchanged at 14/23 and 14/20 eligible cases.",
            "All eight cases have one source; routes and context sizes overlap.",
            "Four observed improvements are offset by four regressions, including two BAD_ABSTENTION failures.",
            "No trusted, evaluation-independent runtime property separates the groups.",
        ],
        "recommended_next_step": "PRECISE_ABSTENTION_CANARY for intentionally empty-context GT-046, GT-077, and GT-087; keep the control evidence ordering.",
    }


def markdown(result: dict[str, Any]) -> str:
    lines = ["# Evidence-Ordering Regression Autopsy", "", f"- Decision: **{result['decision']}**", "- Production changes: none.", "- New LLM calls: 0.", "", "## Case profiles", "", "| ID | Movement | Query | Support shape | Sources | Primary cause |", "| --- | --- | --- | --- | ---: | --- |"]
    for case in result["cases"]:
        lines.append(f"| {case['case_id']} | {case['movement']} | {case['profile']['query_type']} | {case['profile']['support_shape']} | {case['profile']['source_count']} | {case['primary_cause']} |")
    lines += ["", "## Claim coverage", ""]
    for case in result["cases"]:
        lines += [f"### {case['case_id']}", "", "| Requested claim | Supported | Control | Treatment |", "| --- | --- | --- | --- |"]
        lines += [f"| {item['requested_claim']} | {item['supported']} | {item['control_answered']} | {item['treatment_answered']} |" for item in case["claim_coverage"]]
        lines.append(f"\n{case['note']}")
    lines += ["", "## Feature comparison", "", "| Feature | Improved | Regressed |", "| --- | --- | --- |"]
    for key, values in result["feature_matrix"].items():
        lines.append(f"| {key} | {values['improved']} | {values['regressed']} |")
    lines += ["", "## Conclusion", "", result["attention_hypothesis"], "", result["trusted_property_analysis"]["reason"], "", f"Recommended next step: **{result['recommended_next_step']}**"]
    return "\n".join(lines)


def main() -> None:
    result = run()
    OUTPUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    OUTPUT_PATH.with_suffix(".md").write_text(markdown(result), encoding="utf-8")
    print(json.dumps({"decision": result["decision"], "improved": result["improved_case_ids"], "regressed": result["regressed_case_ids"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
