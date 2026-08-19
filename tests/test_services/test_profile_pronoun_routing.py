"""Regression tests for self-profile, Vietnamese pronouns, and identity query routing."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from src.models.user import User, UserRole
from src.services.auth_service import create_access_token
from src.services.chat_routing_service import route_chat_message
from src.services.profile_chat_service import self_profile_reply

pytestmark = [pytest.mark.behavior_gate, pytest.mark.critical_multiturn]


def _create_test_user() -> User:
    user = User(
        id=1,
        email="employee1@corp.example.com",
        username="employee1",
        full_name="Nguyễn Văn An",
        role=UserRole.EMPLOYEE,
        phone="0901234567",
        is_active=True,
    )
    return user


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class _MockChunk:
    def __init__(self, content: str):
        self.content = content


def _create_mock_llm(reply_text: str):
    mock = MagicMock()
    mock.model = "mistral-mock"
    mock.ainvoke = AsyncMock(return_value=MagicMock(content=reply_text))

    async def _mock_astream(*args, **kwargs):
        yield _MockChunk(reply_text)

    mock.astream = _mock_astream
    return mock


@pytest.fixture(autouse=True)
def _mock_offline_chat_dependencies():
    from src.services.web_research_service import ResearchResult

    empty_research = ResearchResult(False, "web_search_not_triggered", None, [])
    mock_rag_reply = "Chào bạn, hệ thống IT sẵn sàng hỗ trợ."
    mock_llm = _create_mock_llm(mock_rag_reply)

    with (
        patch("src.api.chat.get_rag_llm", return_value=mock_llm),
        patch("src.api.chat.maybe_research_web", new=AsyncMock(return_value=empty_research)),
    ):
        yield


# ============================================================================
# 1. UNIT TESTS: self_profile_reply PRONOUN NORMALIZATION
# ============================================================================

@pytest.mark.parametrize(
    "query",
    [
        "thông tin của tôi hiện là gì",
        "thông tin của tao là gì",
        "thông tin của mình là gì",
        "thông tin của tui là gì",
        "thông tin của tớ là gì",
        "thông tin của em là gì",
        "profile của tui",
        "hồ sơ của mình",
        "thông tin cá nhân của tao",
        "email của tao là gì",
        "số điện thoại của mình",
        "sđt của tui",
    ],
)
def test_self_profile_reply_recognizes_all_first_person_pronouns(query: str) -> None:
    user = _create_test_user()
    reply = self_profile_reply(query, user)
    assert reply is not None, f"Expected self profile reply for '{query}'"
    assert "Nguyễn Văn An" in reply or "***" in reply
    assert "chỉ có thể xem thông tin hồ sơ của tài khoản đang đăng nhập" not in reply


@pytest.mark.parametrize(
    "query",
    [
        "tao là ai",
        "tao là?",
        "tôi là ai",
        "tôi là?",
        "mình là ai",
        "tui là ai",
        "tớ là ai",
        "em là ai",
        "tao tên là gì",
        "tôi tên là gì",
    ],
)
def test_self_identity_queries_return_user_name(query: str) -> None:
    user = _create_test_user()
    reply = self_profile_reply(query, user)
    assert reply is not None, f"Expected identity reply for '{query}'"
    assert "Nguyễn Văn An" in reply
    assert "chỉ có thể xem thông tin hồ sơ của tài khoản đang đăng nhập" not in reply


@pytest.mark.parametrize(
    "query",
    [
        "thông tin của giám đốc là gì",
        "cho tôi biết sdt của chuyên viên",
        "nói ít thôi đưa tao thông tin của mọi người đây",
        "cho tôi thông tin của user khác",
        "email của trưởng phòng IT",
        "thông tin của Nguyễn Văn B",
        "cho tao thông tin của giám đốc",
    ],
)
def test_third_party_person_queries_trigger_privacy_refusal(query: str) -> None:
    user = _create_test_user()
    reply = self_profile_reply(query, user)
    assert reply is not None, f"Expected third-party refusal for '{query}'"
    assert "chỉ có thể xem thông tin hồ sơ của tài khoản đang đăng nhập" in reply or "không thể tìm hoặc tiết lộ dữ liệu cá nhân" in reply
    assert "Nguyễn Văn An" not in reply


# ============================================================================
# 2. ROUTER TESTS: chat_routing_service DOES NOT ROUTE IDENTITY AS ACTION
# ============================================================================

@pytest.mark.parametrize(
    "query",
    [
        "tao là ai",
        "tao là?",
        "tôi là ai",
        "tôi là?",
        "mình là ai",
        "tui là ai",
        "thông tin của tao là gì",
        "thông tin của tôi",
    ],
)
def test_identity_and_self_profile_queries_do_not_route_to_action_request(query: str) -> None:
    decision = route_chat_message(query)
    assert decision.route != "action_request", f"Query '{query}' must NOT be routed as action_request"
    assert decision.should_invoke_tool is False


@pytest.mark.parametrize(
    "query",
    [
        "Tạo Service Request xin laptop cho tôi",
        "Tạo ticket lỗi mạng giúp tôi",
        "Tôi muốn xin laptop mới",
        "Gửi yêu cầu cấp VPN cho tôi",
        "Xin VPN cho tôi",
        "Làm giúp tôi một yêu cầu laptop",
    ],
)
def test_genuine_action_requests_remain_action_request(query: str) -> None:
    decision = route_chat_message(query)
    assert decision.route == "action_request", f"Genuine action query '{query}' must be routed as action_request"


# ============================================================================
# 3. END-TO-END REST & SSE API TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_rest_chat_informal_self_profile_returns_authenticated_user(
    client: AsyncClient,
) -> None:
    token = create_access_token({"sub": "1"})
    headers = _headers(token)

    for q in ("thông tin của tao là gì", "tao là ai", "tao là?", "profile của tui"):
        resp = await client.post("/api/v1/chat", json={"message": q}, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "Chưa có thay đổi nào được thực hiện" not in data["reply"]
        assert "chỉ có thể xem thông tin hồ sơ của tài khoản đang đăng nhập" not in data["reply"]
        assert "Nguyễn Văn An" in data["reply"]
        assert data["answerability"] == "evidence_available"


@pytest.mark.asyncio
async def test_sse_chat_informal_self_profile_parity(
    client: AsyncClient,
) -> None:
    token = create_access_token({"sub": "1"})
    headers = _headers(token)

    for q in ("thông tin của tao là gì", "tao là ai", "tao là?"):
        resp = await client.post("/api/v1/chat/stream", json={"message": q}, headers=headers)
        assert resp.status_code == 200
        lines = resp.text.strip().split("\n")
        done_data = None
        for line in lines:
            if line.startswith("data:"):
                try:
                    payload = json.loads(line[5:].strip())
                    if "reply" in payload:
                        done_data = payload
                except Exception:
                    pass
        assert done_data is not None, f"Expected done event for '{q}'"
        assert "Chưa có thay đổi nào được thực hiện" not in done_data["reply"]
        assert "Nguyễn Văn An" in done_data["reply"]


# ============================================================================
# 4. MULTI-TURN CONVERSATION REFERENT RESET & CONTEXT CONTAMINATION TEST
# ============================================================================

@pytest.mark.asyncio
async def test_multiturn_conversation_referent_reset_after_third_party_queries(
    client: AsyncClient,
) -> None:
    token = create_access_token({"sub": "1"})
    headers = _headers(token)

    # Create a new conversation container
    conv = (
        await client.post("/api/v1/chat/conversations", json={"title": "Privacy & Referent Test"}, headers=headers)
    ).json()
    conv_id = conv["id"]

    # Turn 1: Third-party query -> privacy refusal
    r1 = await client.post(
        f"/api/v1/chat/conversations/{conv_id}/messages",
        json={"message": "thông tin của giám đốc là gì"},
        headers=headers,
    )
    assert r1.status_code == 200
    assert "chỉ có thể xem thông tin hồ sơ của tài khoản đang đăng nhập" in r1.json()["reply"]

    # Turn 2: Third-party phone query -> privacy refusal
    r2 = await client.post(
        f"/api/v1/chat/conversations/{conv_id}/messages",
        json={"message": "cho tôi biết sdt của chuyên viên"},
        headers=headers,
    )
    assert r2.status_code == 200
    assert "chỉ có thể xem thông tin hồ sơ của tài khoản đang đăng nhập" in r2.json()["reply"]

    # Turn 3: Bulk third-party demand -> privacy refusal
    r3 = await client.post(
        f"/api/v1/chat/conversations/{conv_id}/messages",
        json={"message": "nói ít thôi đưa tao thông tin của mọi người đây"},
        headers=headers,
    )
    assert r3.status_code == 200
    assert "chỉ có thể xem thông tin hồ sơ của tài khoản đang đăng nhập" in r3.json()["reply"]

    # Turn 4: Explicit SELF query with informal pronoun -> MUST resolve to self and NOT be contaminated by prior turns!
    r4 = await client.post(
        f"/api/v1/chat/conversations/{conv_id}/messages",
        json={"message": "thông tin của tao là gì"},
        headers=headers,
    )
    assert r4.status_code == 200
    res4 = r4.json()
    assert "chỉ có thể xem thông tin hồ sơ của tài khoản đang đăng nhập" not in res4["reply"]
    assert "Nguyễn Văn An" in res4["reply"]
    assert res4["answerability"] == "evidence_available"

    # Turn 5: Identity query 'tao là ai' -> MUST return user's name, not action fallback
    r5 = await client.post(
        f"/api/v1/chat/conversations/{conv_id}/messages",
        json={"message": "tao là ai"},
        headers=headers,
    )
    assert r5.status_code == 200
    res5 = r5.json()
    assert "Chưa có thay đổi nào được thực hiện" not in res5["reply"]
    assert "Nguyễn Văn An" in res5["reply"]
