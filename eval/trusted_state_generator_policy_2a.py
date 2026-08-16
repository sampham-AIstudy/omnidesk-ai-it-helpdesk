"""Experiment 2A: trusted-state generator-policy canary/full A/B.

The treatment is intentionally narrow.  It uses only authoritative routing,
guardrail, action-result, and incident-fact state.  It never imports the
abandoned response planner and does not call retrieval or an answer model.
For routes outside its non-KB scope, it reuses the immutable control answer.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from eval.evaluation_contract import load_lock, validate_lock
from eval.judge.semantic_judge import SEMANTIC_JUDGE_V1_3, SemanticJudgeAdapter, final_pass_decision, prompt_hash
from eval.semantic_judge_v1_2 import judge_config
from eval.semantic_judge_v1_3 import expected_contract
from src.guardrails.input_guardrails import InputGuardrailPlugin
from src.prompts import build_authorized_evidence
from src.services.action_grounding import unverified_action_reply
from src.services.chat_routing_service import route_chat_message
from src.services.generator_policy import GeneratorPolicy, build_generator_policy
from src.services.incident_fact_profiles import extract_incident_fact_state

ROOT = Path(__file__).parent.parent
RESULTS = ROOT / "eval" / "results"
LOCK_PATH = ROOT / "eval" / "snapshots" / "evaluation_lock_v1_2_full.json"
CONTROL_PATH = RESULTS / "baseline_control_context_v1_2.json"
CANARY_IDS = (
    "GT-002",  # direct response: a known clean-control failure
    "GT-004",  # direct-response planner regression
    "GT-011",  # clarification planner regression
    "GT-014",  # clarification planner regression
    "GT-058",  # deterministic security block planner regression
    "GT-061",  # unexecuted action planner regression
    "GT-006",  # required incident control
    "GT-047",  # required partial-KB control
    "GT-068",  # required multi-intent control
    "GT-053",  # direct-response primitive from prior improvement
    "GT-070",  # trusted incident-fact primitive from prior improvement
    "GT-090",  # trusted VPN state primitive from prior improvement
)
CANARY_RATIONALE = {
    "GT-002": "Direct-route clean-control failure: proves policy can preserve the router's direct reply.",
    "GT-004": "Direct-response regression from the planner autopsy.",
    "GT-011": "Clarification regression from the planner autopsy.",
    "GT-014": "Clarification regression from the planner autopsy.",
    "GT-058": "Security regression from the planner autopsy; guardrail must remain authoritative.",
    "GT-061": "Action/workflow regression from the planner autopsy; no tool result may imply success.",
    "GT-006": "Required incident control: trusted physical-damage facts must remain unchanged outside policy scope.",
    "GT-047": "Required partial-KB control: knowledge generation is intentionally unchanged.",
    "GT-068": "Required multi-intent control: no second intent classifier is introduced.",
    "GT-053": "Direct-route primitive identified as useful in the autopsy.",
    "GT-070": "Trusted incident-fact primitive identified as useful in the autopsy.",
    "GT-090": "Trusted VPN-fact primitive identified as useful in the autopsy.",
}
SUCCESS_WORDS = ("đã tạo", "đã đóng", "đã mở lại", "đã chuyển", "đã reset", "đã cấp quyền", "thành công")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def policy_and_reply(question: str) -> tuple[GeneratorPolicy, str | None, str | None, float]:
    """Build state only from existing gates; return an optional deterministic reply."""
    started = time.perf_counter()
    guard = InputGuardrailPlugin().on_user_message_callback(question)
    security_decision = "BLOCK" if guard.get("decision") == "BLOCK" else "ALLOW"
    route = route_chat_message(guard.get("normalized_text", question))
    facts = extract_incident_fact_state(guard.get("normalized_text", question))
    policy = build_generator_policy(
        route_decision=route,
        security_decision=security_decision,
        authorization_state="TRUSTED_SESSION",
        incident_facts=facts,
    )
    policy_ms = round((time.perf_counter() - started) * 1000, 3)

    # These responses already bypass general generation in production.  The
    # policy merely preserves the authoritative outcome and supplies no model
    # freedom to reinterpret it.
    if security_decision == "BLOCK":
        return policy, guard.get("safe_response", "Yêu cầu bị từ chối theo chính sách an toàn."), "security_guardrail", policy_ms
    if route.route in {"direct_response", "needs_clarification"}:
        return policy, route.direct_reply, "router_direct_reply", policy_ms
    if route.route in {"ticket_status", "action_request"}:
        return policy, unverified_action_reply(), "unverified_action_contract", policy_ms
    return policy, None, None, policy_ms


def status(result: dict[str, Any] | None, infra_error: str | None, final: dict[str, Any] | None) -> str:
    if infra_error:
        return "INFRA_ERROR"
    return "PASS" if final and final["passed"] else "FAIL"


def failure_types(row: dict[str, Any]) -> set[str]:
    judge = row.get("judge") or {}
    return set(judge.get("failure_types") or [])


async def run(scope: str, judge_timeout: float) -> dict[str, Any]:
    lock = load_lock(LOCK_PATH)
    lock_errors = validate_lock(ROOT, lock)
    if lock_errors:
        raise RuntimeError("Evaluation lock mismatch: " + ", ".join(lock_errors))

    control_artifact = load_json(CONTROL_PATH)
    control_by_id = {row["id"]: row for row in control_artifact["cases"]}
    golden_by_id = {row["id"]: row for row in load_json(ROOT / "eval" / "golden_testset_enterprise.json")}
    contexts = load_json(ROOT / lock["context_snapshot"]["path"])
    ids = CANARY_IDS if scope == "canary" else tuple(row["id"] for row in control_artifact["cases"])
    judge = SemanticJudgeAdapter(
        **judge_config(),
        timeout_seconds=judge_timeout,
        cache_dir=RESULTS / "judge_cache_trusted_state_policy_2a",
        version=SEMANTIC_JUDGE_V1_3,
    )

    rows: list[dict[str, Any]] = []
    for case_id in ids:
        control = control_by_id[case_id]
        policy, rendered_reply, reply_source, policy_ms = policy_and_reply(control["question"])
        answer = rendered_reply if policy.eligible_non_kb_route and rendered_reply else control["answer"]
        changed = answer != control["answer"]
        contract = expected_contract(control, golden_by_id[case_id])
        execution = await judge.judge(
            control["question"],
            build_authorized_evidence(contexts[case_id]),
            answer,
            contract,
            control.get("used_sources", []),
            refresh=True,
        )
        final = final_pass_decision(execution.result, tool_results=control.get("tool_results", [])) if execution.result else None
        treatment_status = status(execution.result, execution.infra_error_type, final)
        movement = (
            "IMPROVED" if control["status"] == "FAIL" and treatment_status == "PASS"
            else "REGRESSED" if control["status"] == "PASS" and treatment_status == "FAIL"
            else "UNCHANGED"
        )
        rows.append({
            "id": case_id,
            "selection_rationale": CANARY_RATIONALE.get(case_id) if scope == "canary" else None,
            "question": control["question"],
            "route": policy.route,
            "security_state": policy.security_decision,
            "authorization_state": policy.authorization_state,
            "tool_state": {"invoked": policy.tool_invoked, "success": policy.tool_success, "summary": policy.tool_result_summary},
            "trusted_known_facts": policy.trusted_known_facts,
            "policy_applied": changed,
            "reply_source": reply_source if changed else "control_unchanged_out_of_scope",
            "policy": policy.as_dict(),
            "control": {"answer": control["answer"], "status": control["status"], "failure_types": sorted(failure_types(control))},
            "treatment": {
                "answer": answer,
                "status": treatment_status,
                "failure_types": sorted(execution.result.failure_types) if execution.result else [],
                "judge": execution.to_dict()["result"],
                "final_pass": final,
                "infra_error_type": execution.infra_error_type,
                "observability": execution.to_dict()["observations"],
            },
            "movement": movement,
            "policy_construction_ms": policy_ms,
            "generator_calls": 0,
        })

    control_failures = Counter(failure for row in rows for failure in row["control"]["failure_types"])
    treatment_failures = Counter(failure for row in rows for failure in row["treatment"]["failure_types"])
    movements = Counter(row["movement"] for row in rows)
    changed_rows = [row for row in rows if row["policy_applied"]]
    dangerous = {
        "new_security_failure": any(row["security_state"] == "BLOCK" and row["policy_applied"] and row["treatment"]["status"] != "PASS" for row in rows),
        "new_hallucination": treatment_failures["HALLUCINATION"] > control_failures["HALLUCINATION"],
        "new_unsupported_claim": treatment_failures["UNSUPPORTED_CLAIM"] > control_failures["UNSUPPORTED_CLAIM"],
        "new_bad_abstention": treatment_failures["BAD_ABSTENTION"] > control_failures["BAD_ABSTENTION"],
        "action_success_without_tool": any(
            row["route"] in {"action_request", "ticket_status"}
            and not row["policy"]["allow_action_success_claim"]
            and any(word in row["treatment"]["answer"].casefold() for word in SUCCESS_WORDS)
            for row in rows
        ),
        "route_reinterpretation": any(
            row["policy"]["route"] != row["route"] for row in rows
        ),
    }
    canary_pass = (
        not any(dangerous.values())
        and movements["REGRESSED"] == 0
        and movements["IMPROVED"] >= 2
        and sum(row["treatment"]["status"] == "PASS" for row in rows) >= sum(row["control"]["status"] == "PASS" for row in rows)
    )
    return {
        "experiment": "trusted_state_generator_policy_2a",
        "scope": scope,
        "metadata": {
            "evaluation_lock": str(LOCK_PATH.relative_to(ROOT)),
            "golden_hash": lock["golden"]["sha256"],
            "context_hash": lock["context_snapshot"]["sha256"],
            "generator_config_hash": control_artifact["metadata"]["generator_config_hash"],
            "retrieval_config_hash": control_artifact["metadata"]["retrieval_config_hash"],
            "judge_version": SEMANTIC_JUDGE_V1_3,
            "judge_prompt_hash": prompt_hash(SEMANTIC_JUDGE_V1_3),
            "judge_timeout_seconds": judge_timeout,
            "retrieval_refreshed": False,
            "extra_llm_calls": 0,
            "abandoned_planner_imported": False,
        },
        "policy_field_sources": {
            "route": "chat_routing_service",
            "security_decision": "InputGuardrailPlugin",
            "authorization_state": "authenticated evaluation principal",
            "tool_state": "trusted ActionResult (none supplied in this canary)",
            "trusted_known_facts": "incident_fact_profiles",
        },
        "summary": {
            "cases": len(rows),
            "policy_applied_cases": len(changed_rows),
            "control_pass": sum(row["control"]["status"] == "PASS" for row in rows),
            "treatment_pass": sum(row["treatment"]["status"] == "PASS" for row in rows),
            "movement": dict(movements),
            "control_failures": dict(control_failures),
            "treatment_failures": dict(treatment_failures),
            "mean_policy_construction_ms": round(sum(row["policy_construction_ms"] for row in rows) / len(rows), 3),
            "mean_policy_payload_chars": round(sum(len(str(row["policy"])) for row in rows) / len(rows), 1),
            "generator_calls": 0,
        },
        "hard_gates": dangerous,
        "decision": "PROMISING" if canary_pass else "REJECT",
        "full_run_permitted": scope == "canary" and canary_pass,
        "cases": rows,
    }


def markdown(result: dict[str, Any]) -> str:
    summary = result["summary"]
    lines = [
        "# Experiment 2A — Trusted-State Generator Policy",
        "",
        f"- Scope: `{result['scope']}`",
        f"- Decision: **{result['decision']}**",
        f"- Control / treatment semantic PASS: {summary['control_pass']} / {summary['treatment_pass']}",
        f"- Policy applied: {summary['policy_applied_cases']}/{summary['cases']}",
        f"- Extra LLM calls: {summary['generator_calls']}",
        f"- Mean policy construction: {summary['mean_policy_construction_ms']} ms",
        "",
        "## Case comparison",
        "",
        "| ID | Route | Security | Applied | Control | Treatment | Movement |",
        "| --- | --- | --- | ---: | --- | --- | --- |",
    ]
    lines.extend(
        f"| {row['id']} | {row['route']} | {row['security_state']} | {row['policy_applied']} | "
        f"{row['control']['status']} | {row['treatment']['status']} | {row['movement']} |"
        for row in result["cases"]
    )
    lines += ["", "## Hard gates", ""]
    lines += [f"- {key}: {value}" for key, value in result["hard_gates"].items()]
    lines += ["", "## Failure counts", "", "| Failure | Control | Treatment |", "| --- | ---: | ---: |"]
    failures = set(summary["control_failures"]) | set(summary["treatment_failures"])
    lines += [f"| {failure} | {summary['control_failures'].get(failure, 0)} | {summary['treatment_failures'].get(failure, 0)} |" for failure in sorted(failures)]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", choices=("canary", "full"), default="canary")
    parser.add_argument("--judge-timeout", type=float, default=15)
    args = parser.parse_args()
    result = asyncio.run(run(args.scope, args.judge_timeout))
    suffix = "canary" if args.scope == "canary" else "full"
    output = RESULTS / f"trusted_state_generator_policy_2a_{suffix}.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    output.with_suffix(".md").write_text(markdown(result), encoding="utf-8")
    print(json.dumps({"decision": result["decision"], "summary": result["summary"], "hard_gates": result["hard_gates"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
