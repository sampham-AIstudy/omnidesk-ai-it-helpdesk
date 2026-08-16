from src.services.chat_response_planning import (
    build_response_plan,
    minimal_incident_triage_reply,
    partial_evidence_reply,
)


def test_partial_answer_plan_separates_supported_and_unsupported_claims() -> None:
    plan = build_response_plan(
        "VPN dùng cổng nào và tài khoản bị khóa sau bao nhiêu lần nhập sai?",
        [{"content": "VPN uses port 443 for the corporate gateway."}],
    )
    assert plan.answerable_claims == ["VPN dùng cổng nào"]
    assert plan.unsupported_claims == ["tài khoản bị khóa sau bao nhiêu lần nhập sai"]
    reply = partial_evidence_reply(plan, [{"content": "VPN uses port 443 for the corporate gateway."}])
    assert reply is not None
    assert "port 443" in reply
    assert "không đủ" in reply


def test_incident_plan_preserves_known_facts_and_asks_no_required_question() -> None:
    plan = build_response_plan("Tôi vừa đấm vào màn hình laptop, giờ màn hình đen xì luôn.", [])
    assert plan.known_facts == {
        "device": "laptop", "symptom": "black_screen", "cause": "physical_impact",
        "physical_damage": "physical_impact",
        "temporal_relation": "immediate_or_after_event",
    }
    assert plan.missing_required_facts == []
    reply = minimal_incident_triage_reply(plan)
    assert reply is not None
    assert "không cần hỏi lại" in reply


def test_multi_intent_plan_keeps_incident_and_replacement_request() -> None:
    plan = build_response_plan("Laptop tôi hỏng rồi và tôi muốn xin laptop thay thế.", [])
    assert plan.primary_intent == "incident"
    assert plan.secondary_intents == ["service_request_replacement_device"]
