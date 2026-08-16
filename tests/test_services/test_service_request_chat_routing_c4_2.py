"""C4.2: distinguish Service Request knowledge from an execution request."""
from __future__ import annotations

import pytest

from src.services.chat_routing_service import route_chat_message


@pytest.mark.parametrize(
    "message",
    [
        "Service Request là gì?",
        "Quy trình Service Request là gì?",
        "Quy trình tạo Service Request là gì?",
        "Sau khi gửi Service Request thì ai duyệt?",
        "Service Request cần những thông tin gì?",
        "Trạng thái pending approval nghĩa là gì?",
        "Quy trình xin VPN gồm những bước nào?",
        "Cách xin quyền Git repo thế nào?",
    ],
)
def test_service_request_process_and_policy_questions_use_knowledge(message: str) -> None:
    decision = route_chat_message(message)

    assert decision.route == "knowledge"
    assert decision.should_retrieve is True
    assert decision.should_invoke_tool is False


@pytest.mark.parametrize(
    "message",
    [
        "Tạo Service Request xin laptop cho tôi",
        "Tôi muốn xin laptop mới",
        "Gửi yêu cầu cấp VPN cho tôi",
        "Xin VPN cho tôi",
        "Xin quyền Git repo giúp tôi",
        "Làm giúp tôi một yêu cầu laptop",
        "Tôi muốn đăng ký Microsoft 365",
    ],
)
def test_service_request_execution_requests_use_action_request(message: str) -> None:
    decision = route_chat_message(message)

    assert decision.route == "action_request"
    assert decision.should_retrieve is False
    assert decision.should_invoke_tool is True


@pytest.mark.parametrize(
    "message",
    [
        "Cho tôi biết quy trình yêu cầu laptop",
        "Yêu cầu laptop hoạt động ra sao?",
        "Hướng dẫn đăng ký Microsoft 365",
        "QUY TRÌNH TẠO SERVICE REQUEST LÀ GÌ?",
    ],
)
def test_service_request_knowledge_paraphrases_keep_precedence(message: str) -> None:
    assert route_chat_message(message).route == "knowledge"


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Xin chào", "direct_response"),
        ("Máy tôi không vào được VPN", "incident"),
        ("Ticket INC-123 đang ở trạng thái nào?", "ticket_status"),
        ("Không được", "needs_clarification"),
        ("Tôi cần gặp chuyên viên IT", "knowledge"),
    ],
)
def test_unrelated_routing_contracts_are_unchanged(message: str, expected: str) -> None:
    assert route_chat_message(message).route == expected
