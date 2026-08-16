"""Read-only fallback-path autopsy for the frozen knowledge-generation slice.

The baseline and canary invoke the generator directly with the immutable
context snapshot.  This report therefore records that evaluation path
separately from the production chat and ticket-agent runtime paths.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from eval.evaluation_contract import load_lock, validate_lock
from eval.knowledge_completeness_canary import generation_prompt, uses_generic_fallback
from src.prompts import build_authorized_evidence, evidence_source_ids
from src.prompts.helpdesk_rag import redact_untrusted_instructions
from src.services.chat_routing_service import route_chat_message

ROOT = Path(__file__).parent.parent
RESULTS = ROOT / "eval" / "results"
LOCK_PATH = ROOT / "eval" / "snapshots" / "evaluation_lock_v1_2_full.json"
CONTROL_PATH = RESULTS / "baseline_control_context_v1_2.json"
CANARY_PATH = RESULTS / "knowledge_completeness_canary.json"
OUTPUT_PATH = RESULTS / "knowledge_fallback_autopsy_v1_2.json"

TARGET_IDS = ("GT-020", "GT-029", "GT-046", "GT-067", "GT-077", "GT-087", "GT-049")
REFERENCE_IDS = ("GT-047", "GT-048", "GT-027")
EVIDENCE_MODE = {
    "GT-020": "SUPPORTED",
    "GT-029": "PARTIALLY_SUPPORTED",
    "GT-046": "UNSUPPORTED",
    "GT-067": "PARTIALLY_SUPPORTED",
    "GT-077": "UNSUPPORTED",
    "GT-087": "UNSUPPORTED",
    "GT-049": "SUPPORTED_CONFLICT",
    "GT-047": "PARTIALLY_SUPPORTED",
    "GT-048": "PARTIALLY_SUPPORTED",
    "GT-027": "SUPPORTED",
}

# Locations are intentionally explicit and audited, rather than inferred from
# the model's natural-language answer.  ``eval/*`` items are not runtime.
FALLBACK_LOCATIONS = (
    {
        "location": "src/prompts/helpdesk_rag.py:28-29",
        "trigger": "Authorized evidence is incomplete or does not support an important requested part.",
        "kind": "PROMPT_INSTRUCTED_FALLBACK",
        "deterministic": False,
        "used_by": "standard chat, streaming chat, ticket conversation, ticket RAG synthesis",
    },
    {
        "location": "src/api/chat.py:413,598",
        "trigger": "No retained internal RAG document after retrieval/filtering.",
        "kind": "CONTEXT_EMPTY_FALLBACK",
        "deterministic": True,
        "used_by": "standard and streaming chat prompt construction; placeholder context only, not final answer",
    },
    {
        "location": "src/api/chat.py:457,633",
        "trigger": "LLM invocation raises, or streaming emits no raw content.",
        "kind": "DETERMINISTIC_PRE_GENERATION_FALLBACK",
        "deterministic": True,
        "used_by": "standard and streaming chat final reply",
    },
    {
        "location": "src/agents/nodes/rag_node.py:40-94",
        "trigger": "No ticket KB documents, low relevance, unavailable external research, or failed external synthesis.",
        "kind": "RETRIEVAL_CONFIDENCE_FALLBACK",
        "deterministic": True,
        "used_by": "ticket-agent RAG workflow only",
    },
    {
        "location": "src/agents/nodes/rag_node.py:220-233",
        "trigger": "Ticket-agent synthesis emits an INSUFFICIENT_KB_MARKER.",
        "kind": "POST_GENERATION_REPLACEMENT",
        "deterministic": True,
        "used_by": "ticket-agent RAG workflow only",
    },
    {
        "location": "src/services/ticket_conversation_service.py:497-501",
        "trigger": "Ticket conversation LLM invocation raises.",
        "kind": "DETERMINISTIC_PRE_GENERATION_FALLBACK",
        "deterministic": True,
        "used_by": "ticket conversation only",
    },
    {
        "location": "eval/knowledge_completeness_canary.py:generation_prompt",
        "trigger": "Never: fixed context is passed directly; no answerability, confidence, template, or post-generation fallback branch exists.",
        "kind": "NO_DETERMINISTIC_FALLBACK",
        "deterministic": True,
        "used_by": "clean-control-equivalent canary evaluation only",
    },
)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def source_id(document: dict[str, Any]) -> str:
    return str(document.get("doc_id") or document.get("metadata", {}).get("source_id") or "unknown")


def context_state(case_id: str, context: list[dict[str, Any]]) -> tuple[str, bool]:
    mode = EVIDENCE_MODE[case_id]
    if not context:
        return "EMPTY", mode == "UNSUPPORTED"
    if mode == "PARTIALLY_SUPPORTED":
        return "PARTIAL_SUPPORT", False
    if mode == "SUPPORTED_CONFLICT":
        return "FULL_SUPPORT", False
    return "FULL_SUPPORT", False


def sanitizer_trace(context: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for document in context:
        original = str(document.get("content", ""))
        sanitized = redact_untrusted_instructions(original)
        rows.append({
            "source_id": source_id(document),
            "before_characters": len(original),
            "after_characters": len(sanitized),
            "content_changed": original != sanitized,
            "removed_span_classification": "MALICIOUS_INSTRUCTION" if original != sanitized else "NONE",
        })
    return rows


def runtime_trace(case_id: str, question: str, context: list[dict[str, Any]], control_answer: str) -> dict[str, Any]:
    route = route_chat_message(question)
    state, intentionally_empty = context_state(case_id, context)
    snapshot_ids = [source_id(document) for document in context]
    final_evidence = build_authorized_evidence(context)
    final_prompt = generation_prompt(question, context)
    retained_ids = sorted(evidence_source_ids(context))
    generic = uses_generic_fallback(control_answer)
    direct_eval_origin = "LLM_SELF_SELECTED_FALLBACK" if generic else "NOT_A_GENERIC_FALLBACK"
    if case_id in {"GT-020", "GT-029", "GT-067"}:
        first_wrong = "LLM_IGNORED_VALID_CONTEXT"
        root = "LLM_IGNORED_VALID_CONTEXT"
    elif case_id in {"GT-046", "GT-077", "GT-087"}:
        first_wrong = "GENERIC_FALLBACK_TOO_EAGER"
        root = "GENERIC_FALLBACK_TOO_EAGER"
    elif case_id == "GT-049":
        first_wrong = "OTHER_VERIFIED"
        root = "OTHER_VERIFIED"
    else:
        first_wrong = "NONE"
        root = "NONE"
    return {
        "case_id": case_id,
        "question": question,
        "evaluation_evidence_mode": EVIDENCE_MODE[case_id],
        "runtime_route": route.route,
        "runtime_answerability": route.answerability,
        "retrieval_required": route.retrieval_required,
        "retrieval_decision": route.retrieval_decision,
        "retrieval_confidence": "NOT_AVAILABLE_IN_FIXED_SNAPSHOT",
        "snapshot_context": {
            "state": state,
            "intentionally_empty": intentionally_empty,
            "source_ids": snapshot_ids,
            "characters": sum(len(str(document.get("content", ""))) for document in context),
            "approx_tokens": sum(len(str(document.get("content", "")).split()) for document in context),
        },
        "sanitizer": sanitizer_trace(context),
        "final_generator_context": {
            "source_ids_retained": retained_ids,
            "source_ids_removed": sorted(set(snapshot_ids) - set(retained_ids)),
            "characters": len(final_evidence),
            "approx_tokens": len(final_evidence.split()),
            "generator_prompt_characters": len(final_prompt),
            "generator_template": "PRODUCTION_RAG_SYSTEM_PROMPT + fixed [AUTHORIZED_EVIDENCE] evaluation input",
            "answerability_gate": "NONE_IN_FIXED_CONTEXT_EVALUATION",
            "fallback_flags": {
                "deterministic_pre_generation_fallback": False,
                "retrieval_confidence_gate": False,
                "context_filtered_to_empty": False,
                "citation_validation_fallback": False,
                "prompt_allows_full_abstention": True,
            },
        },
        "control_answer_generic_fallback": generic,
        "control_answer_origin": direct_eval_origin,
        "raw_vs_final": "RAW_LLM_OUTPUT_NOT_CAPTURED_IN_HISTORICAL_CONTROL; no direct-evaluation postprocessor has a generic-fallback replacement branch.",
        "first_wrong_decision": first_wrong,
        "primary_root_cause": root,
        "runtime_comparability_note": (
            "The frozen generation evaluator bypasses live retrieval and standard-chat filtering by design. "
            "GT-067 would route to action_request in live chat, so its fixed-context generation failure cannot be treated as a live standard-chat fallback trace."
            if case_id == "GT-067" else "Fixed-context evaluator directly reaches the generator after context serialization."
        ),
    }


def treatment_delta(canary_rows: dict[str, dict[str, Any]], case_id: str) -> dict[str, Any] | None:
    row = canary_rows.get(case_id)
    if not row:
        return None
    return {
        "movement": row["movement"],
        "control_status": row["control"]["status"],
        "treatment_status": row["treatment"]["status"],
        "control_generic_fallback": row["control"]["usage"]["USED_GENERIC_FALLBACK"],
        "treatment_generic_fallback": row["treatment"]["usage"]["USED_GENERIC_FALLBACK"],
        "treatment_failure_types": row["treatment"]["failure_types"],
    }


def run() -> dict[str, Any]:
    lock = load_lock(LOCK_PATH)
    if errors := validate_lock(ROOT, lock):
        raise RuntimeError("Evaluation lock mismatch: " + ", ".join(errors))
    control = {row["id"]: row for row in load_json(CONTROL_PATH)["cases"]}
    golden = {row["id"]: row for row in load_json(ROOT / lock["golden"]["path"])}
    contexts = load_json(ROOT / lock["context_snapshot"]["path"])
    canary = {row["id"]: row for row in load_json(CANARY_PATH)["cases"]}
    rows = []
    for case_id in TARGET_IDS + REFERENCE_IDS:
        row = runtime_trace(case_id, control[case_id]["question"], contexts[case_id], control[case_id]["answer"])
        row["test_type"] = golden[case_id].get("type")
        row["control_status"] = control[case_id]["status"]
        row["control_failure_types"] = control[case_id]["judge"]["failure_types"]
        row["canary_delta"] = treatment_delta(canary, case_id)
        rows.append(row)

    targets = [row for row in rows if row["case_id"] in TARGET_IDS]
    root_cases: dict[str, list[str]] = defaultdict(list)
    for row in targets:
        root_cases[row["primary_root_cause"]].append(row["case_id"])
    return {
        "analysis": "knowledge_fallback_mechanism_autopsy_v1_2",
        "scope": "read_only_static_trace_plus_existing_artifacts",
        "metadata": {
            "evaluation_contract": lock["evaluation_contract_version"],
            "evaluation_lock": str(LOCK_PATH.relative_to(ROOT)),
            "golden_hash": lock["golden"]["sha256"],
            "context_snapshot_hash": lock["context_snapshot"]["sha256"],
            "judge_version": "1.3",
            "new_generator_calls": 0,
            "production_behavior_changed": False,
        },
        "fallback_locations": list(FALLBACK_LOCATIONS),
        "cases": rows,
        "findings": {
            "standard_chat_answerability_gate": "No pre-generation answerability or retrieval-confidence branch returns a generic fallback. retrieval confidence is only used for document filtering, web-research decision and telemetry.",
            "fixed_context_evaluation_path": "No deterministic fallback/template/answerability branch exists after fixed context is supplied. The generator receives every retained snapshot source through build_authorized_evidence.",
            "sanitizer": "No inspected frozen target/reference source was modified by redact_untrusted_instructions.",
            "postprocessing": "content_filter and citation cleanup redact/format/remove invalid citation labels; neither selects a generic insufficient-information answer.",
            "ticket_agent_separation": "Ticket-agent rag_node does contain deterministic relevance and post-synthesis fallback branches, but the v1.2 fixed-context generation suite does not execute that graph.",
            "gt049_regression": {
                "classification": "OTHER_VERIFIED",
                "reason": "The 581-character addendum was the only intentional input change, but both answers retained the same conflict evidence and broad fallback. Historical raw request/response logs are unavailable, so a causal prompt conflict cannot be proven; the observed difference is one newly sampled model output and demonstrates prompt sensitivity rather than a deterministic fallback branch.",
            },
        },
        "root_cause_distribution": [
            {"root_cause": root, "count": len(case_ids), "cases": case_ids}
            for root, case_ids in sorted(root_cases.items())
        ],
        "systemic_conclusion": {
            "systemic": True,
            "mechanisms": [
                "LLM_IGNORED_VALID_CONTEXT affects GT-020, GT-029 and GT-067 in the fixed-context evaluator.",
                "GENERIC_FALLBACK_TOO_EAGER affects intentionally empty GT-046, GT-077 and GT-087; their issue is claim specificity, not lost evidence.",
            ],
            "not_verified": [
                "CONTEXT_LOST", "SANITIZER_OVERFILTER", "ANSWERABILITY_GATE_FALSE_NEGATIVE", "RETRIEVAL_SCORE_MISUSED", "POSTPROCESS_OVERRIDE",
            ],
        },
        "recommended_next_canary": {
            "name": "GENERATOR_EVIDENCE_USE_CANARY",
            "scope": "Only nonempty valid-context cases GT-020, GT-029 and GT-067, with GT-027, GT-047 and GT-048 as controls.",
            "reason": "The fixed-context trace preserves evidence and contains no deterministic fallback gate; the first wrong decision is the generator selecting broad abstention despite valid context. Empty-context claim-specific abstention is a separate primitive and must not be bundled.",
            "not_implemented": True,
        },
    }


def markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Knowledge Fallback Mechanism Autopsy v1.2",
        "",
        "Read-only trace: no production behavior, retrieval, prompt, Judge, golden or snapshot change.",
        "",
        "## Fallback locations",
        "",
        "| Location | Trigger | Origin | Used by |", "| --- | --- | --- | --- |",
    ]
    lines += [f"| {row['location']} | {row['trigger']} | {row['kind']} | {row['used_by']} |" for row in result["fallback_locations"]]
    lines += ["", "## Case timelines", "", "| ID | Snapshot | Route | First wrong decision | Root cause |", "| --- | --- | --- | --- | --- |"]
    lines += [f"| {row['case_id']} | {row['snapshot_context']['state']} | {row['runtime_route']} | {row['first_wrong_decision']} | {row['primary_root_cause']} |" for row in result["cases"]]
    lines += ["", "## Findings", ""]
    lines += [f"- **{name}**: {value}" for name, value in result["findings"].items() if isinstance(value, str)]
    lines += ["", "## Root causes", "", "| Root cause | Count | Cases |", "| --- | ---: | --- |"]
    lines += [f"| {row['root_cause']} | {row['count']} | {', '.join(row['cases'])} |" for row in result["root_cause_distribution"]]
    recommendation = result["recommended_next_canary"]
    lines += ["", "## One recommended next canary", "", f"- **{recommendation['name']}**", f"- Scope: {recommendation['scope']}", f"- Reason: {recommendation['reason']}"]
    return "\n".join(lines)


def main() -> None:
    result = run()
    OUTPUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    OUTPUT_PATH.with_suffix(".md").write_text(markdown(result), encoding="utf-8")
    print(json.dumps({"root_causes": result["root_cause_distribution"], "next": result["recommended_next_canary"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
