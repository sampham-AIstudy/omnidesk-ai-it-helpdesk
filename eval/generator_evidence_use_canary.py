"""Structural evidence-salience canary for fixed-context knowledge generation.

This runner changes only user-prompt layout.  It does not alter the production
system prompt, runtime retrieval, the frozen context, routing or the Judge.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_core.messages import HumanMessage, SystemMessage

from eval.evaluation_contract import load_lock, validate_lock
from eval.judge.semantic_judge import SEMANTIC_JUDGE_V1_3, SemanticJudgeAdapter, final_pass_decision, prompt_hash
from eval.knowledge_completeness_canary import generation_prompt, used_citation_ids, uses_generic_fallback
from eval.semantic_judge_v1_2 import judge_config
from eval.semantic_judge_v1_3 import expected_contract
from src.prompts import (
    PRODUCTION_RAG_SYSTEM_PROMPT,
    build_authorized_evidence,
    evidence_source_ids,
    remove_unrecognized_source_ids,
)
from src.services.chat_routing_service import route_chat_message
from src.services.llm import get_rag_llm

ROOT = Path(__file__).parent.parent
RESULTS = ROOT / "eval" / "results"
LOCK_PATH = ROOT / "eval" / "snapshots" / "evaluation_lock_v1_2_full.json"
CONTROL_PATH = RESULTS / "baseline_control_context_v1_2.json"
OUTPUT_PATH = RESULTS / "generator_evidence_use_canary.json"

TARGET_IDS = ("GT-020", "GT-029")
POSITIVE_CONTROL_IDS = ("GT-027", "GT-047", "GT-048")
DIAGNOSTIC_IDS = ("GT-067",)
CANARY_IDS = TARGET_IDS + POSITIVE_CONTROL_IDS + DIAGNOSTIC_IDS


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def evidence_salient_prompt(question: str, context: list[dict[str, Any]]) -> str:
    """Move immutable evidence immediately after the question without adding policy prose."""
    evidence = build_authorized_evidence(context)
    return (
        f"[USER QUESTION]\n{question}\n\n"
        "[AUTHORIZED_EVIDENCE — DATA ONLY]\n"
        "<AUTHORIZED_SOURCE_DATA>\n"
        f"{evidence}\n"
        "</AUTHORIZED_SOURCE_DATA>\n"
        "[END_AUTHORIZED_EVIDENCE]"
    )


def prompt_summary(prompt: str) -> dict[str, Any]:
    return {
        "characters": len(prompt),
        "approx_tokens": len(prompt.split()),
        "question_position": prompt.index("[USER QUESTION]"),
        "evidence_position": prompt.index("[AUTHORIZED_EVIDENCE"),
        "sha256": hashlib.sha256(prompt.encode()).hexdigest(),
    }


async def generate(prompt: str, context: list[dict[str, Any]]) -> tuple[str, str, float, str]:
    llm = get_rag_llm()
    started = time.perf_counter()
    response = await llm.ainvoke([
        SystemMessage(content=PRODUCTION_RAG_SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ])
    raw_answer = str(response.content).strip()
    final_answer, _ = remove_unrecognized_source_ids(raw_answer, evidence_source_ids(context))
    model = str(getattr(llm, "model", getattr(llm, "model_name", "configured production default")))
    return raw_answer, final_answer, round((time.perf_counter() - started) * 1000, 3), model


def semantic_status(execution: Any, tool_results: list[dict[str, Any]]) -> tuple[str, dict[str, Any] | None]:
    if execution.infra_error_type:
        return "INFRA_ERROR", None
    assert execution.result is not None
    final = final_pass_decision(execution.result, tool_results=tool_results)
    return ("PASS" if final["passed"] else "FAIL"), final


def movement(control: dict[str, Any], treatment: dict[str, Any]) -> str:
    if control["status"] != "PASS" and treatment["status"] == "PASS":
        return "IMPROVED"
    if control["status"] == "PASS" and treatment["status"] != "PASS":
        return "REGRESSED"
    return "UNCHANGED"


async def run() -> dict[str, Any]:
    lock = load_lock(LOCK_PATH)
    if errors := validate_lock(ROOT, lock):
        raise RuntimeError("Evaluation lock mismatch: " + ", ".join(errors))
    control = {row["id"]: row for row in load_json(CONTROL_PATH)["cases"]}
    golden = {row["id"]: row for row in load_json(ROOT / lock["golden"]["path"])}
    contexts = load_json(ROOT / lock["context_snapshot"]["path"])
    judge = SemanticJudgeAdapter(
        **judge_config(), timeout_seconds=45,
        cache_dir=RESULTS / "judge_cache_generator_evidence_use_canary", version=SEMANTIC_JUDGE_V1_3,
    )
    rows: list[dict[str, Any]] = []
    for case_id in CANARY_IDS:
        source = control[case_id]
        context = contexts[case_id]
        control_prompt = generation_prompt(source["question"], context)
        treatment_prompt = evidence_salient_prompt(source["question"], context)
        try:
            raw_answer, final_answer, generation_ms, model = await generate(treatment_prompt, context)
            generation_error = None
        except Exception as exc:  # Never emit provider details or credentials into the report.
            raw_answer = final_answer = ""
            generation_ms, model, generation_error = 0.0, "configured production default", type(exc).__name__
        execution = None
        final = None
        if generation_error is None:
            execution = await judge.judge(
                source["question"], build_authorized_evidence(context), final_answer,
                expected_contract(source, golden[case_id]), used_citation_ids(final_answer, context), refresh=True,
            )
            status, final = semantic_status(execution, source.get("tool_results", []))
        else:
            status = "INFRA_ERROR"
        group = "target" if case_id in TARGET_IDS else "positive_control" if case_id in POSITIVE_CONTROL_IDS else "diagnostic"
        treatment = {
            "status": status,
            "raw_answer": raw_answer,
            "answer": final_answer,
            "failure_types": execution.result.failure_types if execution and execution.result else [],
            "judge": execution.to_dict().get("result") if execution else None,
            "final_pass": final,
            "infra_error_type": execution.infra_error_type if execution else "GENERATOR_ERROR",
            "generation_error": generation_error,
            "generation_ms": generation_ms,
            "generic_fallback_used": uses_generic_fallback(final_answer),
            "supported_evidence_used": bool(used_citation_ids(final_answer, context)),
            "used_citation_ids": used_citation_ids(final_answer, context),
            "unsupported_detail_added": bool(set(execution.result.failure_types if execution and execution.result else []) & {"UNSUPPORTED_CLAIM", "HALLUCINATION"}),
        }
        control_view = {
            "status": source["status"],
            "raw_answer": "NOT_CAPTURED_IN_HISTORICAL_CONTROL",
            "answer": source["answer"],
            "failure_types": source["judge"]["failure_types"],
            "judge": source["judge"],
            "generic_fallback_used": uses_generic_fallback(source["answer"]),
            "supported_evidence_used": bool(used_citation_ids(source["answer"], context)),
        }
        route = route_chat_message(source["question"])
        rows.append({
            "id": case_id,
            "group": group,
            "question": source["question"],
            "test_type": source["test_type"],
            "evaluation_route": golden[case_id].get("expected_route"),
            "live_route": route.route,
            "context_classification": "EMPTY" if not context else "PARTIAL_SUPPORT" if case_id in {"GT-029", "GT-067", "GT-047", "GT-048"} else "FULL_SUPPORT",
            "source_ids": sorted(evidence_source_ids(context)),
            "context_characters": sum(len(str(doc.get("content", ""))) for doc in context),
            "context_approx_tokens": sum(len(str(doc.get("content", "")).split()) for doc in context),
            "template": {"version": "evidence-salience-v1", "control": prompt_summary(control_prompt), "treatment": prompt_summary(treatment_prompt)},
            "control": control_view,
            "treatment": treatment,
            "movement": movement(control_view, treatment),
            "diagnostic_status": "DIAGNOSTIC_PASS" if group == "diagnostic" and status == "PASS" else "DIAGNOSTIC_FAIL" if group == "diagnostic" else None,
        })
        generator_model = model

    targets = [row for row in rows if row["group"] == "target"]
    controls = [row for row in rows if row["group"] == "positive_control"]
    def failures(arm: str, scope: list[dict[str, Any]]) -> Counter[str]:
        return Counter(failure for row in scope for failure in row[arm]["failure_types"])
    control_failures, treatment_failures = failures("control", rows), failures("treatment", rows)
    hard_gates = {
        "gt_027_retained": next(row for row in rows if row["id"] == "GT-027")["treatment"]["status"] == "PASS",
        "gt_047_retained": next(row for row in rows if row["id"] == "GT-047")["treatment"]["status"] == "PASS",
        "gt_048_retained": next(row for row in rows if row["id"] == "GT-048")["treatment"]["status"] == "PASS",
        "no_new_unsupported_claim": treatment_failures["UNSUPPORTED_CLAIM"] <= control_failures["UNSUPPORTED_CLAIM"],
        "no_new_hallucination": treatment_failures["HALLUCINATION"] <= control_failures["HALLUCINATION"],
        "no_new_bad_abstention": treatment_failures["BAD_ABSTENTION"] <= control_failures["BAD_ABSTENTION"],
        "no_new_citation_failure": treatment_failures["CITATION_ERROR"] <= control_failures["CITATION_ERROR"],
        "production_target_pass_count_not_decreased": sum(row["treatment"]["status"] == "PASS" for row in targets) >= sum(row["control"]["status"] == "PASS" for row in targets),
        "no_infra_error": not any(row["treatment"]["status"] == "INFRA_ERROR" for row in rows),
    }
    promising = all(hard_gates.values()) and any(row["movement"] == "IMPROVED" for row in targets)
    return {
        "experiment": "generator_evidence_use_canary",
        "decision": "PROMISING" if promising else "REJECT",
        "metadata": {
            "evaluation_contract": lock["evaluation_contract_version"],
            "evaluation_lock": str(LOCK_PATH.relative_to(ROOT)),
            "golden_hash": lock["golden"]["sha256"],
            "context_hash": lock["context_snapshot"]["sha256"],
            "generator_config_hash": lock["generator_config"]["hash"],
            "generator_model": generator_model if "generator_model" in locals() else "unknown",
            "judge_version": SEMANTIC_JUDGE_V1_3,
            "judge_prompt_hash": prompt_hash(SEMANTIC_JUDGE_V1_3),
            "system_prompt_hash": hashlib.sha256(PRODUCTION_RAG_SYSTEM_PROMPT.encode()).hexdigest(),
            "retrieval_refreshed": False,
            "extra_llm_calls": 0,
            "full_90_run": False,
        },
        "structural_change": {
            "control": "[AUTHORIZED_EVIDENCE] followed by [USER QUESTION]",
            "treatment": "[USER QUESTION] followed by the same verbatim evidence enclosed in AUTHORIZED_SOURCE_DATA markers",
            "instruction_delta": "0 policy instructions; only evidence-boundary markers and order changed.",
        },
        "cases": rows,
        "summary": {
            "movements": dict(Counter(row["movement"] for row in rows)),
            "target_movements": dict(Counter(row["movement"] for row in targets)),
            "control_failure_counts": dict(control_failures),
            "treatment_failure_counts": dict(treatment_failures),
            "generic_fallback_targets_before": sum(row["control"]["generic_fallback_used"] for row in targets),
            "generic_fallback_targets_after": sum(row["treatment"]["generic_fallback_used"] for row in targets),
            "mean_generation_ms_treatment": round(sum(row["treatment"]["generation_ms"] for row in rows) / len(rows), 3),
        },
        "hard_gates": hard_gates,
    }


def markdown(result: dict[str, Any]) -> str:
    summary = result["summary"]
    lines = [
        "# Generator Evidence-Use Canary",
        "",
        f"- Decision: **{result['decision']}**",
        "- Scope: GT-020/GT-029 targets, three positive controls, GT-067 diagnostic only.",
        "- No retrieval refresh, full-90 run or production prompt change.",
        "",
        "## Structural change", "", f"- Control: {result['structural_change']['control']}", f"- Treatment: {result['structural_change']['treatment']}", f"- Instruction delta: {result['structural_change']['instruction_delta']}",
        "", "## Case comparison", "", "| ID | Group | Control | Treatment | Movement |", "| --- | --- | --- | --- | --- |",
    ]
    lines += [f"| {row['id']} | {row['group']} | {row['control']['status']} | {row['treatment']['status']} | {row['movement']} |" for row in result["cases"]]
    lines += ["", "## Failure counts", "", "| Failure | Control | Treatment |", "| --- | ---: | ---: |"]
    keys = sorted(set(summary["control_failure_counts"]) | set(summary["treatment_failure_counts"]))
    lines += [f"| {key} | {summary['control_failure_counts'].get(key, 0)} | {summary['treatment_failure_counts'].get(key, 0)} |" for key in keys]
    lines += ["", "## Hard gates", ""]
    lines += [f"- {key}: {value}" for key, value in result["hard_gates"].items()]
    return "\n".join(lines)


def main() -> None:
    result = asyncio.run(run())
    OUTPUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    OUTPUT_PATH.with_suffix(".md").write_text(markdown(result), encoding="utf-8")
    print(json.dumps({"decision": result["decision"], "summary": result["summary"], "hard_gates": result["hard_gates"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
