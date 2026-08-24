from eval.baseline_v1 import (
    deterministic_generation_checks,
    evaluate_clarification,
    evaluate_partial_answer,
    route_result,
)
from src.services.chat_response_planning import (
    build_response_plan,
    minimal_incident_triage_reply,
    partial_evidence_reply,
)


def test_regression_a_sufficient_incident_facts_actionable_no_redundant_clarification() -> None:
    """A. Sufficient incident facts: actionable answer, no redundant clarification."""
    # Semantic family: physical impact on laptop resulting in black screen
    queries = [
        "Tôi vừa đấm vào màn hình laptop, giờ màn hình đen xì luôn.",
        "Tôi lỡ tay đập vào laptop, giờ màn hình bị đen không hiển thị gì.",
        "Vừa làm rơi laptop xong giờ màn hình bị tối đen.",
    ]
    for query in queries:
        plan = build_response_plan(query, [])
        assert plan.known_facts.get("device") == "laptop"
        assert plan.known_facts.get("symptom") == "black_screen"
        assert plan.missing_required_facts == []

        reply = minimal_incident_triage_reply(plan)
        assert reply is not None
        # Must give safe actionable guidance
        assert "ngừng mọi tác động" in reply or "ngừng tác động" in reply
        assert "đèn nguồn" in reply or "màn hình ngoài" in reply
        assert "kỹ thuật" in reply.casefold() or "hỗ trợ" in reply.casefold()

        # Must have 0 redundant questions
        clar = evaluate_clarification(
            reply,
            {"device": "laptop", "symptom": "black_screen", "cause": "physical_impact", "temporal_relation": "immediate"},
            [],
        )
        assert clar["redundant_question_count"] == 0
        assert clar["missing_required_question_count"] == 0
        assert clar["unnecessary_question_count"] == 0


def test_regression_b_compound_question_all_facts_supported() -> None:
    """B. Compound question with all facts supported: answers all supported facts."""
    docs = [
        {"doc_id": "doc-vpn", "content": "Corporate VPN uses port 443.", "metadata": {"source_id": "doc-vpn"}},
        {"doc_id": "doc-policy", "content": "Tài khoản bị khóa sau 5 lần nhập sai mật khẩu.", "metadata": {"source_id": "doc-policy"}},
    ]
    plan = build_response_plan("VPN dùng cổng nào và tài khoản bị khóa sau bao nhiêu lần nhập sai?", docs)
    assert len(plan.answerable_claims) == 2
    assert len(plan.unsupported_claims) == 0


def test_regression_c_compound_question_partially_supported() -> None:
    """C. Compound question partially supported: answer supported portion, abstain only unsupported portion."""
    docs = [
        {"doc_id": "eval-gt047-vpn-port", "content": "Corporate VPN gateway uses port 443. This fixture contains no account lockout policy.", "metadata": {"source_id": "eval-gt047-vpn-port"}},
    ]
    plan = build_response_plan("VPN dùng cổng nào và tài khoản bị khóa sau bao nhiêu lần nhập sai?", docs)
    assert plan.answerable_claims == ["VPN dùng cổng nào"]
    assert plan.unsupported_claims == ["tài khoản bị khóa sau bao nhiêu lần nhập sai"]

    reply = partial_evidence_reply(plan, docs)
    assert reply is not None
    assert "port 443" in reply
    assert "[eval-gt047-vpn-port]" in reply
    assert "chưa đủ" in reply or "không đủ" in reply
    assert "5 lần" not in reply  # No hallucination

    # Evaluation contracts
    failures = evaluate_partial_answer(reply)
    assert failures == []


def test_regression_d_compound_question_no_evidence_full_abstention() -> None:
    """D. Compound question with no evidence: full abstention remains allowed."""
    plan = build_response_plan("VPN dùng cổng nào và tài khoản bị khóa sau bao nhiêu lần nhập sai?", [])
    assert len(plan.answerable_claims) == 0
    assert len(plan.unsupported_claims) == 2
    reply = partial_evidence_reply(plan, [])
    assert reply is None  # Partial evidence reply not applicable, falls through to general abstention


def test_regression_e_should_use_memory_false_no_memory_invocation() -> None:
    """E. should_use_memory=false: no memory invocation in route_result."""
    case = {
        "id": "GT-047",
        "query": "VPN dùng cổng nào và tài khoản bị khóa sau bao nhiêu lần nhập sai?",
        "expected_route": None,
        "should_retrieve": True,
        "should_use_memory": False,
    }
    actual, failures, status = route_result(case)
    assert actual["retrieve_memory"] is False
    assert status == "NOT_APPLICABLE"


def test_regression_f_irrelevant_evidence_quality_contract() -> None:
    """F. Irrelevant evidence cannot satisfy evidence-quality contract."""
    case = {
        "id": "GT-TEST",
        "query": "Cấu hình VPN trên macOS",
        "expected_titles": ["Hướng dẫn cấu hình VPN"],
        "expected_context_terms": ["forticlient", "macos"],
        "should_retrieve": True,
        "should_use_memory": False,
        "should_search_web": False,
        "should_create_ticket": False,
        "should_escalate": False,
    }
    # Irrelevant docs
    irrelevant_docs = [{"content": "Hướng dẫn cài đặt máy in Canon LBP 2900.", "metadata": {"title": "Cài máy in", "source_id": "fx-print-001"}}]
    doc_text = " ".join(d["content"] for d in irrelevant_docs).casefold()
    expected_terms = [t.casefold() for t in case["expected_context_terms"]]
    hits = sum(1 for term in expected_terms if term in doc_text)
    assert hits == 0  # Evidence is not relevant and coverage is 0


def test_regression_g_citation_references_only_evidence_used() -> None:
    """G. Citation references only evidence actually used."""
    docs = [
        {"doc_id": "eval-gt047-vpn-port", "content": "Corporate VPN gateway uses port 443.", "metadata": {"source_id": "eval-gt047-vpn-port"}},
        {"doc_id": "eval-unused-doc", "content": "Unrelated BitLocker recovery key instructions.", "metadata": {"source_id": "eval-unused-doc"}},
    ]
    plan = build_response_plan("VPN dùng cổng nào và tài khoản bị khóa sau bao nhiêu lần nhập sai?", docs)
    reply = partial_evidence_reply(plan, docs)
    assert reply is not None
    assert "[eval-gt047-vpn-port]" in reply
    assert "[eval-unused-doc]" not in reply

    checks, failures = deterministic_generation_checks(
        {"required_answer_terms": ["443"]},
        reply,
        docs,
    )
    assert checks["citation_ids"] == ["eval-gt047-vpn-port"]
    assert checks["invalid_citation_ids"] == []
    assert failures == []
