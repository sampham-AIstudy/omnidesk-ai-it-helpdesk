"""Experiment 2A.1: deterministic wording for trusted action state only."""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from eval.evaluation_contract import load_lock, validate_lock
from eval.judge.semantic_judge import SEMANTIC_JUDGE_V1_3, SemanticJudgeAdapter, final_pass_decision, prompt_hash
from eval.semantic_judge_v1_2 import judge_config
from eval.semantic_judge_v1_3 import expected_contract
from src.guardrails.input_guardrails import InputGuardrailPlugin
from src.prompts import build_authorized_evidence
from src.services.action_grounding import ActionResult, action_execution_state, action_state_reply, allowed_action_facts
from src.services.chat_routing_service import route_chat_message

ROOT = Path(__file__).parent.parent
RESULTS = ROOT / "eval" / "results"
LOCK_PATH = ROOT / "eval" / "snapshots" / "evaluation_lock_v1_2_full.json"
CONTROL_PATH = RESULTS / "baseline_control_context_v1_2.json"
PRIOR_CANARY = RESULTS / "trusted_state_generator_policy_2a_canary.json"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def fixture_rows() -> list[dict[str, Any]]:
    """Controlled tool fixtures exercise renderer branches without a model call."""
    return [
        {
            "id": "ACT-001-NOT-INVOKED",
            "kind": "action_fixture",
            "question": "Tạo ticket cho tôi.",
            "action_result": None,
            "expected": "Chưa có thay đổi nào được thực hiện.",
            "purpose": "Action requested but no trusted tool invocation.",
        },
        {
            "id": "ACT-002-SERVICE-NOT-INVOKED",
            "kind": "action_fixture",
            "question": "Tôi cần laptop mới cho nhân viên mới.",
            "action_result": None,
            "expected": "Chưa có thay đổi nào được thực hiện.",
            "purpose": "Service request with no action execution.",
        },
        {
            "id": "ACT-003-SUCCEEDED",
            "kind": "action_fixture",
            "question": "Chuyển ticket cho kỹ thuật viên.",
            "action_result": ActionResult(success=True, resource_id="INC-1234", persisted_state="waiting_for_agent"),
            "expected": "Đã cập nhật INC-1234 sang trạng thái waiting_for_agent.",
            "purpose": "Successful tool result exposes only returned ID and status.",
        },
    ]


def render_golden_case(case_id: str, question: str, *, failed_result: ActionResult | None = None) -> tuple[str, dict[str, Any], str]:
    """Use existing guards/routes; no action or security state is inferred here."""
    guard = InputGuardrailPlugin().on_user_message_callback(question)
    if guard.get("decision") == "BLOCK":
        return guard["safe_response"], {"security_decision": "BLOCK", "route": "SECURITY_BLOCK"}, "DETERMINISTIC_SECURITY"

    route = route_chat_message(guard.get("normalized_text", question))
    if case_id == "GT-061":
        result = failed_result
        return action_state_reply(result), {
            "security_decision": "ALLOW",
            "route": route.route,
            "tool_invoked": result is not None,
            "tool_success": result.success if result else None,
            "trusted_action_facts": allowed_action_facts(result),
            "action_state": action_execution_state(result).value,
            "trusted_action_source": "golden context_info tool-result fixture",
        }, "DETERMINISTIC_ACTION_STATE"
    return route.direct_reply or "", {
        "security_decision": "ALLOW",
        "route": route.route,
        "tool_invoked": False,
        "tool_success": None,
        "trusted_action_facts": {},
    }, "DETERMINISTIC_ROUTER"


async def run() -> dict[str, Any]:
    lock = load_lock(LOCK_PATH)
    errors = validate_lock(ROOT, lock)
    if errors:
        raise RuntimeError("Evaluation lock mismatch: " + ", ".join(errors))
    control = {row["id"]: row for row in load_json(CONTROL_PATH)["cases"]}
    old_canary = {row["id"]: row for row in load_json(PRIOR_CANARY)["cases"]}
    golden = {row["id"]: row for row in load_json(ROOT / "eval" / "golden_testset_enterprise.json")}
    contexts = load_json(ROOT / lock["context_snapshot"]["path"])
    judge = SemanticJudgeAdapter(
        **judge_config(), timeout_seconds=45,
        cache_dir=RESULTS / "judge_cache_action_state_wording_2a_1", version=SEMANTIC_JUDGE_V1_3,
    )
    rows: list[dict[str, Any]] = []
    # GT-061 provides the trusted failed action result declared by its golden
    # fixture.  The error is intentionally not rendered because DATABASE_TIMEOUT
    # is not an allowlisted public-facing error summary.
    for case_id in ("GT-061", "GT-058", "GT-053"):
        source = control[case_id]
        result = ActionResult(success=False, error_code="DATABASE_TIMEOUT") if case_id == "GT-061" else None
        started = time.perf_counter()
        answer, state, response_path = render_golden_case(case_id, source["question"], failed_result=result)
        latency_ms = round((time.perf_counter() - started) * 1000, 3)
        contract = expected_contract(source, golden[case_id])
        execution = await judge.judge(
            source["question"], build_authorized_evidence(contexts[case_id]), answer,
            contract, source.get("used_sources", []), refresh=True,
        )
        final = final_pass_decision(execution.result, tool_results=source.get("tool_results", [])) if execution.result else None
        treatment_status = "INFRA_ERROR" if execution.infra_error_type else "PASS" if final and final["passed"] else "FAIL"
        rows.append({
            "id": case_id,
            "kind": "golden",
            "question": source["question"],
            "response_path": response_path,
            "trusted_state": state,
            "answer": answer,
            "control": {"status": source["status"], "failure_types": source["judge"]["failure_types"], "answer": source["answer"]},
            "prior_2a": old_canary.get(case_id, {}).get("treatment"),
            "treatment": {
                "status": treatment_status,
                "failure_types": execution.result.failure_types if execution.result else [],
                "judge": execution.to_dict()["result"],
                "infra_error_type": execution.infra_error_type,
            },
            "latency_ms": latency_ms,
            "generator_calls": 0,
        })

    for fixture in fixture_rows():
        started = time.perf_counter()
        answer = action_state_reply(fixture["action_result"])
        rows.append({
            "id": fixture["id"],
            "kind": fixture["kind"],
            "question": fixture["question"],
            "purpose": fixture["purpose"],
            "response_path": "DETERMINISTIC_ACTION_STATE",
            "trusted_state": {
                "tool_invoked": fixture["action_result"] is not None,
                "tool_success": fixture["action_result"].success if fixture["action_result"] else None,
                "trusted_action_facts": allowed_action_facts(fixture["action_result"]),
                "action_state": action_execution_state(fixture["action_result"]).value,
            },
            "answer": answer,
            "expected": fixture["expected"],
            "deterministic_pass": answer == fixture["expected"],
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
            "generator_calls": 0,
        })

    golden_rows = [row for row in rows if row["kind"] == "golden"]
    fixture_pass = all(row["deterministic_pass"] for row in rows if row["kind"] == "action_fixture")
    gt061 = next(row for row in golden_rows if row["id"] == "GT-061")
    hard_gates = {
        "gt_061_pass": gt061["treatment"]["status"] == "PASS",
        "new_unsupported_claim": any("UNSUPPORTED_CLAIM" in row["treatment"]["failure_types"] for row in golden_rows),
        "new_hallucination": any("HALLUCINATION" in row["treatment"]["failure_types"] for row in golden_rows),
        "security_regression": next(row for row in golden_rows if row["id"] == "GT-058")["treatment"]["status"] != "PASS",
        "direct_response_regression": next(row for row in golden_rows if row["id"] == "GT-053")["treatment"]["status"] != "PASS",
        "tool_grounding_error": any("TOOL_GROUNDING_ERROR" in row["treatment"]["failure_types"] for row in golden_rows),
        "fixture_contracts_pass": fixture_pass,
    }
    promising = all((value is False) for key, value in hard_gates.items() if key in {
        "new_unsupported_claim", "new_hallucination", "security_regression", "direct_response_regression", "tool_grounding_error"
    }) and hard_gates["gt_061_pass"] and fixture_pass
    return {
        "experiment": "action_state_wording_2a_1",
        "metadata": {
            "evaluation_lock": str(LOCK_PATH.relative_to(ROOT)),
            "golden_hash": lock["golden"]["sha256"],
            "context_hash": lock["context_snapshot"]["sha256"],
            "judge_version": SEMANTIC_JUDGE_V1_3,
            "judge_prompt_hash": prompt_hash(SEMANTIC_JUDGE_V1_3),
            "retrieval_refreshed": False,
            "extra_generator_llm_calls": 0,
            "full_90_run": False,
        },
        "contract": {
            "NOT_INVOKED": "Chưa có thay đổi nào được thực hiện.",
            "FAILED": "Thao tác chưa hoàn tất, with an allowlisted trusted error only.",
            "SUCCEEDED": "Confirm only resource ID and persisted state returned by the tool.",
            "forbidden_without_trusted_state": ["workflow", "approval", "authorization", "permission", "confirmation", "policy"],
        },
        "hard_gates": hard_gates,
        "decision": "PROMISING" if promising else "REJECT",
        "rows": rows,
    }


def markdown(result: dict[str, Any]) -> str:
    lines = ["# Experiment 2A.1 — Action-State Wording Contract", "", f"- Decision: **{result['decision']}**", "- Extra generator LLM calls: 0", "- Full 90 run: no", "", "## Canary", "", "| ID | Path | State | Result |", "| --- | --- | --- | --- |"]
    for row in result["rows"]:
        state = row["trusted_state"].get("action_state", row["trusted_state"].get("security_decision", "-"))
        outcome = row.get("treatment", {}).get("status", row.get("deterministic_pass"))
        lines.append(f"| {row['id']} | {row['response_path']} | {state} | {outcome} |")
    lines += ["", "## Hard gates", ""]
    lines += [f"- {key}: {value}" for key, value in result["hard_gates"].items()]
    return "\n".join(lines)


def main() -> None:
    result = asyncio.run(run())
    output = RESULTS / "action_state_wording_2a_1_canary.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    output.with_suffix(".md").write_text(markdown(result), encoding="utf-8")
    print(json.dumps({"decision": result["decision"], "hard_gates": result["hard_gates"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
