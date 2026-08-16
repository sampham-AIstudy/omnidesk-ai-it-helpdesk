from eval.precise_abstention_canary import (
    TARGET_IDS,
    candidate_path_eligible,
    has_precise_subject,
    render_candidate_precise_abstention,
)


def test_target_subjects_are_named_without_inventing_missing_values() -> None:
    for question in (
        "Password công ty cần tối thiểu bao nhiêu ký tự?",
        "Phiên bản mới nhất của Microsoft Teams hiện tại là gì?",
        "Account sẽ khóa sau bao nhiêu lần nhập sai?",
    ):
        reply = render_candidate_precise_abstention(question)
        assert has_precise_subject(reply, question)
        assert "không xác nhận" in reply.casefold()


def test_canary_scope_remains_three_empty_context_targets() -> None:
    assert TARGET_IDS == ("GT-046", "GT-077", "GT-087")


def test_candidate_scope_excludes_nonempty_action_and_direct_paths() -> None:
    assert candidate_path_eligible(route="knowledge", authorized_source_count=0, web_source_count=0)
    assert not candidate_path_eligible(route="knowledge", authorized_source_count=1, web_source_count=0)
    assert not candidate_path_eligible(route="action_request", authorized_source_count=0, web_source_count=0)
    assert not candidate_path_eligible(route="direct_response", authorized_source_count=0, web_source_count=0)
