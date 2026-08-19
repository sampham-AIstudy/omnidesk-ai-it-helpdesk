"""Pre-deployment and release verification script for Help Desk AI Agent Behavior Gate."""
from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import pytest  # noqa: E402

from eval.behavior.behavior_validator import load_behavior_manifest, validate_manifest_integrity  # noqa: E402
from src.version import get_build_info  # noqa: E402


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print("=" * 70)
    print("[BEHAVIOR GATE] VinAI Help Desk AI Agent - Chat Behavior Regression Gate")
    print("=" * 70)

    # 1. Build Info
    build = get_build_info()
    print(f"App Version:         {build['app_version']}")
    print(f"Guardrails Version:  {build['guardrails_version']}")
    print(f"Contract Version:    {build['behavior_contract_version']}")
    print(f"Git Commit:          {build['git_commit']}")
    print(f"Manifest SHA Digest: {build['manifest_hash']}")
    print(f"Environment:         {build['app_env']}")
    print("-" * 70)

    # 2. Manifest Validation
    print("Validating Chat Behavior Manifest integrity...")
    cases = load_behavior_manifest()
    errors = validate_manifest_integrity()
    if errors:
        print("[FAIL] Manifest integrity validation FAILED:")
        for err in errors:
            print(f"   - {err}")
        return 1

    print(f"[OK] Manifest integrity valid ({len(cases)} behavior cases loaded across positive/negative pairs)")
    print("-" * 70)

    # 3. Pytest Behavior Gate Execution (Single-turn & Critical Multi-turn)
    print("Running full behavioral regression gate suite (single-turn + multi-turn flows)...")
    pytest_args = [
        str(PROJECT_ROOT / "tests" / "test_behavior_gate.py"),
        str(PROJECT_ROOT / "tests" / "test_critical_multiturn.py"),
        str(PROJECT_ROOT / "tests" / "test_api" / "test_chat_new_conversation_flow.py"),
        "-v",
        "--tb=short",
    ]
    exit_code = pytest.main(pytest_args)

    print("-" * 70)
    if exit_code == 0:
        print("[PASS] ALL BEHAVIORAL REGRESSION GATE & MULTI-TURN CHECKS PASSED.")
    else:
        print(f"[FAIL] BEHAVIORAL REGRESSION GATE FAILED (exit code: {exit_code}).")
    print("=" * 70)
    return int(exit_code)


if __name__ == "__main__":
    sys.exit(main())
