from src.guardrails.input_guardrails import InputGuardrailPlugin
from src.guardrails.output_guardrails import format_plain_text_response


def test_plain_text_finalizer_removes_markdown_but_preserves_citations():
    result = format_plain_text_response("# Title\n**Important** and _plain_.\n- Step [1]\n[Microsoft](https://learn.microsoft.com)")

    assert "**" not in result
    assert "_plain_" not in result
    assert "# Title" not in result
    assert "[1]" in result
    assert "Microsoft (https://learn.microsoft.com)" in result


def test_non_it_food_request_is_blocked_before_rag_or_web_research():
    result = InputGuardrailPlugin().on_user_message_callback("t muốn hốc cơm")

    assert result["decision"] == "BLOCK"
    assert "IT support" in result["safe_response"]
