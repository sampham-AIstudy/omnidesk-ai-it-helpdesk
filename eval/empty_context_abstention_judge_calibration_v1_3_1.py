"""Calibrate Judge v1.3.1 only for empty-context precise abstention."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from eval.evaluation_contract import load_lock, validate_lock
from eval.judge.semantic_judge import (
    SEMANTIC_JUDGE_V1_3,
    SEMANTIC_JUDGE_V1_3_1,
    SemanticJudgeAdapter,
    final_pass_decision,
    prompt_hash,
)
from eval.precise_abstention_canary import render_candidate_precise_abstention
from eval.semantic_judge_v1_2 import judge_config
from eval.semantic_judge_v1_3 import expected_contract
from src.prompts import build_authorized_evidence

ROOT = Path(__file__).parent.parent
RESULTS = ROOT / "eval" / "results"
LOCK_PATH = ROOT / "eval" / "snapshots" / "evaluation_lock_v1_2_full.json"
CONTROL_PATH = RESULTS / "baseline_control_context_v1_2.json"
CALIBRATION_PATH = ROOT / "eval" / "calibration_empty_context_abstention_v1_3_1.json"
OUTPUT_PATH = RESULTS / "empty_context_abstention_judge_calibration_v1_3_1.json"
TARGET_IDS = ("GT-046", "GT-077", "GT-087")
CONTROL_IDS = ("GT-027", "GT-047", "GT-048")
KNOWN_FAILURE_IDS = ("GT-080", "GT-086")
KNOWN_SECURITY_IDS = ("GT-058",)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def outcome(execution: Any) -> dict[str, Any]:
    if execution.infra_error_type:
        return {"status": "INFRA_ERROR", "result": None, "infra_error_type": execution.infra_error_type}
    assert execution.result is not None
    final = final_pass_decision(execution.result)
    return {
        "status": "PASS" if final["passed"] else "FAIL",
        "result": execution.to_dict()["result"],
        "infra_error_type": None,
    }


async def judge_one(adapter: SemanticJudgeAdapter, case: dict[str, Any]) -> dict[str, Any]:
    execution = await adapter.judge(
        case["question"], case["context"], case["answer"], case["expected"], case.get("citations", []), refresh=False,
    )
    return outcome(execution)


def agreement(rows: list[dict[str, Any]], version: str) -> dict[str, Any]:
    completed = [row for row in rows if row["results"][version]["status"] != "INFRA_ERROR"]
    if not completed:
        return {"evaluated": 0}
    semantic = [(row["results"][version]["status"] == "PASS") == row["human"]["semantic_pass"] for row in completed]
    hallucination = [
        (("HALLUCINATION" in row["results"][version]["result"]["failure_types"]) == row["human"]["hallucination"])
        for row in completed
    ]
    abstention = [
        ((row["results"][version]["result"]["correct_abstention"] == 1.0) == row["human"]["correct_abstention"])
        for row in completed
    ]
    false_positive = sum(row["results"][version]["status"] == "PASS" and not row["human"]["semantic_pass"] for row in completed)
    false_negative = sum(row["results"][version]["status"] != "PASS" and row["human"]["semantic_pass"] for row in completed)
    return {
        "evaluated": len(completed),
        "semantic_pass_agreement": round(sum(semantic) / len(completed), 4),
        "hallucination_agreement": round(sum(hallucination) / len(completed), 4),
        "correct_abstention_agreement": round(sum(abstention) / len(completed), 4),
        "semantic_false_positive": false_positive,
        "semantic_false_negative": false_negative,
    }


def candidate_span_review(question: str, answer: str, result: dict[str, Any]) -> dict[str, Any]:
    result_data = result.get("result") or {}
    hallucination = "HALLUCINATION" in result_data.get("failure_types", [])
    return {
        "alleged_hallucinated_span": answer if hallucination else None,
        "judge_identified_concrete_span": result_data.get("unsupported_claims", []),
        "span_sources": [
            {"span": "Tài liệu hiện có không xác nhận thông tin về", "source": "ASSISTANT_INVENTED", "is_material_claim": False},
            {"span": question.rstrip("?.! "), "source": "USER_QUERY", "is_material_claim": False},
        ] if hallucination else [],
        "classification": "JUDGE_FALSE_HALLUCINATION" if hallucination and not result_data.get("unsupported_claims") else "NO_FALSE_HALLUCINATION_DETECTED",
    }


async def run() -> dict[str, Any]:
    lock = load_lock(LOCK_PATH)
    if errors := validate_lock(ROOT, lock):
        raise RuntimeError("Evaluation lock mismatch: " + ", ".join(errors))
    calibration = load_json(CALIBRATION_PATH)
    adapters = {
        version: SemanticJudgeAdapter(
            **judge_config(), timeout_seconds=45,
            cache_dir=RESULTS / f"judge_cache_empty_context_calibration_v{version.replace('.', '_')}",
            version=version,
        )
        for version in (SEMANTIC_JUDGE_V1_3, SEMANTIC_JUDGE_V1_3_1)
    }
    rows: list[dict[str, Any]] = []
    for item in calibration["cases"]:
        row = {**item, "results": {}}
        for version, adapter in adapters.items():
            row["results"][version] = await judge_one(adapter, item)
        rows.append(row)

    control = {row["id"]: row for row in load_json(CONTROL_PATH)["cases"]}
    golden = {row["id"]: row for row in load_json(ROOT / lock["golden"]["path"])}
    contexts = load_json(ROOT / lock["context_snapshot"]["path"])
    targeted: list[dict[str, Any]] = []
    for case_id in TARGET_IDS + CONTROL_IDS + KNOWN_FAILURE_IDS + KNOWN_SECURITY_IDS:
        saved = control[case_id]
        candidate = case_id in TARGET_IDS
        answer = render_candidate_precise_abstention(saved["question"]) if candidate else saved["answer"]
        case = {
            "id": case_id,
            "question": saved["question"],
            "context": build_authorized_evidence(contexts[case_id]),
            "answer": answer,
            "expected": expected_contract(saved, golden[case_id]),
            "citations": [] if candidate else saved.get("used_sources", []),
        }
        versioned = {version: await judge_one(adapter, case) for version, adapter in adapters.items()}
        targeted.append({
            "id": case_id,
            "group": "precise_abstention_target" if candidate else "known_control_or_failure",
            "answer": answer,
            "results": versioned,
            "span_review": candidate_span_review(saved["question"], answer, versioned[SEMANTIC_JUDGE_V1_3]),
            "taxonomy_inconsistency_v1_3": bool(
                "HALLUCINATION" in (versioned[SEMANTIC_JUDGE_V1_3].get("result") or {}).get("failure_types", [])
                and not (versioned[SEMANTIC_JUDGE_V1_3].get("result") or {}).get("unsupported_claims")
            ),
        })

    v131_targets = [row for row in targeted if row["group"] == "precise_abstention_target"]
    known_failures = [row for row in targeted if row["id"] in KNOWN_FAILURE_IDS]
    dangerous_false_passes = [
        row["id"] for row in targeted if row["id"] in KNOWN_FAILURE_IDS
        and row["results"][SEMANTIC_JUDGE_V1_3_1]["status"] == "PASS"
    ]
    accepted = (
        all(row["results"][SEMANTIC_JUDGE_V1_3_1]["status"] == "PASS" for row in v131_targets)
        and all(row["results"][SEMANTIC_JUDGE_V1_3_1]["status"] == "FAIL" for row in known_failures)
        and not dangerous_false_passes
    )
    return {
        "analysis": "empty_context_correct_abstention_judge_calibration_v1_3_1",
        "metadata": {
            "evaluation_contract": lock["evaluation_contract_version"],
            "golden_hash": lock["golden"]["sha256"],
            "context_hash": lock["context_snapshot"]["sha256"],
            "production_changes": False,
            "generator_calls": 0,
            "calibration_set_size": len(rows),
            "judge_versions": {
                SEMANTIC_JUDGE_V1_3: {"prompt_hash": prompt_hash(SEMANTIC_JUDGE_V1_3)},
                SEMANTIC_JUDGE_V1_3_1: {"prompt_hash": prompt_hash(SEMANTIC_JUDGE_V1_3_1)},
            },
        },
        "calibration_cases": rows,
        "calibration_agreement": {version: agreement(rows, version) for version in adapters},
        "targeted_regression": targeted,
        "taxonomy_inconsistencies_v1_3": [row["id"] for row in targeted if row["taxonomy_inconsistency_v1_3"]],
        "dangerous_false_passes_v1_3_1": dangerous_false_passes,
        "decision": "ACCEPT_JUDGE_V1_3_1" if accepted else "KEEP_JUDGE_V1_3",
        "should_rerun_precise_abstention_canary": accepted,
    }


def markdown(result: dict[str, Any]) -> str:
    lines = ["# Empty-Context Abstention Judge Calibration", "", f"- Decision: **{result['decision']}**", f"- Calibration examples: {result['metadata']['calibration_set_size']}", "- Production changes: none.", "", "## Calibration agreement", "", "| Version | Semantic agreement | Hallucination agreement | Abstention agreement | FP | FN |", "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for version, metrics in result["calibration_agreement"].items():
        lines.append(f"| {version} | {metrics.get('semantic_pass_agreement')} | {metrics.get('hallucination_agreement')} | {metrics.get('correct_abstention_agreement')} | {metrics.get('semantic_false_positive')} | {metrics.get('semantic_false_negative')} |")
    lines += ["", "## Targeted regression", "", "| ID | v1.3 | v1.3.1 | v1.3 taxonomy inconsistency |", "| --- | --- | --- | --- |"]
    lines += [f"| {row['id']} | {row['results']['1.3']['status']} | {row['results']['1.3.1']['status']} | {row['taxonomy_inconsistency_v1_3']} |" for row in result["targeted_regression"]]
    lines += ["", f"Dangerous false passes v1.3.1: {result['dangerous_false_passes_v1_3_1']}"]
    return "\n".join(lines)


def main() -> None:
    result = asyncio.run(run())
    OUTPUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    OUTPUT_PATH.with_suffix(".md").write_text(markdown(result), encoding="utf-8")
    print(json.dumps({"decision": result["decision"], "agreement": result["calibration_agreement"], "dangerous_false_passes": result["dangerous_false_passes_v1_3_1"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
