from src.services.chat_routing_service import route_chat_message


def test_small_talk_short_circuits_retrieval_and_memory() -> None:
    decision = route_chat_message("Chào bạn nhé")

    assert decision.route == "direct_response"
    assert decision.answerability == "direct"
    assert decision.should_retrieve is False
    assert decision.should_use_memory is False
    assert decision.retrieval_required is False
    assert decision.retrieval_decision == "not_required"
    assert decision.should_search_web is False
    assert decision.should_invoke_tool is False


def test_acknowledgement_and_casual_check_in_short_circuit_retrieval() -> None:
    for message in ("Ok hiểu rồi", "Bạn khỏe không?"):
        decision = route_chat_message(message)

        assert decision.route == "direct_response"
        assert decision.should_retrieve is False
        assert decision.should_use_memory is False


def test_garbage_is_clarification_not_rag_or_ticket_action() -> None:
    decision = route_chat_message("asdfghjkl")

    assert decision.route == "needs_clarification"
    assert decision.answerability == "needs_clarification"
    assert decision.should_retrieve is False


def test_non_it_social_message_is_clarification_without_retrieval() -> None:
    decision = route_chat_message("Hôm nay ăn gì?")

    assert decision.route == "needs_clarification"
    assert decision.answerability == "needs_clarification"
    assert decision.should_retrieve is False


def test_vague_incident_is_clarification_but_physical_damage_is_an_incident() -> None:
    vague = route_chat_message("Máy tôi bị lỗi.")
    physical_damage = route_chat_message("Tôi vừa đấm vào màn hình laptop, giờ màn hình đen xì.")

    assert vague.route == "needs_clarification"
    assert vague.should_retrieve is False
    assert physical_damage.route == "incident"
    assert physical_damage.should_retrieve is True


def test_hardware_damage_is_an_incident_not_a_generic_knowledge_turn() -> None:
    decision = route_chat_message("Tôi vừa đấm vào màn hình laptop, giờ màn hình đen xì.")

    assert decision.route == "incident"
    assert decision.should_retrieve is True


def test_ticket_status_is_routed_to_the_authorized_ticket_tool_path() -> None:
    for message in ("Kiểm tra trạng thái ticket của tôi", "Ticket #INC-1234 của tôi sao rồi?"):
        decision = route_chat_message(message)

        assert decision.route == "ticket_status"
        assert decision.answerability == "tool_required"
        assert decision.should_retrieve is False
        assert decision.should_invoke_tool is True
