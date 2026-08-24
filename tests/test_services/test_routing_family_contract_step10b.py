"""Family-level deterministic regressions for the enterprise routing contract."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.services.chat_routing_service import route_chat_message

GOLDEN_PATH = Path(__file__).resolve().parents[2] / "eval" / "golden_testset_enterprise.json"
SOCIAL_IDS = tuple(
    [f"GT-{number:03d}" for number in range(91, 105)]
    + ["GT-287", "GT-288", "GT-290", "GT-292", "GT-293", "GT-294", "GT-295", "GT-297", "GT-298", "GT-300"]
)
GARBAGE_IDS = tuple(f"GT-{number:03d}" for number in (105, 106, 107, 108, 110, 112, 113, 115, 116, 117, 118))
AMBIGUOUS_INCIDENT_IDS = tuple(f"GT-{number:03d}" for number in range(273, 287))


@pytest.fixture(scope="module")
def golden_cases() -> dict[str, dict]:
    return {case["id"]: case for case in json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))}


@pytest.mark.parametrize(
    "case_id",
    SOCIAL_IDS + GARBAGE_IDS + AMBIGUOUS_INCIDENT_IDS,
)
def test_step10b_enterprise_routing_regressions(golden_cases: dict[str, dict], case_id: str) -> None:
    """All previously failing route-contract cases must retain their dataset contract."""
    case = golden_cases[case_id]
    decision = route_chat_message(case["query"])

    assert decision.route == case["expected_route"]
    assert decision.retrieval_required is False
    assert decision.should_use_memory is False
    assert decision.should_search_web is False


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
