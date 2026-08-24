from __future__ import annotations

import json
from pathlib import Path


def test_context_completeness_dataset_is_separate_and_complete():
    path = Path(__file__).resolve().parents[2] / "eval" / "context_completeness_v1.json"
    dataset = json.loads(path.read_text(encoding="utf-8"))

    assert len(dataset["cases"]) >= 7
    assert {"anchor_expected_source", "required_context_facts", "optional_context_facts", "forbidden_unrelated_context"} <= set(dataset["cases"][0])
    assert all(case["required_context_facts"] and case["forbidden_unrelated_context"] for case in dataset["cases"])
