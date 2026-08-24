from scripts.promote_p0_shadow_v3 import _record_digest


def test_record_digest_is_stable_and_detects_metadata_change() -> None:
    original = [{"id": "p0-01", "document": "content", "metadata": {"topic": "vpn.auth"}, "embedding": [0.1, 0.2]}]
    copied = [{"id": "p0-01", "document": "content", "metadata": {"topic": "vpn.auth"}, "embedding": [0.1, 0.2]}]
    changed = [{"id": "p0-01", "document": "content", "metadata": {"topic": "routing"}, "embedding": [0.1, 0.2]}]
    assert _record_digest(original) == _record_digest(copied)
    assert _record_digest(original) != _record_digest(changed)
