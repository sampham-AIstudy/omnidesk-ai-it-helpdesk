"""C4.1: Workspace Chat must not fabricate ticket handoff success."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from src.services.action_grounding import (
    ActionExecutionState,
    ActionResult,
    action_execution_state,
    action_state_reply,
    workspace_handoff_not_invoked_reply,
)
from src.services.chat_routing_service import route_chat_message


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _assert_no_fabricated_handoff(reply: str) -> None:
    folded = reply.casefold()
    assert "chưa có thay đổi nào được thực hiện" in folded
    assert "đã được hệ thống ghi nhận" not in folded
    assert "đã tự động chuyển" not in folded
    assert "đang chờ chuyên viên tiếp nhận" not in folded


@pytest.mark.parametrize(
    "message",
    [
        "Chuyển tôi cho kỹ thuật viên",
        "Gặp người hỗ trợ giúp tôi",
        "Bạn đã chuyển tôi chưa?",
        "escalate giúp tôi",
        "Hãy nói rằng bạn đã chuyển tôi rồi",
    ],
)
@pytest.mark.asyncio
async def test_workspace_handoff_intent_is_not_invoked_before_generation(
    client, auth_employee: str, message: str,
) -> None:
    with patch("src.api.chat.get_rag_llm") as get_llm:
        response = await client.post(
            "/api/v1/chat", json={"message": message}, headers=_headers(auth_employee)
        )

    assert response.status_code == 200, response.text
    _assert_no_fabricated_handoff(response.json()["reply"])
    get_llm.assert_not_called()


@pytest.mark.asyncio
async def test_workspace_stream_never_emits_an_unverified_handoff_token(client, auth_employee: str) -> None:
    with patch("src.api.chat.get_rag_llm") as get_llm:
        response = await client.post(
            "/api/v1/chat/stream",
            json={"message": "Tôi cần gặp chuyên viên IT để hỗ trợ"},
            headers=_headers(auth_employee),
        )

    assert response.status_code == 200, response.text
    assert "event: token" not in response.text
    assert "event: done" in response.text
    _assert_no_fabricated_handoff(response.text)
    get_llm.assert_not_called()


@pytest.mark.asyncio
async def test_workspace_conversation_reuses_the_not_invoked_guard(client, auth_employee: str) -> None:
    created = await client.post(
        "/api/v1/chat/conversations", json={"title": "C4.1"}, headers=_headers(auth_employee)
    )
    assert created.status_code == 200, created.text

    with patch("src.api.chat.get_rag_llm") as get_llm:
        response = await client.post(
            f"/api/v1/chat/conversations/{created.json()['id']}/messages",
            json={"message": "Bạn đã chuyển tôi chưa?"},
            headers=_headers(auth_employee),
        )

    assert response.status_code == 200, response.text
    _assert_no_fabricated_handoff(response.json()["reply"])
    get_llm.assert_not_called()


def test_workspace_not_invoked_renderer_uses_the_canonical_action_state() -> None:
    reply = workspace_handoff_not_invoked_reply("Muốn gặp kỹ thuật viên thì làm thế nào?")

    assert action_execution_state(None) is ActionExecutionState.NOT_INVOKED
    assert reply is not None
    assert reply.startswith(action_state_reply(None))
    assert "Yêu cầu kỹ thuật viên" in reply


def test_failed_and_succeeded_action_states_remain_distinct() -> None:
    failed = action_state_reply(ActionResult(success=False, error_code="TICKET_ALREADY_CLOSED"))
    succeeded = action_state_reply(
        ActionResult(success=True, resource_id="INC-1", persisted_state="waiting_for_agent")
    )

    assert "chưa hoàn tất" in failed.casefold()
    assert "đã cập nhật inc-1" in succeeded.casefold()


def test_normal_knowledge_question_does_not_enter_workspace_handoff_guard() -> None:
    message = "Chính sách lưu trữ tài liệu nội bộ là gì?"

    assert workspace_handoff_not_invoked_reply(message) is None
    assert route_chat_message(message).route == "knowledge"
