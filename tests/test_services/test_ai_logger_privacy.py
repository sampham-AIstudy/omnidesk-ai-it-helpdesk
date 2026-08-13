from __future__ import annotations

import json
from unittest.mock import mock_open, patch

from src.services import ai_logger


def test_ai_logger_masks_email_and_phone_before_writing(monkeypatch):
    monkeypatch.setattr(
        ai_logger,
        "_get_cached_git_info",
        lambda: {"repo": "test", "branch": "main", "commit": "local", "student": "test@example.com"},
    )

    with patch("builtins.open", mock_open()) as mocked_open:
        ai_logger.log_web_app_ai_event(
            event_name="test",
            prompt="Contact me at an.nguyen@example.com or 0901 234 567.",
            response_summary="Email an.nguyen@example.com; phone +84 901-234-567.",
        )

    event = json.loads(mocked_open().write.call_args.args[0])
    serialized = json.dumps(event)
    assert "an.nguyen@example.com" not in serialized
    assert "test@example.com" not in serialized
    assert "0901 234 567" not in serialized
    assert "+84 901-234-567" not in serialized
    assert event["prompt"].count("***") == 2
    assert event["response_summary"].count("***") == 2
