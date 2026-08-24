from __future__ import annotations

import json
from pathlib import Path

from eval.v4_eval_matching import (
    doc_matches_targets,
    targets_canonical_aliases,
)

ROOT = Path(__file__).resolve().parents[2]
HN_DATASET_PATH = ROOT / "eval" / "expanded_hard_negatives_v4.json"


def test_matching_with_missing_or_none_metadata_does_not_falsely_match() -> None:
    doc = {
        "doc_id": "kb-001",
        "metadata": {
            "source_id": None,
            "canonical_source_id": None,
            "title": "VPN Guide",
        },
    }
    target_aliases = targets_canonical_aliases(["web-github-ssh-permission-denied-001"])
    negative_aliases = targets_canonical_aliases(["p0-05-firewall-acl-nat-c001"])

    assert not doc_matches_targets(doc, target_aliases)
    assert not doc_matches_targets(doc, negative_aliases)


def test_matching_does_not_perform_unsafe_substring_matching() -> None:
    doc = {"doc_id": "kb-010", "metadata": {}}
    target_aliases = targets_canonical_aliases(["kb-001", "kb-01"])
    assert not doc_matches_targets(doc, target_aliases)


def test_matching_handles_chunk_suffixes_and_canonical_ids() -> None:
    doc = {
        "doc_id": "web-github-ssh-permission-denied-002",
        "metadata": {
            "source_id": "github-ssh-permission-denied",
            "canonical_source_id": "github-ssh-permission-denied",
        },
    }
    target_aliases = targets_canonical_aliases(["web-github-ssh-permission-denied-001"])
    assert doc_matches_targets(doc, target_aliases)


def test_dataset_target_and_negative_sets_never_overlap() -> None:
    assert HN_DATASET_PATH.exists()
    dataset = json.loads(HN_DATASET_PATH.read_text(encoding="utf-8"))
    assert len(dataset) == 100

    for item in dataset:
        raw_target = set(item["primary_expected_source_ids"])
        raw_neg = set(item["hard_negative_source_ids"])
        assert not (raw_target & raw_neg), f"Raw overlap in {item['id']}"

        canon_target = targets_canonical_aliases(raw_target)
        canon_neg = targets_canonical_aliases(raw_neg)
        assert not (canon_target & canon_neg), f"Canonical overlap in {item['id']}"


def test_rank1_mutually_exclusive_classification() -> None:
    doc_target = {"doc_id": "web-github-ssh-permission-denied-001", "metadata": {}}
    doc_neg = {"doc_id": "p0-05-firewall-acl-nat-c001", "metadata": {}}
    doc_neither = {"doc_id": "kb-001", "metadata": {}}

    target_aliases = targets_canonical_aliases(["web-github-ssh-permission-denied-001"])
    neg_aliases = targets_canonical_aliases(["p0-05-firewall-acl-nat-c001"])

    def classify_rank1(doc: dict) -> str:
        is_tgt = doc_matches_targets(doc, target_aliases)
        is_hn = doc_matches_targets(doc, neg_aliases)
        if is_tgt and is_hn:
            return "BOTH"
        if is_tgt:
            return "TARGET_ONLY"
        if is_hn:
            return "HARD_NEGATIVE_ONLY"
        return "NEITHER"

    assert classify_rank1(doc_target) == "TARGET_ONLY"
    assert classify_rank1(doc_neg) == "HARD_NEGATIVE_ONLY"
    assert classify_rank1(doc_neither) == "NEITHER"
