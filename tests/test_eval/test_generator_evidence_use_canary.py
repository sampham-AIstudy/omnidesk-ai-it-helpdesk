from eval.generator_evidence_use_canary import evidence_salient_prompt


def test_evidence_salience_prompt_preserves_verbatim_source_content_after_question():
    context = [{"doc_id": "kb-001", "content": "VPN uses port 443.", "metadata": {"source_id": "kb-001"}}]

    prompt = evidence_salient_prompt("VPN dùng port nào?", context)

    assert prompt.index("[USER QUESTION]") < prompt.index("[AUTHORIZED_EVIDENCE")
    assert "[kb-001]" in prompt
    assert "VPN uses port 443." in prompt
    assert "<AUTHORIZED_SOURCE_DATA>" in prompt
    assert "[END_AUTHORIZED_EVIDENCE]" in prompt
