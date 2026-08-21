import json
from pathlib import Path

from scripts.evaluate_p0_hard_negatives import _metrics

DATASET = Path(__file__).resolve().parents[2] / "eval" / "p0_shadow_v3_hard_negative_cases.json"


def test_hard_negative_dataset_has_required_families_and_variants():
    cases = json.loads(DATASET.read_text(encoding="utf-8"))["cases"]
    by_category = {}
    for case in cases:
        by_category[case["category"]] = by_category.get(case["category"], 0) + 1
        assert case["expected_source_ids"]
        assert "acceptable_source_ids" in case
        assert case["hard_negative_source_ids"] or case["hard_negative_topics"]

    assert by_category == {
        "tcp_port_vs_http_status": 10,
        "ping_vs_tcp": 5,
        "timeout_vs_refused": 10,
        "vpn_auth_vs_post_connection": 10,
        "dns_routing_proxy": 10,
        "http_vs_generic_firewall": 5,
    }


def test_metrics_count_rank_one_hard_negative_as_intent_confusion():
    metrics = _metrics([
        {"primary_rank": 1, "hard_negative_at_1": False, "hard_negative_in_top3": False, "intent_confusion": False},
        {"primary_rank": 2, "hard_negative_at_1": True, "hard_negative_in_top3": True, "intent_confusion": True},
    ])

    assert metrics["hit_rate_at_1"] == 0.5
    assert metrics["hit_rate_at_3"] == 1.0
    assert metrics["hard_negative_at_1_rate"] == 0.5
    assert metrics["intent_confusion_rate"] == 0.5
