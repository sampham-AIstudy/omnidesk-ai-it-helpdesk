"""Narrow knowledge-completeness canary on the immutable v1.2 snapshot.

Only the production knowledge instruction differs from the saved clean-control
answers.  Retrieval, contexts, routing, the Judge and action grounding remain
unchanged.  This is deliberately not a second planner.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_core.messages import HumanMessage, SystemMessage

from eval.evaluation_contract import load_lock, validate_lock
from eval.judge.semantic_judge import SEMANTIC_JUDGE_V1_3, SemanticJudgeAdapter, final_pass_decision, prompt_hash
from eval.semantic_judge_v1_2 import judge_config
from eval.semantic_judge_v1_3 import expected_contract
from src.prompts import (
    PRODUCTION_RAG_SYSTEM_PROMPT,
    build_authorized_evidence,
    evidence_source_ids,
    remove_unrecognized_source_ids,
)
from src.services.llm import get_rag_llm

ROOT = Path(__file__).parent.parent
RESULTS = ROOT / "eval" / "results"
LOCK_PATH = ROOT / "eval" / "snapshots" / "evaluation_lock_v1_2_full.json"
CONTROL_PATH = RESULTS / "baseline_control_context_v1_2.json"
OUTPUT_PATH = RESULTS / "knowledge_completeness_canary.json"

TARGET_IDS = ("GT-020", "GT-029", "GT-046", "GT-067", "GT-077", "GT-087")
POSITIVE_CONTROL_IDS = ("GT-027", "GT-047", "GT-048", "GT-049", "GT-088")
CANARY_IDS = TARGET_IDS + POSITIVE_CONTROL_IDS

_CITATION = re.compile(r"\[(?:SOURCE_ID:\s*)?([A-Za-z0-9][A-Za-z0-9_.:-]{0,127})\]", re.IGNORECASE)
_GENERIC_FALLBACK = re.compile(
    r"(?:rất tiếc[, ]*)?thông tin (?:hiện có|được cung cấp).{0,50}(?:chưa đủ|không đủ).{0,50}trả lời (?:câu hỏi|vấn đề)(?: này)?",
    re.IGNORECASE | re.DOTALL,
)
KNOWLEDGE_COMPLETENESS_ADDENDUM = """[KNOWLEDGE COMPLETENESS]
Với câu hỏi knowledge/RAG, phải dùng mọi evidence có liên quan trực tiếp trước khi dùng câu trả lời chung chung. Không dùng câu kiểu "thông tin hiện có chưa đủ để trả lời" nếu evidence vẫn xác nhận được một fact trọng yếu mà người dùng hỏi. Khi evidence chỉ xác nhận một phần, trả lời phần được xác nhận trước rồi nêu chính xác claim nào chưa thể xác nhận. Chỉ dùng từ chối toàn bộ khi không có claim trọng yếu nào trong câu hỏi được evidence hỗ trợ. Không suy ra policy, số liệu, bước thủ tục hoặc chi tiết còn thiếu chỉ để làm câu trả lời có vẻ đầy đủ."""


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def generation_prompt(question: str, context: list[dict[str, Any]]) -> str:
    """Keep the v1.2 fixed-evidence input shape; the system rule is the treatment."""
    return f"[AUTHORIZED_EVIDENCE]\n{build_authorized_evidence(context)}\n\n[USER QUESTION]\n{question}"


def treatment_system_prompt() -> str:
    """Insert the experimental instruction without changing the runtime prompt."""
    marker = "\n\n[CITATIONS]"
    assert marker in PRODUCTION_RAG_SYSTEM_PROMPT
    return PRODUCTION_RAG_SYSTEM_PROMPT.replace(marker, f"\n\n{KNOWLEDGE_COMPLETENESS_ADDENDUM}{marker}", 1)


def used_citation_ids(answer: str, context: list[dict[str, Any]]) -> list[str]:
    allowed = evidence_source_ids(context)
    return list(dict.fromkeys(match.group(1) for match in _CITATION.finditer(answer or "") if match.group(1) in allowed))


def uses_generic_fallback(answer: str) -> bool:
    return bool(_GENERIC_FALLBACK.search(answer or ""))


def answer_usage(answer: str, context: list[dict[str, Any]]) -> dict[str, bool]:
    return {
        "USED_SUPPORTED_EVIDENCE": bool(used_citation_ids(answer, context)),
        "USED_PRECISE_ABSTENTION": any(token in (answer or "").casefold() for token in ("không xác nhận", "không thể xác nhận", "không được cung cấp", "không đề cập")),
        "USED_GENERIC_FALLBACK": uses_generic_fallback(answer),
        "ADDED_UNSUPPORTED_DETAIL": False,
    }


async def generate_answer(question: str, context: list[dict[str, Any]]) -> tuple[str, float, str]:
    llm = get_rag_llm()
    started = time.perf_counter()
    response = await llm.ainvoke([
        SystemMessage(content=treatment_system_prompt()),
        HumanMessage(content=generation_prompt(question, context)),
    ])
    answer = str(response.content).strip()
    answer, _ = remove_unrecognized_source_ids(answer, evidence_source_ids(context))
    model = str(getattr(llm, "model", getattr(llm, "model_name", "configured production default")))
    return answer, round((time.perf_counter() - started) * 1000, 3), model


def treatment_status(execution: Any, tool_results: list[dict[str, Any]]) -> tuple[str, dict[str, Any] | None]:
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
        cache_dir=RESULTS / "judge_cache_knowledge_completeness_canary", version=SEMANTIC_JUDGE_V1_3,
    )
    rows: list[dict[str, Any]] = []
    for case_id in CANARY_IDS:
        source = control[case_id]
        context = contexts[case_id]
        try:
            answer, generation_ms, model = await generate_answer(source["question"], context)
            generation_error = None
        except Exception as exc:  # Do not serialize provider detail or credentials.
            answer, generation_ms, model = "", 0.0, "configured production default"
            generation_error = type(exc).__name__
        execution = None
        final = None
        if generation_error is None:
            execution = await judge.judge(
                source["question"], build_authorized_evidence(context), answer,
                expected_contract(source, golden[case_id]), used_citation_ids(answer, context), refresh=True,
            )
            status, final = treatment_status(execution, source.get("tool_results", []))
        else:
            status = "INFRA_ERROR"
        treatment = {
            "status": status,
            "answer": answer,
            "failure_types": execution.result.failure_types if execution and execution.result else [],
            "judge": execution.to_dict().get("result") if execution else None,
            "final_pass": final,
            "infra_error_type": execution.infra_error_type if execution else "GENERATOR_ERROR",
            "generation_error": generation_error,
            "generation_ms": generation_ms,
            "used_citation_ids": used_citation_ids(answer, context),
            "usage": answer_usage(answer, context),
        }
        control_view = {
            "status": source["status"],
            "answer": source["answer"],
            "failure_types": source["judge"]["failure_types"],
            "judge": source["judge"],
            "generation_ms": source.get("generation_ms"),
            "usage": answer_usage(source["answer"], context),
        }
        rows.append({
            "id": case_id,
            "group": "target" if case_id in TARGET_IDS else "positive_control",
            "question": source["question"],
            "test_type": source["test_type"],
            "context_source_ids": [str(doc.get("doc_id") or doc.get("metadata", {}).get("source_id")) for doc in context],
            "control": control_view,
            "treatment": treatment,
            "movement": movement(control_view, treatment),
            "non_improvement_reason": None,
        })
        if model:
            generator_model = model

    for row in rows:
        if row["group"] != "target" or row["movement"] == "IMPROVED":
            continue
        treatment = row["treatment"]
        if treatment["generation_error"]:
            reason = "OTHER_VERIFIED"
        elif treatment["usage"]["USED_GENERIC_FALLBACK"]:
            reason = "GENERIC_FALLBACK_STILL_DOMINATES"
        elif not treatment["usage"]["USED_SUPPORTED_EVIDENCE"] and row["context_source_ids"]:
            reason = "EVIDENCE_NOT_SELECTED_BY_GENERATOR"
        elif "INCOMPLETE_ANSWER" in treatment["failure_types"]:
            reason = "SUPPORTED_FACT_STILL_OMITTED"
        elif "BAD_ABSTENTION" in treatment["failure_types"]:
            reason = "ABSTENTION_BOUNDARY_WRONG"
        else:
            reason = "PROMPT_RULE_NOT_TRIGGERED"
        row["non_improvement_reason"] = reason

    def failures(arm: str) -> Counter[str]:
        return Counter(failure for row in rows for failure in row[arm]["failure_types"])

    control_failures, treatment_failures = failures("control"), failures("treatment")
    targets = [row for row in rows if row["group"] == "target"]
    positives = [row for row in rows if row["group"] == "positive_control"]
    hard_gates = {
        "targets_improved_at_least_3": sum(row["movement"] == "IMPROVED" for row in targets) >= 3,
        "positive_control_pass_retained": all(row["treatment"]["status"] == "PASS" for row in positives),
        "gt_047_retained": next(row for row in rows if row["id"] == "GT-047")["treatment"]["status"] == "PASS",
        "gt_048_retained": next(row for row in rows if row["id"] == "GT-048")["treatment"]["status"] == "PASS",
        "unsupported_claim_not_increased": treatment_failures["UNSUPPORTED_CLAIM"] <= control_failures["UNSUPPORTED_CLAIM"],
        "hallucination_not_increased": treatment_failures["HALLUCINATION"] <= control_failures["HALLUCINATION"],
        "bad_abstention_not_increased": treatment_failures["BAD_ABSTENTION"] <= control_failures["BAD_ABSTENTION"],
        "citation_failure_not_increased": treatment_failures["CITATION_ERROR"] <= control_failures["CITATION_ERROR"],
        "no_regression": not any(row["movement"] == "REGRESSED" for row in rows),
        "no_infra_error": not any(row["treatment"]["status"] == "INFRA_ERROR" for row in rows),
    }
    promising = all(hard_gates.values())
    return {
        "experiment": "knowledge_completeness_canary",
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
            "control_system_prompt_hash": hashlib.sha256(PRODUCTION_RAG_SYSTEM_PROMPT.encode()).hexdigest(),
            "treatment_system_prompt_hash": hashlib.sha256(treatment_system_prompt().encode()).hexdigest(),
            "retrieval_refreshed": False,
            "extra_llm_calls": 0,
            "full_90_run": False,
            "prompt_character_delta": len(treatment_system_prompt()) - len(PRODUCTION_RAG_SYSTEM_PROMPT),
        },
        "rule": "Use materially relevant authorized evidence before broad abstention; answer supported portions, name unsupported claims precisely, and never invent missing detail.",
        "cases": rows,
        "summary": {
            "targets": len(targets),
            "positive_controls": len(positives),
            "movements": dict(Counter(row["movement"] for row in rows)),
            "target_movements": dict(Counter(row["movement"] for row in targets)),
            "control_failure_counts": dict(control_failures),
            "treatment_failure_counts": dict(treatment_failures),
            "generic_fallback_before": sum(row["control"]["usage"]["USED_GENERIC_FALLBACK"] for row in rows),
            "generic_fallback_after": sum(row["treatment"]["usage"]["USED_GENERIC_FALLBACK"] for row in rows),
            "mean_generation_ms_control": round(sum(row["control"]["generation_ms"] or 0 for row in rows) / len(rows), 3),
            "mean_generation_ms_treatment": round(sum(row["treatment"]["generation_ms"] for row in rows) / len(rows), 3),
        },
        "hard_gates": hard_gates,
    }


def markdown(result: dict[str, Any]) -> str:
    summary = result["summary"]
    lines = [
        "# Knowledge Completeness Canary",
        "",
        f"- Decision: **{result['decision']}**",
        "- Scope: 11 knowledge cases only; no full-90 run.",
        "- Frozen context snapshot: v1.2; retrieval was not refreshed.",
        "- Extra LLM calls: 0 (one existing generator call per treatment case).",
        "",
        "## Case comparison",
        "",
        "| ID | Group | Control | Treatment | Movement |", "| --- | --- | --- | --- | --- |",
    ]
    lines += [f"| {row['id']} | {row['group']} | {row['control']['status']} | {row['treatment']['status']} | {row['movement']} |" for row in result["cases"]]
    lines += ["", "## Failure counts", "", "| Failure | Control | Treatment |", "| --- | ---: | ---: |"]
    all_failures = sorted(set(summary["control_failure_counts"]) | set(summary["treatment_failure_counts"]))
    lines += [f"| {failure} | {summary['control_failure_counts'].get(failure, 0)} | {summary['treatment_failure_counts'].get(failure, 0)} |" for failure in all_failures]
    lines += ["", "## Usage and performance", "", f"- Generic fallback: {summary['generic_fallback_before']} → {summary['generic_fallback_after']}", f"- Mean generation latency: {summary['mean_generation_ms_control']} ms → {summary['mean_generation_ms_treatment']} ms", "", "## Hard gates", ""]
    lines += [f"- {name}: {value}" for name, value in result["hard_gates"].items()]
    lines += ["", "## Target diagnostics", ""]
    for row in result["cases"]:
        if row["group"] == "target" and row["non_improvement_reason"]:
            lines.append(f"- {row['id']}: {row['non_improvement_reason']}")
    return "\n".join(lines)


def main() -> None:
    result = asyncio.run(run())
    OUTPUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    OUTPUT_PATH.with_suffix(".md").write_text(markdown(result), encoding="utf-8")
    print(json.dumps({"decision": result["decision"], "summary": result["summary"], "hard_gates": result["hard_gates"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
