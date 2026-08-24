"""Contract helpers for the V4 broad-coverage evaluation only.

This module deliberately lives under :mod:`eval`: production retrieval must
never consume benchmark labels, acceptable targets, or scoring classifications.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from eval.v4_eval_matching import targets_canonical_aliases

CONTRACT_PATH = Path("eval/broad_coverage_v4_contract.json")
AMBIGUOUS = "AMBIGUOUS"
COVERAGE_GAP = "COVERAGE_GAP"


def load_contract(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    """Load and minimally validate the versioned V4 evaluation contract."""
    contract = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(contract.get("schema_version"), str):
        raise ValueError("BROAD_CONTRACT_SCHEMA_VERSION_MISSING")
    if not isinstance(contract.get("case_overrides"), dict):
        raise ValueError("BROAD_CONTRACT_CASE_OVERRIDES_MISSING")
    if not isinstance(contract.get("acceptable_alternatives"), dict):
        raise ValueError("BROAD_CONTRACT_ALTERNATIVES_MISSING")
    return contract


def case_override(contract: dict[str, Any], case_id: str) -> dict[str, Any]:
    """Return a case's declared scoring classification, if any."""
    return contract["case_overrides"].get(case_id, {})


def acceptable_doc_ids(contract: dict[str, Any], case_id: str) -> list[str]:
    """Return explicit source-level alternatives for one evaluation case."""
    return contract["acceptable_alternatives"].get(case_id, {}).get("acceptable_doc_ids", [])


def target_doc_ids(case: dict[str, Any], contract: dict[str, Any]) -> list[str]:
    """Combine primary and accepted evaluation sources without changing runtime."""
    return [*case["expected_doc_ids"], *acceptable_doc_ids(contract, case["id"])]


def validate_contract(dataset: list[dict[str, Any]], contract: dict[str, Any]) -> None:
    """Reject malformed aliases or references before executing a benchmark."""
    dataset_ids = {case["id"] for case in dataset}
    referenced = set(contract["case_overrides"]) | set(contract["acceptable_alternatives"])
    unknown = sorted(referenced - dataset_ids)
    if unknown:
        raise ValueError(f"BROAD_CONTRACT_UNKNOWN_CASE_IDS:{','.join(unknown)}")

    for case in dataset:
        primary = case.get("expected_doc_ids")
        if not isinstance(primary, list) or not primary or not targets_canonical_aliases(primary):
            raise ValueError(f"BROAD_CONTRACT_MALFORMED_PRIMARY_TARGETS:{case['id']}")

        alternatives = acceptable_doc_ids(contract, case["id"])
        if not isinstance(alternatives, list) or not all(isinstance(item, str) and item.strip() for item in alternatives):
            raise ValueError(f"BROAD_CONTRACT_MALFORMED_ALTERNATIVES:{case['id']}")
        if alternatives and not targets_canonical_aliases(alternatives):
            raise ValueError(f"BROAD_CONTRACT_EMPTY_ALTERNATIVE_ALIASES:{case['id']}")

        override = case_override(contract, case["id"])
        classification = override.get("classification")
        if classification and classification not in {AMBIGUOUS, COVERAGE_GAP}:
            raise ValueError(f"BROAD_CONTRACT_UNKNOWN_CLASSIFICATION:{case['id']}")
        if classification and not isinstance(override.get("reason"), str):
            raise ValueError(f"BROAD_CONTRACT_CLASSIFICATION_REASON_MISSING:{case['id']}")


def metric_summary(outcomes: list[dict[str, Any]]) -> dict[str, Any]:
    """Produce raw and product-ranking metrics with explicit denominators."""
    total = len(outcomes)
    available = [outcome for outcome in outcomes if outcome["target_available"]]
    gaps = [outcome for outcome in outcomes if outcome["classification"] == COVERAGE_GAP]
    ambiguous = [outcome for outcome in outcomes if outcome["classification"] == AMBIGUOUS]
    scorable = [
        outcome
        for outcome in outcomes
        if outcome["target_available"] and outcome["classification"] not in {AMBIGUOUS, COVERAGE_GAP}
    ]

    def rates(items: list[dict[str, Any]]) -> dict[str, float]:
        denominator = len(items)
        return {
            f"hit_rate_at_{cutoff}": round(
                100 * sum(outcome["rank"] is not None and outcome["rank"] <= cutoff for outcome in items) / denominator,
                2,
            ) if denominator else 0.0
            for cutoff in (1, 3, 5)
        }

    return {
        "total_cases": total,
        "available_cases": len(available),
        "coverage_gap_cases": len(gaps),
        "ambiguous_cases": len(ambiguous),
        "coverage_availability_rate": round(100 * len(available) / total, 2) if total else 0.0,
        "raw_all_cases_metrics": {"denominator": total, **rates(outcomes)},
        "scorable_available_metrics": {"denominator": len(scorable), **rates(scorable)},
    }


def domain_metric_summary(outcomes: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Report raw and scorable metrics per domain without hiding excluded cases."""
    grouped: dict[str, list[dict[str, Any]]] = {}
    for outcome in outcomes:
        grouped.setdefault(outcome["domain"], []).append(outcome)
    return {domain: metric_summary(domain_outcomes) for domain, domain_outcomes in sorted(grouped.items())}


def contract_counts(contract: dict[str, Any]) -> dict[str, int]:
    """Expose declared classifications for integrity assertions and reporting."""
    classifications = Counter(override.get("classification") for override in contract["case_overrides"].values())
    return {
        "ambiguous_cases": classifications[AMBIGUOUS],
        "coverage_gap_cases": classifications[COVERAGE_GAP],
    }
