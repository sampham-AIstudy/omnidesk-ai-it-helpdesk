"""Validate evidence-salience layout across the frozen 23-case knowledge slice.

Only non-empty fixed contexts receive the structural treatment.  Intentionally
empty contexts retain their saved control answers so this run does not mix
evidence-use validation with precise-abstention work.
"""
from __future__ import annotations

import asyncio
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from eval.evaluation_contract import load_lock, validate_lock
from eval.fixture_integrity import EvidenceMode, audit_fixture_integrity
from eval.generator_evidence_use_canary import (
    evidence_salient_prompt,
    generate,
    movement,
    prompt_summary,
    semantic_status,
)
from eval.judge.semantic_judge import SEMANTIC_JUDGE_V1_3, SemanticJudgeAdapter, prompt_hash
from eval.knowledge_completeness_canary import generation_prompt, used_citation_ids, uses_generic_fallback
from eval.knowledge_generation_autopsy_v1_2 import EVIDENCE_MODE, KNOWLEDGE_IDS
from eval.semantic_judge_v1_2 import judge_config
from eval.semantic_judge_v1_3 import expected_contract, response_mode
from src.prompts import build_authorized_evidence
from src.services.chat_routing_service import route_chat_message

ROOT = Path(__file__).parent.parent
RESULTS = ROOT / "eval" / "results"
LOCK_PATH = ROOT / "eval" / "snapshots" / "evaluation_lock_v1_2_full.json"
CONTROL_PATH = RESULTS / "baseline_control_context_v1_2.json"
OUTPUT_PATH = RESULTS / "knowledge_evidence_salience_slice.json"
UNTOUCHED_EMPTY_IDS = ("GT-046", "GT-077", "GT-087")
DIAGNOSTIC_ONLY_IDS = ("GT-067",)
CRITICAL_CONTROL_IDS = ("GT-027", "GT-047", "GT-048")
SCORES = ("faithfulness", "completeness", "relevance", "correct_abstention", "citation_correctness")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def failure_counts(rows: list[dict[str, Any]], arm: str) -> Counter[str]:
    return Counter(failure for row in rows for failure in row[arm]["failure_types"])


def metrics(rows: list[dict[str, Any]], arm: str) -> dict[str, Any]:
    judged = [row[arm] for row in rows if row[arm]["status"] != "INFRA_ERROR"]
    return {
        "case_count": len(rows),
        "semantic_pass": sum(item["status"] == "PASS" for item in judged),
        "semantic_fail": sum(item["status"] == "FAIL" for item in judged),
        "infra_error": len(rows) - len(judged),
        "averages": {
            score: round(sum(item["judge"][score] for item in judged if item["judge"]) / len(judged), 4) if judged else None
            for score in SCORES
        },
        "failure_counts": dict(failure_counts(rows, arm)),
        "generic_fallback_count": sum(item["generic_fallback_used"] for item in judged),
    }


def regression_cause(control: dict[str, Any], treatment: dict[str, Any]) -> str:
    failures = set(treatment["failure_types"])
    if "HALLUCINATION" in failures or "UNSUPPORTED_CLAIM" in failures:
        return "UNSUPPORTED_EXPANSION"
    if "BAD_ABSTENTION" in failures:
        return "OVER_ABSTENTION"
    if "INCOMPLETE_ANSWER" in failures and treatment["generic_fallback_used"]:
        return "QUESTION_FIRST_ATTENTION_SHIFT"
    if "INCOMPLETE_ANSWER" in failures:
        return "SUPPORTED_FACT_OMITTED"
    if failures != set(control["failure_types"]):
        return "PROMPT_SENSITIVITY"
    return "OTHER_VERIFIED"


async def run() -> dict[str, Any]:
    lock = load_lock(LOCK_PATH)
    if errors := validate_lock(ROOT, lock):
        raise RuntimeError("Evaluation lock mismatch: " + ", ".join(errors))
    golden_rows = load_json(ROOT / lock["golden"]["path"])
    golden = {row["id"]: row for row in golden_rows}
    contexts = load_json(ROOT / lock["context_snapshot"]["path"])
    source_mapping = load_json(ROOT / "eval" / "source_mappings_enterprise_v1_2.json")
    requirements = source_mapping["entries"]
    mode_overrides = {
        case_id: EvidenceMode(item["expected_evidence_mode"])
        for case_id, item in requirements.items()
    }
    fixture_audit = audit_fixture_integrity(
        golden_rows, contexts, mode_overrides=mode_overrides, requirements=requirements,
    )
    if fixture_audit["eval_fixture_error_count"]:
        raise RuntimeError("Fixture integrity failed before generation")
    control = {row["id"]: row for row in load_json(CONTROL_PATH)["cases"]}
    judge = SemanticJudgeAdapter(
        **judge_config(), timeout_seconds=45,
        cache_dir=RESULTS / "judge_cache_generator_evidence_use_canary", version=SEMANTIC_JUDGE_V1_3,
    )
    rows: list[dict[str, Any]] = []
    for case_id in KNOWLEDGE_IDS:
        source = control[case_id]
        context = contexts[case_id]
        treatment_applied = bool(context)
        reason = "NONEMPTY_AUTHORIZED_SOURCE_CONTEXT" if treatment_applied else "INTENTIONALLY_EMPTY_CONTEXT_PRESERVED"
        control_view = {
            "status": source["status"],
            "answer": source["answer"],
            "failure_types": source["judge"]["failure_types"],
            "judge": source["judge"],
            "generic_fallback_used": uses_generic_fallback(source["answer"]),
            "supported_evidence_used": bool(used_citation_ids(source["answer"], context)),
            "citation_status": source["judge"]["citation_correctness"],
            "generation_ms": source.get("generation_ms"),
        }
        if treatment_applied:
            prompt = evidence_salient_prompt(source["question"], context)
            try:
                raw_answer, answer, generation_ms, model = await generate(prompt, context)
                generation_error = None
            except Exception as exc:  # Do not store provider details or secrets.
                raw_answer = answer = ""
                generation_ms, model, generation_error = 0.0, "unknown", type(exc).__name__
            execution = None
            final = None
            if generation_error is None:
                execution = await judge.judge(
                    source["question"], build_authorized_evidence(context), answer,
                    expected_contract(source, golden[case_id]), used_citation_ids(answer, context), refresh=True,
                )
                status, final = semantic_status(execution, source.get("tool_results", []))
            else:
                status = "INFRA_ERROR"
            treatment_view = {
                "status": status,
                "raw_answer": raw_answer,
                "answer": answer,
                "failure_types": execution.result.failure_types if execution and execution.result else [],
                "judge": execution.to_dict().get("result") if execution else None,
                "final_pass": final,
                "infra_error_type": execution.infra_error_type if execution else "GENERATOR_ERROR",
                "generation_error": generation_error,
                "generic_fallback_used": uses_generic_fallback(answer),
                "supported_evidence_used": bool(used_citation_ids(answer, context)),
                "unsupported_detail_added": bool(set(execution.result.failure_types if execution and execution.result else []) & {"UNSUPPORTED_CLAIM", "HALLUCINATION"}),
                "citation_status": execution.result.citation_correctness if execution and execution.result else None,
                "generation_ms": generation_ms,
            }
            generator_model = model
            template = {"version": "evidence-salience-v1", "control": prompt_summary(generation_prompt(source["question"], context)), "treatment": prompt_summary(prompt)}
        else:
            treatment_view = {**control_view, "raw_answer": "CONTROL_REUSED_INTENTIONALLY_EMPTY_CONTEXT", "final_pass": source["final_pass"], "infra_error_type": None, "generation_error": None, "unsupported_detail_added": False}
            template = {"version": "control-retained-empty-context", "control": prompt_summary(generation_prompt(source["question"], context)), "treatment": None}
        route = route_chat_message(source["question"])
        row = {
            "id": case_id,
            "live_route": route.route,
            "live_route_applicability": case_id not in DIAGNOSTIC_ONLY_IDS,
            "diagnostic_only": case_id in DIAGNOSTIC_ONLY_IDS,
            "evaluation_mode": response_mode(golden[case_id]),
            "context_mode": EVIDENCE_MODE[case_id],
            "context_source_ids": [str(doc.get("doc_id") or doc.get("metadata", {}).get("source_id")) for doc in context],
            "context_characters": sum(len(str(doc.get("content", ""))) for doc in context),
            "context_approx_tokens": sum(len(str(doc.get("content", "")).split()) for doc in context),
            "treatment_applied": treatment_applied,
            "treatment_reason": reason,
            "template": template,
            "control": control_view,
            "treatment": treatment_view,
            "movement": movement(control_view, treatment_view),
            "regression_cause": None,
        }
        if row["movement"] == "REGRESSED":
            row["regression_cause"] = regression_cause(control_view, treatment_view)
        rows.append(row)

    eligible = [row for row in rows if row["treatment_applied"]]
    targets = [row for row in rows if row["id"] in CRITICAL_CONTROL_IDS]
    full_control, full_treatment = metrics(rows, "control"), metrics(rows, "treatment")
    eligible_control, eligible_treatment = metrics(eligible, "control"), metrics(eligible, "treatment")
    hard_gates = {
        "fixture_integrity_90_90": fixture_audit["passed"] == 90,
        "gt_027_retained": next(row for row in rows if row["id"] == "GT-027")["treatment"]["status"] == "PASS",
        "gt_047_retained": next(row for row in rows if row["id"] == "GT-047")["treatment"]["status"] == "PASS",
        "gt_048_retained": next(row for row in rows if row["id"] == "GT-048")["treatment"]["status"] == "PASS",
        "unsupported_claim_not_increased": full_treatment["failure_counts"].get("UNSUPPORTED_CLAIM", 0) <= full_control["failure_counts"].get("UNSUPPORTED_CLAIM", 0),
        "hallucination_not_increased": full_treatment["failure_counts"].get("HALLUCINATION", 0) <= full_control["failure_counts"].get("HALLUCINATION", 0),
        "bad_abstention_not_increased": full_treatment["failure_counts"].get("BAD_ABSTENTION", 0) <= full_control["failure_counts"].get("BAD_ABSTENTION", 0),
        "citation_error_not_increased": full_treatment["failure_counts"].get("CITATION_ERROR", 0) <= full_control["failure_counts"].get("CITATION_ERROR", 0),
        "no_dangerous_regression": not any(row["movement"] == "REGRESSED" and set(row["treatment"]["failure_types"]) & {"HALLUCINATION", "UNSUPPORTED_CLAIM", "BAD_ABSTENTION", "CITATION_ERROR"} for row in rows),
        "no_infra_error": full_treatment["infra_error"] == 0,
    }
    promising = (
        all(hard_gates.values())
        and eligible_treatment["semantic_pass"] > eligible_control["semantic_pass"]
        and eligible_treatment["generic_fallback_count"] < eligible_control["generic_fallback_count"]
    )
    return {
        "experiment": "knowledge_evidence_salience_slice",
        "decision": "PROMISING_FOR_PRODUCTION" if promising else "REJECT",
        "metadata": {
            "evaluation_contract": lock["evaluation_contract_version"],
            "evaluation_lock": str(LOCK_PATH.relative_to(ROOT)),
            "golden_hash": lock["golden"]["sha256"],
            "context_hash": lock["context_snapshot"]["sha256"],
            "generator_config_hash": lock["generator_config"]["hash"],
            "generator_model": generator_model if "generator_model" in locals() else "not_called",
            "judge_version": SEMANTIC_JUDGE_V1_3,
            "judge_prompt_hash": prompt_hash(SEMANTIC_JUDGE_V1_3),
            "retrieval_refreshed": False,
            "extra_llm_calls": 0,
            "treatment_generator_calls": len(eligible),
            "full_90_run": False,
        },
        "knowledge_case_ids": list(KNOWLEDGE_IDS),
        "treatment_eligible_case_ids": [row["id"] for row in eligible],
        "untouched_empty_context_case_ids": list(UNTOUCHED_EMPTY_IDS),
        "diagnostic_only_case_ids": list(DIAGNOSTIC_ONLY_IDS),
        "structural_change": "USER QUESTION first, then the same verbatim authorized evidence inside AUTHORIZED_SOURCE_DATA; no policy instructions added.",
        "fixture_integrity": fixture_audit,
        "cases": rows,
        "full_slice": {"control": full_control, "treatment": full_treatment},
        "eligible_subset": {"control": eligible_control, "treatment": eligible_treatment},
        "movements": dict(Counter(row["movement"] for row in rows)),
        "regressions": [row for row in rows if row["movement"] == "REGRESSED"],
        "hard_gates": hard_gates,
    }


def markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Knowledge Evidence-Salience Slice", "", f"- Decision: **{result['decision']}**", "- Full-90: not run.",
        f"- Treatment eligible: {len(result['treatment_eligible_case_ids'])}/23; intentionally empty cases retain control.",
        "", "## Case movement", "", "| ID | Applied | Control | Treatment | Movement |", "| --- | --- | --- | --- | --- |",
    ]
    lines += [f"| {row['id']} | {row['treatment_applied']} | {row['control']['status']} | {row['treatment']['status']} | {row['movement']} |" for row in result["cases"]]
    for label, values in (("Full 23-case slice", result["full_slice"]), ("Treatment-eligible subset", result["eligible_subset"])):
        lines += ["", f"## {label}", "", "| Metric | Control | Treatment |", "| --- | ---: | ---: |"]
        lines += [f"| Semantic pass | {values['control']['semantic_pass']} | {values['treatment']['semantic_pass']} |", f"| Semantic fail | {values['control']['semantic_fail']} | {values['treatment']['semantic_fail']} |", f"| Generic fallback | {values['control']['generic_fallback_count']} | {values['treatment']['generic_fallback_count']} |"]
        lines += [f"| {score} | {values['control']['averages'][score]} | {values['treatment']['averages'][score]} |" for score in SCORES]
    lines += ["", "## Hard gates", ""]
    lines += [f"- {key}: {value}" for key, value in result["hard_gates"].items()]
    return "\n".join(lines)


def main() -> None:
    result = asyncio.run(run())
    OUTPUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    OUTPUT_PATH.with_suffix(".md").write_text(markdown(result), encoding="utf-8")
    print(json.dumps({"decision": result["decision"], "full": result["full_slice"], "eligible": result["eligible_subset"], "gates": result["hard_gates"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
