"""Five-case generation canary after contract v1.2 preconditions pass."""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_core.messages import HumanMessage, SystemMessage

from eval.evaluation_contract import load_lock, validate_lock
from eval.judge.semantic_judge import SEMANTIC_JUDGE_V1_3, SemanticJudgeAdapter, final_pass_decision, prompt_hash
from eval.semantic_judge_v1_2 import judge_config
from eval.semantic_judge_v1_3 import expected_contract
from src.prompts import PRODUCTION_RAG_SYSTEM_PROMPT, build_authorized_evidence
from src.services.chat_response_planning import (
    build_response_plan,
    minimal_incident_triage_reply,
    multi_intent_reply,
    partial_evidence_reply,
)
from src.services.llm import get_rag_llm

ROOT = Path(__file__).parent.parent
RESULTS = ROOT / "eval" / "results"
CANARY_IDS = ("GT-006", "GT-023", "GT-047", "GT-048", "GT-068")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def contract_metadata(case_id: str) -> dict[str, Any]:
    if case_id == "GT-006":
        return {"knowledge_answerability": "root_cause_unknown", "workflow_actionability": True, "blocking_clarification": []}
    if case_id == "GT-068":
        return {"knowledge_answerability": "policy_unknown", "workflow_actionability": True, "blocking_clarification": []}
    return {"workflow_actionability": case_id == "GT-023"}


async def generate(question: str, context: list[dict[str, Any]]) -> tuple[str, dict[str, Any], float, int]:
    started = time.perf_counter()
    plan = build_response_plan(question, context)
    planning_ms = round((time.perf_counter() - started) * 1000, 3)
    for reply in (minimal_incident_triage_reply(plan), multi_intent_reply(plan), partial_evidence_reply(plan, context)):
        if reply:
            return reply, plan.as_dict(), planning_ms, 0
    prompt = (
        f"[AUTHORIZED_EVIDENCE]\n{build_authorized_evidence(context)}\n\n{plan.as_prompt_block()}\n\n"
        f"[USER QUESTION]\n{question}\n\n"
        "Trả lời ngắn gọn bằng tiếng Việt. Address every requested part, not necessarily answer every part: "
        "answer supported parts, abstain specifically for unsupported parts, and ask only required user facts."
    )
    response = await get_rag_llm().ainvoke([SystemMessage(content=PRODUCTION_RAG_SYSTEM_PROMPT), HumanMessage(content=prompt)])
    return str(response.content).strip(), plan.as_dict(), planning_ms, 1


async def run() -> dict[str, Any]:
    lock = load_lock(ROOT / "eval" / "snapshots" / "evaluation_lock_v1_2.json")
    errors = validate_lock(ROOT, lock)
    if errors:
        raise RuntimeError("Evaluation lock mismatch: " + ", ".join(errors))
    baseline = {row["id"]: row for row in load_json(RESULTS / "baseline_v1_1.json")["cases"]}
    prior = {row["id"]: row for row in load_json(RESULTS / "semantic_judge_v1_3.json")["cases"]}
    golden = {row["id"]: row for row in load_json(ROOT / "eval" / "golden_testset_enterprise.json")}
    contexts = load_json(ROOT / lock["context_snapshot"]["path"])
    config = judge_config()
    judge = SemanticJudgeAdapter(**config, timeout_seconds=45, cache_dir=RESULTS / "judge_cache_response_planner_exp1_2", version=SEMANTIC_JUDGE_V1_3)
    rows: list[dict[str, Any]] = []
    for case_id in CANARY_IDS:
        source = baseline[case_id]
        answer, plan, latency, calls = await generate(source["question"], contexts[case_id])
        contract = expected_contract(source, golden[case_id])
        contract["evaluation_metadata"] = contract_metadata(case_id)
        execution = await judge.judge(source["question"], build_authorized_evidence(contexts[case_id]), answer, contract, source.get("used_sources", []), refresh=True)
        final = final_pass_decision(execution.result, tool_results=source.get("tool_results", [])) if execution.result else None
        status = "INFRA_ERROR" if execution.infra_error_type else "PASS" if final and final["passed"] else "FAIL"
        old_status = prior[case_id]["status"]
        delta = "IMPROVED" if old_status == "FAIL" and status == "PASS" else "REGRESSED" if old_status == "PASS" and status == "FAIL" else "UNCHANGED"
        rows.append({"id": case_id, "question": source["question"], "old": prior[case_id], "new": {"answer": answer, "plan": plan, "evaluation_metadata": contract["evaluation_metadata"], "judge": execution.to_dict()["result"], "observability": execution.to_dict()["observations"], "infra_error_type": execution.infra_error_type, "final_pass": final, "status": status, "planning_ms": latency, "generator_calls": calls}, "delta": delta})
    blocked = {"UNSUPPORTED_CLAIM", "HALLUCINATION", "BAD_ABSTENTION", "INCORRECT_REFUSAL", "TOOL_GROUNDING_ERROR"}
    failures = {failure for row in rows if row["new"]["judge"] for failure in row["new"]["judge"]["failure_types"]}
    reasons = [f"{row['id']}={row['new']['status']}" for row in rows if row["new"]["status"] != "PASS"]
    if failures & blocked:
        reasons.append("blocked failures: " + ", ".join(sorted(failures & blocked)))
    return {"experiment": "response_planner_exp1_2", "metadata": {"evaluation_lock": "evaluation_lock_v1_2.json", "judge_version": SEMANTIC_JUDGE_V1_3, "judge_prompt_hash": prompt_hash(SEMANTIC_JUDGE_V1_3), "retrieval_refreshed": False}, "cases": rows, "summary": {"generator_calls": sum(row["new"]["generator_calls"] for row in rows), "extra_planner_llm_calls": 0, "mean_planning_ms": round(sum(row["new"]["planning_ms"] for row in rows) / len(rows), 3)}, "canary_gate": {"decision": "PASS" if not reasons else "FAIL", "reasons": reasons, "failure_types": sorted(failures)}}


def markdown(result: dict[str, Any]) -> str:
    lines = ["# Response Planner Experiment 1.2 — contract-repaired canary", "", "| Case | Before | After | Delta |", "| --- | --- | --- | --- |"]
    lines.extend(f"| {row['id']} | {row['old']['status']} | {row['new']['status']} | {row['delta']} |" for row in result["cases"])
    lines.extend(["", f"- Canary gate: **{result['canary_gate']['decision']}**", f"- Generator calls: {result['summary']['generator_calls']}", "- Extra planner LLM calls: 0", f"- Mean planner latency: {result['summary']['mean_planning_ms']} ms"])
    return "\n".join(lines)


def main() -> None:
    result = asyncio.run(run())
    path = RESULTS / "response_planner_exp1_2_canary.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    path.with_suffix(".md").write_text(markdown(result), encoding="utf-8")
    print(json.dumps({"canary_gate": result["canary_gate"], "summary": result["summary"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
