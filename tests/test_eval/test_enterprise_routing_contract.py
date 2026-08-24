"""21 independently reported deterministic routing regression cases."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.services.chat_routing_service import route_chat_message

GOLDEN_PATH = Path(__file__).resolve().parents[2] / "eval" / "golden_testset_enterprise.json"
ROUTING_CASE_IDS = tuple(
    [f"GT-{number:03d}" for number in range(1, 20)] + ["GT-040", "GT-055"]
)


@pytest.fixture(scope="module")
def golden_cases() -> dict[str, dict]:
    cases = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    return {case["id"]: case for case in cases}


@pytest.mark.parametrize("case_id", ROUTING_CASE_IDS, ids=ROUTING_CASE_IDS)
def test_enterprise_golden_routing_contract(
    golden_cases: dict[str, dict], case_id: str,
) -> None:
    """The dataset is the single contract for every gate checked here."""
    case = golden_cases[case_id]
    decision = route_chat_message(case["query"])

    assert decision.route == case["expected_route"]
    assert decision.retrieval_required is case["should_retrieve"]
    assert decision.should_use_memory is case["should_use_memory"]
    assert decision.should_search_web is case["should_search_web"]
    assert decision.should_invoke_tool is (case["expected_route"] in {"ticket_status", "action_request"})


def test_routing_contract_has_exactly_twenty_one_independent_cases(
    golden_cases: dict[str, dict],
) -> None:
    assert len(ROUTING_CASE_IDS) == 21
    assert set(ROUTING_CASE_IDS) <= set(golden_cases)
    assert all("expected_route" in golden_cases[case_id] for case_id in ROUTING_CASE_IDS)
