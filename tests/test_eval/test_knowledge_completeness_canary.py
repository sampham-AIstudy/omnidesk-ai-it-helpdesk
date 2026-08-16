from eval.knowledge_completeness_canary import (
    generation_prompt,
    treatment_system_prompt,
    used_citation_ids,
    uses_generic_fallback,
)


def test_canary_preserves_fixed_evidence_prompt_shape():
    prompt = generation_prompt("VPN dùng port nào?", [])

    assert prompt.startswith("[AUTHORIZED_EVIDENCE]\nNO_AUTHORIZED_EVIDENCE")
    assert prompt.endswith("[USER QUESTION]\nVPN dùng port nào?")


def test_treatment_rule_is_isolated_from_the_runtime_prompt():
    prompt = treatment_system_prompt().casefold()

    assert "[knowledge completeness]" in prompt
    assert "phải dùng mọi evidence có liên quan trực tiếp" in prompt


def test_generic_fallback_detector_distinguishes_precise_abstention():
    assert uses_generic_fallback("Rất tiếc, thông tin hiện có chưa đủ để trả lời câu hỏi này.")
    assert not uses_generic_fallback("Tài liệu hiện có không xác nhận số lần nhập sai trước khi tài khoản bị khóa.")


def test_citation_ids_are_limited_to_fixed_context_sources():
    context = [{"doc_id": "kb-001", "content": "VPN uses 443", "metadata": {"source_id": "kb-001"}}]

    assert used_citation_ids("VPN dùng port 443. [kb-001] [kb-999]", context) == ["kb-001"]
