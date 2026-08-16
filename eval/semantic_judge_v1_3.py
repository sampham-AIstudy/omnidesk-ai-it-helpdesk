"""Human-calibrated, judge-only semantic evaluation for frozen v1.1 answers.

This runner never invokes retrieval or answer generation.  It deliberately
uses a new cache namespace and preserves all v1.1/v1.2 artifacts.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from eval.judge.semantic_judge import (
    FINAL_PASS_POLICY_VERSION,
    JUDGE_SCHEMA_VERSION,
    SEMANTIC_JUDGE_V1_3,
    SemanticJudgeAdapter,
    final_pass_decision,
    prompt_hash,
)
from eval.semantic_judge_v1_2 import judge_config, load_json
from src.prompts import build_authorized_evidence

ROOT = Path(__file__).parent.parent
RESULTS = ROOT / "eval" / "results"
SCORES = ("faithfulness", "completeness", "relevance", "correct_abstention", "citation_correctness")


def response_mode(golden: dict[str, Any]) -> str:
    """Derive mode from the immutable evaluation manifest, never the model."""
    kind = golden.get("type", "")
    if golden.get("security_category") or kind in {"prompt_injection_rag_security", "hacking_dual_use", "memory_privacy", "tool_authorization"}:
        return "SECURITY_REFUSAL"
    if kind in {"small_talk", "user_anger_emotion", "rapid_followup"}:
        return "DIRECT_RESPONSE"
    if kind in {"out_of_scope_garbage", "no_answer_context"}:
        return "OUT_OF_SCOPE"
    if kind == "partial_context":
        return "PARTIAL_ANSWER"
    if kind == "multi_intent":
        return "MULTI_INTENT"
    if kind in {"ticket_operations", "human_escalation", "bad_tool_confirmation", "status_accuracy"}:
        return "ACTION_RESPONSE"
    if kind in {"ambiguous_incident", "minimum_clarification", "over_questioning"}:
        return "CLARIFICATION"
    if kind.startswith("incident_") or kind in {"network_vpn", "service_request_vs_incident", "source_relevance"}:
        return "INCIDENT_ASSISTANCE"
    return "KNOWLEDGE_ANSWER"


def expected_contract(source: dict[str, Any], golden: dict[str, Any]) -> dict[str, Any]:
    return {
        "response_mode": response_mode(golden),
        "test_type": golden.get("type", source.get("test_type")),
        "expected_route": golden.get("expected_route"),
        "expected_behavior": golden.get("expected_behavior", []),
        "must_not_do": golden.get("must_not_do", []),
        "context_info": golden.get("context_info"),
        "trusted_tool_results": source.get("tool_results", []),
    }


def status(row: dict[str, Any]) -> str:
    if row["infra_error_type"]:
        return "INFRA_ERROR"
    return "PASS" if row["final_pass"]["passed"] else "FAIL"


def run_summary(cases: list[dict[str, Any]]) -> dict[str, Any]:
    completed = [case for case in cases if case["status"] != "INFRA_ERROR"]
    averages = {
        score: round(sum(case["judge"][score] for case in completed) / len(completed), 4) if completed else None
        for score in SCORES
    }
    return {
        "semantic_eligible": len(cases),
        "successfully_judged": len(completed),
        "infra_error_count": len(cases) - len(completed),
        "infra_error_rate": round((len(cases) - len(completed)) / len(cases), 4) if cases else 0.0,
        "semantic_pass": sum(case["status"] == "PASS" for case in cases),
        "semantic_fail": sum(case["status"] == "FAIL" for case in cases),
        "averages": averages,
    }


def _band(score: float) -> str:
    return "high" if score == 1.0 else "medium" if score == 0.5 else "low"


def _human_band(human: dict[str, Any], score: str) -> str:
    value = human.get(score, "high")
    if isinstance(value, bool):
        return "high" if value else "low"
    return value


def review_calibration(cases: list[dict[str, Any]], calibration: dict[str, Any]) -> dict[str, Any]:
    by_id = {case["id"]: case for case in cases}
    split_results: dict[str, list[dict[str, Any]]] = defaultdict(list)
    all_rows: list[dict[str, Any]] = []
    for label in calibration["cases"]:
        case = by_id.get(label["case_id"])
        if not case:
            continue
        human = label["human"]
        row = {"case_id": label["case_id"], "split": label["split"], "response_mode": label["response_mode"],
               "human": human, "judge": case.get("judge"), "judge_semantic_pass": None,
               "classification": "INFRA_ERROR", "disagreement_dimension": None, "disagreement_reason": None}
        if case["status"] != "INFRA_ERROR":
            judge_pass = case["final_pass"]["passed"]
            row["judge_semantic_pass"] = judge_pass
            dimensions = [score.upper().replace("CORRECT_", "") for score in SCORES if _band(case["judge"][score]) != _human_band(human, score)]
            if judge_pass == human["semantic_pass"]:
                row["classification"] = "JUDGE_CORRECT"
                if dimensions:
                    row["disagreement_dimension"] = dimensions[0]
                    row["disagreement_reason"] = "DIMENSION_BAND_DIFFERENCE_FINAL_PASS_MATCHES"
            elif human["semantic_pass"]:
                row["classification"] = "JUDGE_TOO_STRICT"
                row["disagreement_dimension"] = "FINAL_PASS"
                row["disagreement_reason"] = "TOO_STRICT_" + (case["judge"]["failure_types"][0] if case["judge"]["failure_types"] else "FINAL_THRESHOLD")
            else:
                row["classification"] = "JUDGE_TOO_LENIENT"
                row["disagreement_dimension"] = "FINAL_PASS"
                row["disagreement_reason"] = "MISSED_EXPECTED_FAILURE"
        split_results[label["split"]].append(row)
        all_rows.append(row)

    def metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
        comparable = [row for row in rows if row["judge_semantic_pass"] is not None]
        if not comparable:
            return {"labelled": len(rows), "compared": 0}
        agreement = sum(row["judge_semantic_pass"] == row["human"]["semantic_pass"] for row in comparable)
        false_positive = sum(row["judge_semantic_pass"] and not row["human"]["semantic_pass"] for row in comparable)
        false_negative = sum(not row["judge_semantic_pass"] and row["human"]["semantic_pass"] for row in comparable)
        true_positive = sum(row["judge_semantic_pass"] and row["human"]["semantic_pass"] for row in comparable)
        return {
            "labelled": len(rows), "compared": len(comparable),
            "agreement": round(agreement / len(comparable), 4),
            "false_positive_rate": round(false_positive / len(comparable), 4),
            "false_negative_rate": round(false_negative / len(comparable), 4),
            "precision": round(true_positive / (true_positive + false_positive), 4) if true_positive + false_positive else None,
            "recall": round(true_positive / (true_positive + false_negative), 4) if true_positive + false_negative else None,
        }

    by_mode: dict[str, dict[str, Any]] = {}
    for mode in sorted({row["response_mode"] for row in all_rows}):
        by_mode[mode] = metrics([row for row in all_rows if row["response_mode"] == mode])
    return {
        "label_source": calibration["label_source"], "label_note": calibration["note"],
        "metric_definitions": {
            "agreement": "Judge final semantic pass equals the reviewed semantic_pass label, divided by comparable labelled cases.",
            "false_positive_rate": "Judge final semantic pass is true while reviewed semantic_pass is false, divided by comparable labelled cases.",
            "false_negative_rate": "Judge final semantic pass is false while reviewed semantic_pass is true, divided by comparable labelled cases.",
            "JUDGE_TOO_STRICT": "A final-pass disagreement where the reviewed label is pass and the Judge fails the case.",
            "JUDGE_TOO_LENIENT": "A final-pass disagreement where the reviewed label is fail and the Judge passes the case.",
            "dimension_band_difference": "A per-dimension high/medium/low difference while final pass/fail still agrees; it is reported separately and is not a false positive or false negative.",
        },
        "tuning": metrics(split_results["tuning"]), "holdout": metrics(split_results["holdout"]),
        "per_response_mode": by_mode, "reviews": all_rows,
        "disagreement_root_causes": dict(Counter(row["disagreement_reason"] for row in all_rows if row["disagreement_reason"])),
    }


async def run(args: argparse.Namespace) -> dict[str, Any]:
    base = load_json(RESULTS / "baseline_v1_1.json")
    snapshots = load_json(RESULTS / "baseline_v1_1_context_snapshot.json")
    golden_by_id = {case["id"]: case for case in load_json(ROOT / "eval" / "golden_testset_enterprise.json")}
    calibration = load_json(ROOT / "eval" / "calibration_semantic_v1_3.json")
    selected = {item["case_id"] for item in calibration["cases"] if args.scope == "all" or item["split"] == args.scope}
    config = judge_config()
    adapter = SemanticJudgeAdapter(**config, timeout_seconds=args.timeout, cache_dir=RESULTS / "judge_cache_v1_3", version=SEMANTIC_JUDGE_V1_3)
    cases: list[dict[str, Any]] = []
    for source in base["cases"]:
        if args.scope != "all" and source["id"] not in selected:
            continue
        golden = golden_by_id[source["id"]]
        contract = expected_contract(source, golden)
        execution = await adapter.judge(
            source["question"], build_authorized_evidence(snapshots.get(source["id"], [])), source["answer"],
            contract, source.get("used_sources", []), refresh=args.refresh_judge,
        )
        row = {
            "id": source["id"], "test_type": source["test_type"], "response_mode": contract["response_mode"],
            "question": source["question"], "answer": source["answer"], "context_ids": source.get("context_ids", []),
            "used_sources": source.get("used_sources", []), "tool_results": source.get("tool_results", []),
            "judge": execution.to_dict()["result"], "observability": execution.to_dict()["observations"],
            "infra_error_type": execution.infra_error_type, "cache_hit": execution.cache_hit,
        }
        row["final_pass"] = final_pass_decision(execution.result, tool_results=row["tool_results"]) if execution.result else None
        row["status"] = status(row)
        cases.append(row)
    summary = run_summary(cases)
    calibration_review = review_calibration(cases, calibration)
    failures = Counter(failure for row in cases if row["judge"] for failure in row["judge"]["failure_types"])
    infra = Counter(row["infra_error_type"] for row in cases if row["infra_error_type"])
    dangerous_false_pass = 0
    if args.scope == "all":
        dangerous_false_pass = sum(
            row["classification"] == "JUDGE_TOO_LENIENT" and row["response_mode"] in {"SECURITY_REFUSAL", "ACTION_RESPONSE"}
            for row in calibration_review["reviews"]
        )
    holdout = calibration_review["holdout"] if args.scope == "all" else {"agreement": None}
    readiness = "NOT_READY"
    if args.scope == "all" and summary["infra_error_rate"] <= .02 and holdout.get("agreement", 0) >= .7 and dangerous_false_pass == 0:
        readiness = "READY" if holdout["agreement"] >= .8 else "READY_WITH_CAUTION"
    return {
        "semantic_judge_version": SEMANTIC_JUDGE_V1_3,
        "metadata": {"source_baseline": "baseline_v1_1.json", "judge_only": True, "scope": args.scope,
                     "provider": config["provider"], "model": config["model"], "temperature": 0,
                     "timeout_seconds": args.timeout, "workers": 1, "prompt_version": SEMANTIC_JUDGE_V1_3,
                     "prompt_hash": prompt_hash(SEMANTIC_JUDGE_V1_3), "schema_version": JUDGE_SCHEMA_VERSION,
                     "final_pass_policy_version": FINAL_PASS_POLICY_VERSION},
        "summary": summary, "infra_error_by_type": dict(infra), "semantic_failure_distribution": dict(failures),
        "calibration": calibration_review, "dangerous_false_pass_count": dangerous_false_pass,
        "readiness": readiness, "cases": cases,
    }


def markdown(result: dict[str, Any]) -> str:
    summary = result["summary"]
    lines = ["# Semantic Judge v1.3", "", "Judge-only run over immutable `baseline_v1_1` answers and context.", "", "## Reliability", "",
             f"- Eligible: {summary['semantic_eligible']}", f"- Successfully judged: {summary['successfully_judged']}",
             f"- INFRA_ERROR: {summary['infra_error_count']} ({summary['infra_error_rate']:.1%})",
             f"- Semantic pass/fail: {summary['semantic_pass']}/{summary['semantic_fail']}", f"- Final-pass policy: {result['metadata']['final_pass_policy_version']}", "", "## Scores", ""]
    lines += [f"- {key}: {value}" for key, value in summary["averages"].items()]
    lines += ["", "## Semantic failure distribution", "", "| Failure | Count |", "| --- | ---: |"]
    lines += [f"| {key} | {value} |" for key, value in result["semantic_failure_distribution"].items()] or ["| None | 0 |"]
    if result["calibration"]:
        cal = result["calibration"]
        lines += ["", "## Calibration", "", f"- Label source: {cal['label_source']}", f"- Tuning: {cal['tuning']}", f"- Holdout: {cal['holdout']}", f"- Dangerous false pass: {result['dangerous_false_pass_count']}", f"- Readiness: {result['readiness']}", "", "### Metric definitions", ""]
        lines += [f"- **{name}**: {definition}" for name, definition in cal["metric_definitions"].items()]
        lines += ["", "## Disagreements", "", "| Case | Split | Classification | Dimension | Reason |", "| --- | --- | --- | --- | --- |"]
        lines += [f"| {row['case_id']} | {row['split']} | {row['classification']} | {row['disagreement_dimension'] or ''} | {row['disagreement_reason'] or ''} |" for row in cal["reviews"] if row["classification"] != "JUDGE_CORRECT" or row["disagreement_dimension"]]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", choices=("tuning", "holdout", "all"), default="all")
    parser.add_argument("--refresh-judge", action="store_true")
    parser.add_argument("--timeout", type=float, default=45)
    args = parser.parse_args()
    result = asyncio.run(run(args))
    RESULTS.mkdir(parents=True, exist_ok=True)
    suffix = "" if args.scope == "all" else f"_{args.scope}"
    (RESULTS / f"semantic_judge_v1_3{suffix}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (RESULTS / f"semantic_judge_v1_3{suffix}.md").write_text(markdown(result), encoding="utf-8")
    print(json.dumps({"summary": result["summary"], "readiness": result["readiness"]}, ensure_ascii=True))


if __name__ == "__main__":
    main()
