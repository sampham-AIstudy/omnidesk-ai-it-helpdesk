"""Family-level deterministic regressions for the enterprise routing contract."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.services.chat_routing_service import route_chat_message

GOLDEN_PATH = Path(__file__).resolve().parents[2] / "eval" / "golden_testset_enterprise.json"
RUNTIME_ROUTE_FAMILIES = frozenset(
    {
        "direct_response",
        "needs_clarification",
        "ticket_status",
        "action_request",
        "incident",
        "knowledge",
    }
)


@pytest.fixture(scope="module")
def golden_cases() -> dict[str, dict]:
    return {case["id"]: case for case in json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))}


def test_step10b_enterprise_routing_regressions(golden_cases: dict[str, dict]) -> None:
    """Check only Golden rows that explicitly carry a runtime-route contract.

    ``expected_route`` also carries downstream orchestration outcomes for some
    generation cases (for example ``knowledge_query`` and guardrail outcomes).
    Those are not values returned by ``route_chat_message`` and therefore do
    not belong in this pre-retrieval routing-family regression.
    """
    runtime_cases = [
        case for case in golden_cases.values()
        if case.get("routing_contract") == "step10b_no_retrieval"
        and case.get("expected_route") in RUNTIME_ROUTE_FAMILIES
        and not case["should_retrieve"]
        and not case["should_use_memory"]
        and not case["should_search_web"]
    ]

    assert runtime_cases
    for case in runtime_cases:
        decision = route_chat_message(case["query"])

        assert decision.route == case["expected_route"], case["id"]
        assert decision.retrieval_required is False, case["id"]
        assert decision.should_use_memory is False, case["id"]
        assert decision.should_search_web is False, case["id"]


@pytest.mark.parametrize(
    "message",
    (
        "chào buổi sáng",
        "hello bạn",
        "cảm ơn nhé",
        "ok rồi",
        "ừ",
        "vâng",
        "thôi để sau",
        "bạn khỏe không",
        "bạn có thể nói chuyện một chút không",
    ),
)
def test_social_semantic_family_never_enters_retrieval(message: str) -> None:
    decision = route_chat_message(message)

    assert decision.route == "direct_response"
    assert decision.retrieval_required is False
    assert decision.should_use_memory is False


@pytest.mark.parametrize(
    "message",
    (
        "qwer asdf",
        "lorem test",
        "xin lỗi, tôi gửi nhầm",
        "### 123 ???",
        "không có nội dung gì",
    ),
)
def test_uninterpretable_family_never_enters_retrieval(message: str) -> None:
    decision = route_chat_message(message)

    assert decision.route == "needs_clarification"
    assert decision.retrieval_required is False
    assert decision.should_use_memory is False


@pytest.mark.parametrize(
    "message",
    (
        "máy có vấn đề",
        "mạng bị sao ấy",
        "ứng dụng không ổn",
        "tài khoản bị gì đó",
        "nó lỗi rồi",
    ),
)
def test_underspecified_incident_family_requires_clarification(message: str) -> None:
    decision = route_chat_message(message)

    assert decision.route == "needs_clarification"
    assert decision.retrieval_required is False
    assert decision.should_use_memory is False


@pytest.mark.parametrize("message", ("VPN lỗi", "BitLocker", "DNS lỗi", "WiFi mất mạng", "Outlook không mở được"))
def test_short_technical_signals_remain_eligible_for_normal_routing(message: str) -> None:
    decision = route_chat_message(message)

    assert decision.route != "needs_clarification"
    assert decision.retrieval_required is True
