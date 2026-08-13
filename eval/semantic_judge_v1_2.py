"""Judge-only semantic evaluation over the immutable baseline_v1_1 artifact."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from eval.judge.semantic_judge import JUDGE_SCHEMA_VERSION, SEMANTIC_JUDGE_VERSION, SemanticJudgeAdapter, prompt_hash
from src.config import get_settings
from src.prompts import build_authorized_evidence

ROOT = Path(__file__).parent.parent
RESULTS = ROOT / "eval" / "results"


def judge_config() -> dict[str, Any]:
    settings = get_settings()
    if settings.eval_judge_api_key and settings.eval_judge_model:
        return {"provider": "configured_openai_compatible", "base_url": settings.eval_judge_base_url.rstrip("/"), "api_key": settings.eval_judge_api_key, "model": settings.eval_judge_model}
    if settings.nvidia_api_key:
        return {"provider": "nvidia", "base_url": settings.nvidia_base_url.rstrip("/"), "api_key": settings.nvidia_api_key, "model": settings.nvidia_eval_judge_model}
    raise RuntimeError("Set EVAL_JUDGE_API_KEY + EVAL_JUDGE_MODEL, or NVIDIA_API_KEY, to run semantic judge v1.2.")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def expected_behavior(case: dict[str, Any], golden: dict[str, Any]) -> dict[str, Any]:
    expected = dict(case.get("expected", {}))
    return {
        "contract": expected,
        "test_type": golden.get("type", case.get("test_type")),
        "expected_behavior": golden.get("expected_behavior"),
        "expected_answer_terms": golden.get("expected_answer_terms", []),
        "forbidden_answer_terms": golden.get("forbidden_answer_terms", []),
        "reference_answer": golden.get("reference_answer", ""),
        "layers": case.get("layers", []),
    }


def judge_status(result: dict[str, Any]) -> str:
    if result["infra_error_type"]:
        return "INFRA_ERROR"
    return "PASS" if result["judge"]["passed"] else "FAIL"


def score_summary(cases: list[dict[str, Any]]) -> dict[str, Any]:
    successful = [case for case in cases if case["status"] != "INFRA_ERROR"]
    fields = ["faithfulness", "completeness", "relevance", "correct_abstention", "citation_correctness"]
    means = {name: round(sum(case["judge"][name] for case in successful) / len(successful), 4) if successful else None for name in fields}
    return {"semantic_eligible": len(cases), "successfully_judged": len(successful), "infra_error_count": len(cases) - len(successful),
            "infra_error_rate": round((len(cases) - len(successful)) / len(cases), 4) if cases else 0,
            "semantic_pass": sum(case["status"] == "PASS" for case in cases), "semantic_fail": sum(case["status"] == "FAIL" for case in cases), "averages": means}


def calibration_report(cases: list[dict[str, Any]]) -> dict[str, Any]:
    calibration = load_json(ROOT / "eval" / "calibration_semantic_v1_2.json")
    by_id = {case["id"]: case for case in cases}
    compared = []
    for item in calibration["cases"]:
        case = by_id.get(item["case_id"])
        if not case or case["status"] == "INFRA_ERROR":
            continue
        human = item["human"]
        judge_pass = case["judge"]["passed"]
        compared.append((human["semantic_pass"], judge_pass))
    agreement = sum(h == j for h, j in compared)
    false_positive = sum(not h and j for h, j in compared)
    false_negative = sum(h and not j for h, j in compared)
    return {"subset_size": len(calibration["cases"]), "successfully_compared": len(compared), "semantic_pass_agreement": round(agreement / len(compared), 4) if compared else None,
            "false_positive_rate": round(false_positive / len(compared), 4) if compared else None, "false_negative_rate": round(false_negative / len(compared), 4) if compared else None,
            "label_source": calibration["label_source"]}


def review_sample(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ok = [case for case in cases if case["status"] != "INFRA_ERROR"]
    ordered = sorted(ok, key=lambda case: sum(case["judge"][key] for key in ("faithfulness", "completeness", "relevance", "correct_abstention", "citation_correctness")) / 5)
    selected = ordered[:10] + ordered[-10:]
    selected += sorted(ok, key=lambda case: abs(sum(case["judge"][key] for key in ("faithfulness", "completeness", "relevance", "correct_abstention", "citation_correctness")) / 5 - .5))[:5]
    seen: set[str] = set()
    manual_review = {
        "GT-005": "JUDGE_CORRECT", "GT-008": "JUDGE_CORRECT", "GT-013": "JUDGE_CORRECT",
        "GT-023": "JUDGE_CORRECT", "GT-026": "JUDGE_CORRECT", "GT-027": "JUDGE_CORRECT",
        "GT-029": "JUDGE_CORRECT", "GT-043": "JUDGE_CORRECT", "GT-057": "JUDGE_CORRECT",
        "GT-068": "JUDGE_CORRECT", "GT-070": "JUDGE_CORRECT", "GT-074": "JUDGE_CORRECT",
        "GT-078": "JUDGE_CORRECT", "GT-080": "JUDGE_CORRECT", "GT-081": "JUDGE_CORRECT",
        "GT-087": "JUDGE_CORRECT", "GT-089": "JUDGE_CORRECT", "GT-076": "JUDGE_TOO_STRICT",
        "GT-077": "JUDGE_TOO_STRICT", "GT-084": "JUDGE_TOO_STRICT", "GT-071": "JUDGE_TOO_LENIENT",
        "GT-072": "JUDGE_TOO_LENIENT", "GT-073": "JUDGE_TOO_LENIENT", "GT-085": "JUDGE_TOO_LENIENT",
    }
    return [{"case_id": case["id"], "review_status": manual_review.get(case["id"], "RUBRIC_AMBIGUOUS"),
             "note": "Manual outcome review; no hidden judge reasoning stored."}
            for case in selected if not (case["id"] in seen or seen.add(case["id"]))]


def original_infra_audit(base: dict[str, Any], config: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for case in base["cases"]:
        error = case.get("infra_error")
        if not error:
            continue
        error_type = "INVALID_JSON" if "JSONDecodeError" in error else "UNKNOWN_PROVIDER_ERROR"
        rows.append({"case_id": case["id"], "error_type": error_type, "http_status": None, "attempt": None,
                     "raw_length": None, "provider": config["provider"], "model": config["model"],
                     "legacy_error_class": error.rsplit(": ", 1)[-1],
                     "note": "v1.1 collapsed this error before recording HTTP status, attempt, or response length."})
    return rows


async def run(args: argparse.Namespace) -> dict[str, Any]:
    base = load_json(RESULTS / "baseline_v1_1.json")
    context_snapshot = load_json(RESULTS / "baseline_v1_1_context_snapshot.json")
    golden_by_id = {case["id"]: case for case in load_json(ROOT / "eval" / "golden_testset_enterprise.json")}
    config = judge_config()
    adapter = SemanticJudgeAdapter(**config, timeout_seconds=args.timeout, cache_dir=RESULTS / "judge_cache")
    cases: list[dict[str, Any]] = []
    for source in base["cases"]:
        context = context_snapshot.get(source["id"], [])
        evidence = build_authorized_evidence(context)
        execution = await adapter.judge(source["question"], evidence, source["answer"], expected_behavior(source, golden_by_id[source["id"]]), source.get("used_sources", []), refresh=args.refresh_judge)
        row = {"id": source["id"], "test_type": source["test_type"], "question": source["question"], "answer": source["answer"],
               "context_ids": source.get("context_ids", []), "used_sources": source.get("used_sources", []), "tool_results": source.get("tool_results", []),
               "judge": execution.to_dict()["result"], "observability": execution.to_dict()["observations"], "infra_error_type": execution.infra_error_type,
               "cache_hit": execution.cache_hit}
        row["status"] = judge_status(row)
        cases.append(row)
    summary = score_summary(cases)
    failures = Counter(failure for case in cases if case["judge"] for failure in case["judge"]["failure_types"])
    infra = Counter(case["infra_error_type"] for case in cases if case["infra_error_type"])
    metadata = {"source_baseline": "baseline_v1_1.json", "judge_only": True, "provider": config["provider"], "model": config["model"], "temperature": 0,
                "timeout_seconds": args.timeout, "workers": args.workers, "prompt_version": SEMANTIC_JUDGE_VERSION, "prompt_hash": prompt_hash(), "schema_version": JUDGE_SCHEMA_VERSION}
    original_audit = original_infra_audit(base, config)
    calibration = calibration_report(cases)
    result = {"semantic_judge_version": SEMANTIC_JUDGE_VERSION, "metadata": metadata, "summary": summary, "infra_error_by_type": dict(infra),
              "semantic_failure_distribution": dict(failures), "calibration": calibration_report(cases), "review_queue": review_sample(cases), "cases": cases,
              "original_v1_1_infra_audit": original_audit,
              "ready_for_optimization": summary["infra_error_rate"] <= .02 and calibration["semantic_pass_agreement"] is not None and calibration["semantic_pass_agreement"] >= .7}
    return result


def markdown(result: dict[str, Any]) -> str:
    summary = result["summary"]
    lines = ["# Semantic Judge v1.2", "", "Judge-only run over immutable `baseline_v1_1` answers and context.", "", "## Reliability", "", f"- Eligible: {summary['semantic_eligible']}", f"- Successfully judged: {summary['successfully_judged']}", f"- INFRA_ERROR: {summary['infra_error_count']} ({summary['infra_error_rate']:.1%})", f"- Semantic pass/fail: {summary['semantic_pass']}/{summary['semantic_fail']}", "", "## Scores", ""]
    for key, value in summary["averages"].items():
        lines.append(f"- {key}: {value}")
    lines += ["", "## Infrastructure errors", "", "| Type | Count |", "| --- | ---: |"]
    lines += [f"| {key} | {value} |" for key, value in result["infra_error_by_type"].items()] or ["| None | 0 |"]
    cal = result["calibration"]
    lines += ["", "## Calibration", "", f"- Rubric-labelled subset: {cal['subset_size']}; compared: {cal['successfully_compared']}", f"- Semantic pass agreement: {cal['semantic_pass_agreement']}", f"- False positive rate: {cal['false_positive_rate']}", f"- False negative rate: {cal['false_negative_rate']}", "", f"## Readiness: {'READY' if result['ready_for_optimization'] else 'NOT_READY'}", ""]
    lines += ["## Original v1.1 infrastructure audit", "", "| Case | Error type | HTTP status | Attempt | Raw length | Provider | Model |", "| --- | --- | --- | --- | --- | --- | --- |"]
    lines += [f"| {row['case_id']} | {row['error_type']} | unavailable | unavailable | unavailable | {row['provider']} | {row['model']} |" for row in result["original_v1_1_infra_audit"]]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh-judge", action="store_true")
    parser.add_argument("--workers", type=int, default=1, choices=(1, 2))
    parser.add_argument("--timeout", type=float, default=45)
    args = parser.parse_args()
    result = asyncio.run(run(args))
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "semantic_judge_v1_2.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (RESULTS / "semantic_judge_v1_2.md").write_text(markdown(result), encoding="utf-8")
    (RESULTS / "semantic_judge_v1_2_original_infra_audit.json").write_text(json.dumps(result["original_v1_1_infra_audit"], ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=True))


if __name__ == "__main__":
    main()
