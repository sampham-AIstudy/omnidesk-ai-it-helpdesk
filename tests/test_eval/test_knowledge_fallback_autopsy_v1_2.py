from eval.knowledge_fallback_autopsy_v1_2 import context_state, runtime_trace


def test_intentionally_empty_fixture_is_not_misclassified_as_lost_context():
    state, intentionally_empty = context_state("GT-046", [])

    assert state == "EMPTY"
    assert intentionally_empty is True


def test_fixed_context_trace_has_no_pre_generation_fallback_gate():
    context = [{"doc_id": "kb-001", "content": "VPN uses port 443.", "metadata": {"source_id": "kb-001"}}]

    trace = runtime_trace("GT-047", "VPN dùng port nào?", context, "VPN uses port 443. [kb-001]")

    assert trace["final_generator_context"]["source_ids_retained"] == ["kb-001"]
    assert trace["final_generator_context"]["fallback_flags"]["deterministic_pre_generation_fallback"] is False
    assert trace["final_generator_context"]["answerability_gate"] == "NONE_IN_FIXED_CONTEXT_EVALUATION"
