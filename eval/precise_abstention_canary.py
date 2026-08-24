"""Canary for deterministic claim-specific abstention on empty evidence only."""
from __future__ import annotations

import asyncio
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from eval.evaluation_contract import load_lock, validate_lock
from eval.judge.semantic_judge import SEMANTIC_JUDGE_V1_3, SemanticJudgeAdapter, final_pass_decision, prompt_hash
from eval.knowledge_completeness_canary import uses_generic_fallback
from eval.semantic_judge_v1_2 import judge_config
from eval.semantic_judge_v1_3 import expected_contract
from src.prompts import build_authorized_evidence
from src.services.chat_routing_service import route_chat_message

ROOT = Path(__file__).parent.parent
RESULTS = ROOT / "eval" / "results"
LOCK_PATH = ROOT / "eval" / "snapshots" / "evaluation_lock_v1_2_full.json"
CONTROL_PATH = RESULTS / "baseline_control_context_v1_2.json"
OUTPUT_PATH = RESULTS / "precise_abstention_canary.json"
TARGET_IDS = ("GT-046", "GT-077", "GT-087")
CONTROL_IDS = ("GT-027", "GT-047", "GT-048")
CANARY_IDS = TARGET_IDS + CONTROL_IDS


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def move(control_status: str, treatment_status: str) -> str:
    if control_status != "PASS" and treatment_status == "PASS":
        return "IMPROVED"
    if control_status == "PASS" and treatment_status != "PASS":
        return "REGRESSED"
    return "UNCHANGED"


def candidate_path_eligible(*, route: str, authorized_source_count: int, web_source_count: int) -> bool:
    """Evaluation-only scope guard; it is deliberately not runtime code."""
    return route in {"knowledge", "incident"} and authorized_source_count == 0 and web_source_count == 0


def render_candidate_precise_abstention(user_query: str) -> str:
    """Candidate renderer retained only for the rejected canary artifact."""
    subject = " ".join((user_query or "").split()).rstrip("?.! ")
    return f"Tài liệu hiện có không xác nhận thông tin về: “{subject}”." if subject else "Tài liệu hiện có không xác nhận thông tin bạn đang hỏi."


def has_precise_subject(reply: str, question: str) -> bool:
    subject = question.strip().rstrip("?.! ")
    return "không xác nhận thông tin về" in reply.casefold() and subject.casefold() in reply.casefold()


async def run() -> dict[str, Any]:
    lock = load_lock(LOCK_PATH)
    if errors := validate_lock(ROOT, lock):
        raise RuntimeError("Evaluation lock mismatch: " + ", ".join(errors))
    control = {row["id"]: row for row in load_json(CONTROL_PATH)["cases"]}
    golden = {row["id"]: row for row in load_json(ROOT / lock["golden"]["path"])}
    contexts = load_json(ROOT / lock["context_snapshot"]["path"])
    judge = SemanticJudgeAdapter(
        **judge_config(), timeout_seconds=45,
        cache_dir=RESULTS / "judge_cache_precise_abstention_canary", version=SEMANTIC_JUDGE_V1_3,
    )
    rows: list[dict[str, Any]] = []
    for case_id in CANARY_IDS:
        saved = control[case_id]
        context = contexts[case_id]
        route = route_chat_message(saved["question"])
        target = case_id in TARGET_IDS
        applied = target and candidate_path_eligible(
            route=route.route, authorized_source_count=len(context), web_source_count=0,
        )
        if applied:
            answer = render_candidate_precise_abstention(saved["question"])
            execution = await judge.judge(
                saved["question"], build_authorized_evidence(context), answer,
                expected_contract(saved, golden[case_id]), [], refresh=False,
            )
            if execution.infra_error_type:
                status, final, failures, judge_result = "INFRA_ERROR", None, [], None
                infra_error_type = execution.infra_error_type
                observability = execution.to_dict().get("observability", [])
            else:
                assert execution.result is not None
                final = final_pass_decision(execution.result, tool_results=saved.get("tool_results", []))
                status = "PASS" if final["passed"] else "FAIL"
                failures, judge_result = execution.result.failure_types, execution.to_dict().get("result")
                infra_error_type = None
                observability = execution.to_dict().get("observability", [])
        else:
            answer, status, final = saved["answer"], saved["status"], saved.get("final_pass")
            failures, judge_result = saved["judge"]["failure_types"], saved["judge"]
            infra_error_type, observability = None, []
        treatment = {
            "answer": answer, "status": status, "failure_types": failures, "judge": judge_result,
            "infra_error_type": infra_error_type, "observability": observability,
            "generic_fallback_used": uses_generic_fallback(answer),
            "precise_missing_fact_named": has_precise_subject(answer, saved["question"]) if applied else False,
            "unsupported_detail_added": bool(set(failures) & {"UNSUPPORTED_CLAIM", "HALLUCINATION"}),
        }
        control_view = {
            "answer": saved["answer"], "status": saved["status"],
            "failure_types": saved["judge"]["failure_types"],
            "generic_fallback_used": uses_generic_fallback(saved["answer"]),
        }
        rows.append({
            "id": case_id, "group": "target" if target else "control", "route": route.route,
            "context_mode": "EMPTY" if not context else "NONEMPTY", "context_source_count": len(context),
            "precise_abstention_path": applied, "control": control_view, "treatment": treatment,
            "movement": move(control_view["status"], treatment["status"]),
        })
    targets = [row for row in rows if row["group"] == "target"]
    control_failures = Counter(failure for row in rows for failure in row["control"]["failure_types"])
    treatment_failures = Counter(failure for row in rows for failure in row["treatment"]["failure_types"])
    hard_gates = {
        "targets_apply_path": all(row["precise_abstention_path"] for row in targets),
        "gt_027_retained": next(row for row in rows if row["id"] == "GT-027")["treatment"]["status"] == "PASS",
        "gt_047_retained": next(row for row in rows if row["id"] == "GT-047")["treatment"]["status"] == "PASS",
        "gt_048_retained": next(row for row in rows if row["id"] == "GT-048")["treatment"]["status"] == "PASS",
        "no_unsupported_claim": treatment_failures["UNSUPPORTED_CLAIM"] <= control_failures["UNSUPPORTED_CLAIM"],
        "no_hallucination": treatment_failures["HALLUCINATION"] <= control_failures["HALLUCINATION"],
        "no_bad_abstention_increase": treatment_failures["BAD_ABSTENTION"] <= control_failures["BAD_ABSTENTION"],
        "no_citation_error": treatment_failures["CITATION_ERROR"] <= control_failures["CITATION_ERROR"],
        "no_infra_error": all(row["treatment"]["status"] != "INFRA_ERROR" for row in rows),
    }
    promising = all(hard_gates.values()) and sum(row["movement"] == "IMPROVED" for row in targets) >= 2
    return {
        "experiment": "precise_abstention_canary", "decision": "PROMISING" if promising else "REJECT",
        "metadata": {
            "evaluation_contract": lock["evaluation_contract_version"], "golden_hash": lock["golden"]["sha256"],
            "context_hash": lock["context_snapshot"]["sha256"], "judge_version": SEMANTIC_JUDGE_V1_3,
            "judge_prompt_hash": prompt_hash(SEMANTIC_JUDGE_V1_3), "generator_calls": 0,
            "extra_llm_calls": 0, "full_90_run": False,
        },
        "implementation": {
            "path": "deterministic", "trusted_fields": ["existing router route", "authorized source count", "web source count", "accepted user query"],
            "contract": "Evaluation-only candidate: no authorized or web source establishes the query; render only that the available documentation does not confirm the user-requested information.",
            "production_status": "ROLLED_BACK_AFTER_CANARY_REJECT",
        },
        "cases": rows,
        "summary": {
            "movements": dict(Counter(row["movement"] for row in rows)),
            "generic_fallback_before": sum(row["control"]["generic_fallback_used"] for row in targets),
            "generic_fallback_after": sum(row["treatment"]["generic_fallback_used"] for row in targets),
            "control_failure_counts": dict(control_failures), "treatment_failure_counts": dict(treatment_failures),
        },
        "hard_gates": hard_gates,
        "recommended_next_step": "FINAL_23_CASE_KNOWLEDGE_VALIDATION" if promising else "STOP_AND_KEEP_GENERIC_FALLBACK",
    }


def markdown(result: dict[str, Any]) -> str:
    lines = ["# Precise Abstention Canary", "", f"- Decision: **{result['decision']}**", "- Generator calls: 0.", "", "| ID | Route | Context | Applied | Control | Treatment | Movement |", "| --- | --- | --- | --- | --- | --- | --- |"]
    lines += [f"| {row['id']} | {row['route']} | {row['context_mode']} | {row['precise_abstention_path']} | {row['control']['status']} | {row['treatment']['status']} | {row['movement']} |" for row in result["cases"]]
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
