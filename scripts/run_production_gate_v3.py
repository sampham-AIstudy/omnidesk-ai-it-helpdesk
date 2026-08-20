"""One release orchestrator for the locked v3 retrieval/behavior contract.

It owns sequencing and the final decision only.  Each underlying evaluator
remains the existing authoritative implementation.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
RESULT = ROOT / "eval" / "results" / "production_gate_v3.json"
ACTIVE = "helpdesk_kb_multilingual_v3_sentence_transformer"
ROLLBACK = "helpdesk_kb_multilingual_v2_sentence_transformer"


def _run(*args: str) -> dict[str, Any]:
    completed = subprocess.run([PYTHON, *args], cwd=ROOT, text=True, capture_output=True, check=False)
    return {"command": list(args), "returncode": completed.returncode, "stdout": completed.stdout[-12000:], "stderr": completed.stderr[-4000:]}


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _metric_ok(value: float, floor: float) -> bool:
    return float(value) >= floor


def main() -> int:
    enterprise = _run("eval/enterprise_runtime_v1_0.py")
    behavior = _run("scripts/run_behavior_gate.py")
    retrieval = _run("scripts/run_retrieval_gate.py")
    memory_context = _run("-m", "pytest", "-q", "tests/test_services/test_zero_mem_service.py", "tests/test_services/test_recent_conversation_context.py")
    pytest = _run("-m", "pytest", "-q")
    runtime = _read(ROOT / "eval" / "results" / "enterprise_runtime_v1_0.json")
    hard = _read(ROOT / "eval" / "results" / "adaptive_hard_negative_50_ab.json")
    p0 = _read(ROOT / "eval" / "results" / "adaptive_p0_11_ab.json")
    promotion = _read(ROOT / "eval" / "results" / "p0_v3_promotion.json")
    from src.services.rag_service import get_chroma_client

    client = get_chroma_client()
    active_count = client.get_collection(ACTIVE).count()
    rollback_count = client.get_collection(ROLLBACK).count()
    metrics = hard["v3"]["metrics"]["overall"]
    checks = {
        "active_collection": active_count == 443,
        "rollback_collection": rollback_count == 433,
        "enterprise_product_failure": runtime["status_counts"].get("PRODUCT_FAILURE", 0) == 0,
        "enterprise_fixture_incomplete": runtime["status_counts"].get("FIXTURE_INCOMPLETE", 0) == 0,
        "enterprise_conflicts_documented": all(row.get("contract_conflict") for row in runtime["case_requirement_mapping"] if row["overall_status"] == "CONTRACT_CONFLICT"),
        "p0_v3": p0["p0_candidate"]["v3"]["hit_rate_at_3"] == 1.0 and p0["p0_candidate"]["v3"]["hit_rate_at_5"] == 1.0,
        "hard_negative": _metric_ok(metrics["hit_rate_at_1"], 0.80) and _metric_ok(metrics["hit_rate_at_3"], 0.94) and _metric_ok(metrics["hit_rate_at_5"], 0.98) and float(metrics["hard_negative_at_1_rate"]) <= 0.04 and float(metrics["intent_confusion_rate"]) <= 0.04,
        "provenance": promotion["canonical_v3"]["name"] == ACTIVE and promotion["canonical_v3"]["chunk_count"] == 443,
        "enterprise": enterprise["returncode"] == 0,
        "behavior": behavior["returncode"] == 0,
        "retrieval": retrieval["returncode"] == 0,
        "memory_context": memory_context["returncode"] == 0,
        "pytest": pytest["returncode"] == 0,
    }
    result = {
        "gate": "production-gate-v3", "active_collection": {"name": ACTIVE, "count": active_count},
        "rollback_collection": {"name": ROLLBACK, "count": rollback_count}, "checks": checks,
        "contract_conflicts": [{"case_id": row["case_id"], "reason": row.get("contract_conflict")} for row in runtime["case_requirement_mapping"] if row["overall_status"] == "CONTRACT_CONFLICT"],
        "deferred_non_blockers": {
            "step_6": "PARTIAL / BLOCKED_BY_DATA: no proven multi-chunk hierarchical source; expansion fails closed.",
            "step_7": "PARTIAL / DEFERRED: bounded retry is safe, but no real WEAK-to-RECOVERED corpus evidence or proven pruning benefit.",
        },
        "commands": {"enterprise": enterprise, "behavior": behavior, "retrieval": retrieval, "memory_context": memory_context, "pytest": pytest},
        "status": "PASS" if all(checks.values()) else "FAIL",
    }
    RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": result["status"], "checks": checks, "contract_conflicts": result["contract_conflicts"]}, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
