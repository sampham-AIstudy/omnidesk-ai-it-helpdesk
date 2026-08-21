"""Behavioral Regression Contract validator and test harness."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

MANIFEST_PATH = Path(__file__).resolve().parent / "chat_behavior_manifest.json"


@dataclass(frozen=True)
class BehaviorCaseExpected:
    blocked: bool
    refusal_category: str | None = None
    route: str | None = None
    should_retrieve: bool | None = None
    mutation_count: int = 0
    action_execution_state: str = "NOT_INVOKED"
    requires_clarification: bool = False
    requires_confirmation: bool = False
    expected_intent_keys: list[str] | None = None
    must_include_semantics: list[str] | None = None
    must_not_include_semantics: list[str] | None = None


@dataclass(frozen=True)
class BehaviorCase:
    id: str
    domain: str
    title: str
    input: str
    paired_case_id: str | None
    severity: str
    expected: BehaviorCaseExpected

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BehaviorCase:
        exp = data["expected"]
        expected_obj = BehaviorCaseExpected(
            blocked=exp.get("blocked", False),
            refusal_category=exp.get("refusal_category"),
            route=exp.get("route"),
            should_retrieve=exp.get("should_retrieve"),
            mutation_count=exp.get("mutation_count", 0),
            action_execution_state=exp.get("action_execution_state", "NOT_INVOKED"),
            requires_clarification=exp.get("requires_clarification", False),
            requires_confirmation=exp.get("requires_confirmation", False),
            expected_intent_keys=exp.get("expected_intent_keys"),
            must_include_semantics=exp.get("must_include_semantics"),
            must_not_include_semantics=exp.get("must_not_include_semantics"),
        )
        return cls(
            id=data["id"],
            domain=data["domain"],
            title=data["title"],
            input=data["input"],
            paired_case_id=data.get("paired_case_id"),
            severity=data.get("severity", "high"),
            expected=expected_obj,
        )


def load_behavior_manifest() -> list[BehaviorCase]:
    """Load and parse the behavioral regression manifest."""
    raw = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return [BehaviorCase.from_dict(c) for c in raw["cases"]]


def validate_manifest_integrity() -> list[str]:
    """Check manifest integrity: unique IDs, valid paired links, and complete schemas."""
    errors: list[str] = []
    cases = load_behavior_manifest()
    case_map = {c.id: c for c in cases}

    if len(cases) != len(case_map):
        errors.append(f"Duplicate IDs detected in manifest: {len(cases)} total vs {len(case_map)} unique")

    for case in cases:
        if case.paired_case_id:
            paired = case_map.get(case.paired_case_id)
            if not paired:
                errors.append(f"Case {case.id} references missing paired_case_id '{case.paired_case_id}'")
            elif paired.paired_case_id != case.id:
                errors.append(f"Pairing asymmetry: {case.id} -> {case.paired_case_id}, but {paired.id} -> {paired.paired_case_id}")

            # Ensure paired cases differ in blocked status (one positive, one negative)
            if paired and paired.expected.blocked == case.expected.blocked:
                errors.append(f"Paired cases {case.id} and {paired.id} both have blocked={case.expected.blocked}")

    return errors


def parse_sse_events(raw_sse: str) -> list[dict[str, Any]]:
    """Parse raw Server-Sent Events stream into a list of JSON payloads."""
    events: list[dict[str, Any]] = []
    lines = raw_sse.splitlines()
    event_type = "message"
    for line in lines:
        if line.startswith("event:"):
            event_type = line[len("event:"):].strip()
        elif line.startswith("data:"):
            data_str = line[len("data:"):].strip()
            try:
                payload = json.loads(data_str)
                events.append({"event": event_type, "data": payload})
            except Exception:
                events.append({"event": event_type, "raw_data": data_str})
    return events
