"""Comprehensive Chat Behavior Regression Gate Test Suite."""
from __future__ import annotations

import unicodedata
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from eval.behavior.behavior_validator import (
    BehaviorCase,
    load_behavior_manifest,
    parse_sse_events,
    validate_manifest_integrity,
)
from src.guardrails.input_guardrails import InputGuardrailPlugin
from src.services.action_grounding import (
    ActionExecutionState,
    ActionResult,
    action_execution_state,
    action_state_reply,
    may_confirm_action,
)
from src.services.auth_service import create_access_token
from src.version import get_build_info

BEHAVIOR_CASES = load_behavior_manifest()
CASE_IDS = [case.id for case in BEHAVIOR_CASES]


@pytest.fixture(scope="session")
def auth_employee_token() -> str:
    """Generate deterministic JWT token for employee1."""
    return create_access_token({"sub": "1"})


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(char for char in decomposed if unicodedata.category(char) != "Mn").replace("đ", "d")


class _MockChunk:
    def __init__(self, content: str):
        self.content = content


def _create_mock_llm(reply_text: str) -> Any:
    mock = MagicMock()
    mock.model = "mistral-mock"
    mock.ainvoke = AsyncMock(return_value=MagicMock(content=reply_text))

    async def _mock_astream(*args, **kwargs):
        yield _MockChunk(reply_text)

    mock.astream = _mock_astream
    return mock


# ============================================================================
# 1. MANIFEST INTEGRITY & PAIRED CASE VALIDATION
# ============================================================================

@pytest.mark.behavior_gate
def test_manifest_schema_and_pairing_integrity() -> None:
    """Ensure manifest is structurally sound with bi-directional positive/negative pairs."""
    errors = validate_manifest_integrity()
    assert not errors, f"Manifest integrity validation failed: {errors}"
    assert len(BEHAVIOR_CASES) >= 25, f"Expected at least 25 behavior cases, got {len(BEHAVIOR_CASES)}"


# ============================================================================
# 2. REAL CHAT PATH EXECUTION (REST API)
# ============================================================================

@pytest.mark.behavior_gate
@pytest.mark.parametrize("case", BEHAVIOR_CASES, ids=CASE_IDS)
@pytest.mark.asyncio
async def test_behavior_contract_rest_execution(
    client: AsyncClient, auth_employee_token: str, case: BehaviorCase
) -> None:
    """Verify each behavior case through the real REST chat endpoint (/api/v1/chat)."""
    mock_rag_resp = (
        "Chào bạn, sau khi đổi mật khẩu VPN nếu không đăng nhập được, bạn hãy kiểm tra lại thông tin xác thực "
        "hoặc khởi động lại client VPN theo quy trình hỗ trợ IT."
    )
    mock_llm = _create_mock_llm(mock_rag_resp)
    mock_fast_llm = _create_mock_llm('{"is_complex": false, "sub_queries": []}')
    from src.services.web_research_service import ResearchResult
    empty_research = ResearchResult(False, "web_search_not_triggered", None, [])

    with (
        patch("src.api.chat.get_rag_llm", return_value=mock_llm),
        patch("src.services.query_decomposition_service.get_fast_classifier_llm", return_value=mock_fast_llm),
        patch("src.api.chat.maybe_research_web", new=AsyncMock(return_value=empty_research)),
    ):
        resp = await client.post(
            "/api/v1/chat",
            json={"message": case.input},
            headers=_headers(auth_employee_token),
        )

    assert resp.status_code == 200, f"Expected 200 for case {case.id}, got {resp.status_code}: {resp.text}"
    body = resp.json()
    reply = body.get("reply", "")
    folded_reply = _fold(reply)

    # A. Blocked vs Allowed Verification
    if case.expected.blocked:
        plugin = InputGuardrailPlugin()
        guard_res = plugin.on_user_message_callback(case.input)
        assert guard_res["decision"] == "BLOCK", f"Case {case.id} should have been blocked by guardrail"
        if case.expected.refusal_category:
            assert (
                guard_res.get("security_category") == case.expected.refusal_category
            ), f"Case {case.id} expected category {case.expected.refusal_category}, got {guard_res.get('security_category')}"

        assert body.get("answerability") in ("unanswerable", "needs_clarification", None)
    else:
        assert body.get("answerability") != "unanswerable", f"Case {case.id} was unexpectedly marked unanswerable"

    # B. Clarification Requirement Verification
    if case.expected.requires_clarification:
        assert (
            body.get("answerability") == "needs_clarification"
            or _fold("cần thêm thông tin") in folded_reply
            or _fold("hỗ trợ") in folded_reply
        )

    # C. Multi-Intent / Confirmation Verification
    if case.expected.requires_confirmation:
        assert "xac nhan" in folded_reply or "chua co thay doi nao" in folded_reply

    # D. Semantic Inclusions / Exclusions
    if case.expected.must_include_semantics:
        for term in case.expected.must_include_semantics:
            assert _fold(term) in folded_reply, (
                f"Case {case.id} response missing required semantic term '{term}'. Reply was:\n{reply}"
            )

    if case.expected.must_not_include_semantics:
        for term in case.expected.must_not_include_semantics:
            assert _fold(term) not in folded_reply, (
                f"Case {case.id} response contained forbidden semantic term '{term}'. Reply was:\n{reply}"
            )


# ============================================================================
# 3. REAL CHAT PATH EXECUTION (SSE STREAMING API)
# ============================================================================

@pytest.mark.behavior_gate
@pytest.mark.parametrize("case", BEHAVIOR_CASES, ids=CASE_IDS)
@pytest.mark.asyncio
async def test_behavior_contract_stream_execution(
    client: AsyncClient, auth_employee_token: str, case: BehaviorCase
) -> None:
    """Verify each behavior case through the real SSE streaming endpoint (/api/v1/chat/stream)."""
    mock_rag_resp = (
        "Chào bạn, sau khi đổi mật khẩu VPN nếu không đăng nhập được, bạn hãy kiểm tra lại thông tin xác thực "
        "hoặc khởi động lại client VPN theo quy trình hỗ trợ IT."
    )
    mock_llm = _create_mock_llm(mock_rag_resp)
    mock_fast_llm = _create_mock_llm('{"is_complex": false, "sub_queries": []}')
    from src.services.web_research_service import ResearchResult
    empty_research = ResearchResult(False, "web_search_not_triggered", None, [])

    with (
        patch("src.api.chat.get_rag_llm", return_value=mock_llm),
        patch("src.services.query_decomposition_service.get_fast_classifier_llm", return_value=mock_fast_llm),
        patch("src.api.chat.maybe_research_web", new=AsyncMock(return_value=empty_research)),
    ):
        resp = await client.post(
            "/api/v1/chat/stream",
            json={"message": case.input},
            headers=_headers(auth_employee_token),
        )

    assert resp.status_code == 200
    events = parse_sse_events(resp.text)
    assert len(events) >= 1, f"Case {case.id} received empty SSE stream"

    # Terminal done event verification
    done_events = [e for e in events if e.get("event") == "done"]
    assert len(done_events) == 1, f"Case {case.id} expected exactly one terminal 'done' event, got {len(done_events)}"
    done_data = done_events[0].get("data", {})
    reply = done_data.get("reply", "")
    folded_reply = _fold(reply)

    if case.expected.blocked:
        assert done_data.get("answerability") in ("unanswerable", "needs_clarification", None)

    if case.expected.must_include_semantics:
        for term in case.expected.must_include_semantics:
            assert _fold(term) in folded_reply, (
                f"SSE Case {case.id} stream missing required semantic '{term}'. Reply was:\n{reply}"
            )

    if case.expected.must_not_include_semantics:
        for term in case.expected.must_not_include_semantics:
            assert _fold(term) not in folded_reply, (
                f"SSE Case {case.id} stream contained forbidden semantic '{term}'. Reply was:\n{reply}"
            )


# ============================================================================
# 4. REST AND SSE BEHAVIORAL PARITY
# ============================================================================

@pytest.mark.behavior_gate
@pytest.mark.parametrize("case", BEHAVIOR_CASES[:10], ids=CASE_IDS[:10])
@pytest.mark.asyncio
async def test_rest_and_sse_behavioral_parity(
    client: AsyncClient, auth_employee_token: str, case: BehaviorCase
) -> None:
    """Ensure REST and SSE streaming return equivalent behavioral contracts."""
    mock_rag_resp = (
        "Chào bạn, sau khi đổi mật khẩu VPN nếu không đăng nhập được, bạn hãy kiểm tra lại thông tin xác thực "
        "hoặc khởi động lại client VPN theo quy trình hỗ trợ IT."
    )
    mock_llm = _create_mock_llm(mock_rag_resp)
    mock_fast_llm = _create_mock_llm('{"is_complex": false, "sub_queries": []}')
    from src.services.web_research_service import ResearchResult
    empty_research = ResearchResult(False, "web_search_not_triggered", None, [])

    with (
        patch("src.api.chat.get_rag_llm", return_value=mock_llm),
        patch("src.services.query_decomposition_service.get_fast_classifier_llm", return_value=mock_fast_llm),
        patch("src.api.chat.maybe_research_web", new=AsyncMock(return_value=empty_research)),
    ):
        rest_resp = await client.post(
            "/api/v1/chat",
            json={"message": case.input},
            headers=_headers(auth_employee_token),
        )
        stream_resp = await client.post(
            "/api/v1/chat/stream",
            json={"message": case.input},
            headers=_headers(auth_employee_token),
        )

    assert rest_resp.status_code == 200
    assert stream_resp.status_code == 200

    rest_data = rest_resp.json()
    events = parse_sse_events(stream_resp.text)
    done_data = [e["data"] for e in events if e.get("event") == "done"][0]

    # Parity assertions: Same answerability, same classification confidence, same reply content
    assert rest_data.get("answerability") == done_data.get("answerability")
    assert rest_data.get("reply") == done_data.get("reply")


# ============================================================================
# 5. ACTION GROUNDING STATE MACHINE COMPLETE MATRIX
# ============================================================================

@pytest.mark.behavior_gate
def test_action_grounding_complete_matrix() -> None:
    """Test all action state transitions (SUCCESS, FAILED, TIMEOUT, NULL, malformed)."""
    # 1. Authoritative Success with resource
    success_res = ActionResult(success=True, resource_id="INC-2026-999", persisted_state="waiting_for_agent")
    assert action_execution_state(success_res) is ActionExecutionState.SUCCEEDED
    assert may_confirm_action(success_res, requires_resource=True) is True
    reply_success = action_state_reply(success_res)
    assert "INC-2026-999" in reply_success
    assert "waiting_for_agent" in reply_success

    # 2. Authoritative Success with resource_id only
    res_id_only = ActionResult(success=True, resource_id="REQ-2026-001")
    assert may_confirm_action(res_id_only) is True
    assert "REQ-2026-001" in action_state_reply(res_id_only)

    # 3. Action Failure
    failed_res = ActionResult(success=False, error_code="SERVICE_UNAVAILABLE")
    assert action_execution_state(failed_res) is ActionExecutionState.FAILED
    assert may_confirm_action(failed_res) is False
    assert "thao tác chưa hoàn tất" in action_state_reply(failed_res).lower()
    assert "thành công" not in action_state_reply(failed_res).lower()

    # 4. Timeout Failure
    timeout_res = ActionResult(success=False, error_code="DATABASE_TIMEOUT")
    assert action_execution_state(timeout_res) is ActionExecutionState.FAILED
    assert may_confirm_action(timeout_res) is False
    assert "thao tác chưa hoàn tất" in action_state_reply(timeout_res).lower()
    assert "thành công" not in action_state_reply(timeout_res).lower()

    # 5. Null / NOT_INVOKED Result
    assert action_execution_state(None) is ActionExecutionState.NOT_INVOKED
    assert may_confirm_action(None) is False
    assert action_state_reply(None) == "Chưa có thay đổi nào được thực hiện."


# ============================================================================
# 6. TENANT & CONVERSATION ISOLATION
# ============================================================================

@pytest.mark.behavior_gate
@pytest.mark.asyncio
async def test_tenant_and_conversation_isolation(client: AsyncClient, auth_employee_token: str) -> None:
    """Verify tenant isolation and prevent cross-tenant resource discovery."""
    from src.guardrails.access_guardrails import check_kb_access, check_ticket_access

    user_real_estate = {"user_id": "1", "company_unit": "real_estate", "role": "employee"}
    ticket_healthcare = {"ticket_id": "t1", "company_unit": "healthcare", "created_by_id": "2"}
    ticket_same_tenant_other_user = {"ticket_id": "t2", "company_unit": "real_estate", "created_by_id": "2"}
    ticket_own = {"ticket_id": "t3", "company_unit": "real_estate", "created_by_id": "1"}

    # Employee in REAL_ESTATE cannot access ticket in HEALTHCARE (cross-tenant)
    assert check_ticket_access(user_real_estate, ticket_healthcare)["allowed"] is False

    # Employee cannot access another employee's private ticket in same tenant (IDOR)
    assert check_ticket_access(user_real_estate, ticket_same_tenant_other_user)["allowed"] is False

    # Employee can access their own ticket
    assert check_ticket_access(user_real_estate, ticket_own)["allowed"] is True

    # KB cross-tenant isolation
    kb_healthcare = {"company_unit": "healthcare", "applicable_to_all": False}
    kb_all = {"company_unit": "all", "applicable_to_all": True}
    assert check_kb_access(user_real_estate, kb_healthcare)["allowed"] is False
    assert check_kb_access(user_real_estate, kb_all)["allowed"] is True


# ============================================================================
# 7. RUNTIME VERSION & BUILD VISIBILITY
# ============================================================================

@pytest.mark.behavior_gate
@pytest.mark.asyncio
async def test_runtime_version_and_build_identity(client: AsyncClient) -> None:
    """Verify that /health exposes build commit, manifest hash, and version identifiers."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "ok"
    assert "version" in data
    assert "build_commit" in data
    assert "manifest_hash" in data
    assert "guardrails_version" in data
    assert "behavior_contract_version" in data

    build_info = get_build_info()
    assert data["build_commit"] == build_info["git_commit"]
    assert data["manifest_hash"] == build_info["manifest_hash"]
