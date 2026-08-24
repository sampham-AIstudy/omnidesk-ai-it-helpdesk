from eval.knowledge_evidence_salience_slice import regression_cause


def test_regression_cause_prioritizes_dangerous_unsupported_expansion():
    control = {"failure_types": [], "generic_fallback_used": False}
    treatment = {"failure_types": ["UNSUPPORTED_CLAIM"], "generic_fallback_used": False}

    assert regression_cause(control, treatment) == "UNSUPPORTED_EXPANSION"


def test_regression_cause_marks_generic_incomplete_as_attention_shift():
    control = {"failure_types": [], "generic_fallback_used": False}
    treatment = {"failure_types": ["INCOMPLETE_ANSWER"], "generic_fallback_used": True}

    assert regression_cause(control, treatment) == "QUESTION_FIRST_ATTENTION_SHIFT"
