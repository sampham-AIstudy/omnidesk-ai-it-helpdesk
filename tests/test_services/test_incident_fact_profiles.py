from src.services.chat_response_planning import build_response_plan
from src.services.incident_fact_profiles import extract_incident_fact_state


def test_ambiguous_roi_does_not_turn_hoi_roi_into_physical_impact() -> None:
    for message in ("Laptop tôi hỏng rồi.", "VPN lỗi rồi.", "Tôi restart rồi."):
        state = extract_incident_fact_state(message)
        assert state.known_facts.get("physical_damage") != "physical_impact"
        assert state.known_facts.get("cause") != "physical_impact"


def test_explicit_vietnamese_impact_markers_are_detected_at_token_boundaries() -> None:
    for message in ("Tôi làm rơi laptop.", "Tôi đập màn hình laptop.", "Tôi đấm vào màn hình laptop."):
        state = extract_incident_fact_state(message)
        assert state.domain == "HARDWARE_PHYSICAL_DAMAGE"
        assert state.known_facts["physical_damage"] == "physical_impact"


def test_vpn_profile_has_no_global_hardware_required_facts() -> None:
    state = extract_incident_fact_state("VPN không kết nối được")
    assert state.domain == "VPN_CONNECTIVITY"
    assert state.is_incident is True
    assert state.missing_required_facts == []
    assert "device" in state.optional_facts

    plan = build_response_plan("VPN không kết nối được", [])
    assert plan.incident_domain == "VPN_CONNECTIVITY"
    assert plan.missing_required_facts == []


def test_multi_intent_laptop_replacement_does_not_infer_impact() -> None:
    plan = build_response_plan("Laptop tôi hỏng rồi và tôi muốn xin laptop thay thế.", [])
    assert plan.primary_intent == "incident"
    assert plan.secondary_intents == ["service_request_replacement_device"]
    assert plan.incident_domain == "HARDWARE_PHYSICAL_DAMAGE"
    assert plan.known_facts.get("physical_damage") is None
    assert plan.known_facts.get("cause") is None
