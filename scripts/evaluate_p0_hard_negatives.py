"""Read-only hard-negative A/B evaluation for the P0 shadow knowledge batch."""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.evaluate_p0_shadow_kb import _select_collection  # noqa: E402
from src.services import rag_service  # noqa: E402
from src.services.technical_intent_service import infer_technical_facets  # noqa: E402


def _rank(ids: list[str], expected: set[str]) -> int | None:
    return next((index + 1 for index, value in enumerate(ids) if value in expected), None)


def _metrics(rows: list[dict[str, Any]]) -> dict[str, float | int]:
    total = len(rows)
    ranks = [row["primary_rank"] for row in rows]
    return {
        "cases": total,
        "hit_rate_at_1": sum(rank == 1 for rank in ranks) / total if total else 0.0,
        "hit_rate_at_3": sum(rank is not None and rank <= 3 for rank in ranks) / total if total else 0.0,
        "hit_rate_at_5": sum(rank is not None and rank <= 5 for rank in ranks) / total if total else 0.0,
        "recall_at_1": sum(rank == 1 for rank in ranks) / total if total else 0.0,
        "recall_at_3": sum(rank is not None and rank <= 3 for rank in ranks) / total if total else 0.0,
        "recall_at_5": sum(rank is not None and rank <= 5 for rank in ranks) / total if total else 0.0,
        "mrr_at_5": sum(1.0 / rank for rank in ranks if rank is not None) / total if total else 0.0,
        "ndcg_at_5": sum(1.0 / math.log2(rank + 1) for rank in ranks if rank is not None) / total if total else 0.0,
        "hard_negative_at_1_rate": sum(row["hard_negative_at_1"] for row in rows) / total if total else 0.0,
        "hard_negative_in_top3_rate": sum(row["hard_negative_in_top3"] for row in rows) / total if total else 0.0,
        "intent_confusion_rate": sum(row["intent_confusion"] for row in rows) / total if total else 0.0,
    }


def _evidence(document: dict[str, Any] | None) -> dict[str, Any] | None:
    if document is None:
        return None
    metadata = document.get("metadata", {}) or {}
    source = metadata.get("source", "NO_SOURCE_KEY")
    return {
        "doc_id": document.get("doc_id"), "topic": metadata.get("topic"),
        "title": metadata.get("title"), "source": source,
        "authority_factor": rag_service.SOURCE_AUTHORITY_FACTORS.get(source, 1.0),
        "semantic_score": document.get("semantic_score"), "dense_rank": document.get("dense_rank"),
        "lexical_rank": document.get("lexical_rank"), "fusion_score": document.get("fusion_score"),
        "relevance_score": document.get("relevance_score"),
        "dense_rrf": document.get("dense_rrf"), "lexical_rrf": document.get("lexical_rrf"),
        "exact_contribution": document.get("exact_contribution"), "rrf_score": document.get("rrf_score"),
        "topic_compatibility": document.get("topic_compatibility"),
        "topic_compatibility_reason": document.get("topic_compatibility_reason"),
        "topic_adjusted_score": document.get("topic_adjusted_score"), "final_score": document.get("final_score"),
    }


def _failure_cause(row: dict[str, Any], expected_exists: bool) -> str | None:
    if row["primary_rank"] == 1:
        return None
    if not expected_exists:
        return "MISSING_KNOWLEDGE"
    if row["hard_negative_at_1"]:
        top = row["rank1"] or {}
        expected = row["expected_retrieved"] or {}
        if top.get("lexical_rank") and (not expected.get("lexical_rank") or top["lexical_rank"] < expected["lexical_rank"]):
            return "LEXICAL_COLLISION"
        return "SEMANTIC_COLLISION"
    top = row["rank1"] or {}
    expected = row["expected_retrieved"] or {}
    if (
        top.get("source") == "internal_curated_kb"
        and expected.get("source") == "official_web_documentation"
        and top.get("topic_compatibility", 0.0) > 1.0
    ):
        return "AUTHORITY_CONFLICT"
    if top.get("topic_compatibility_reason") == "no_high_confidence_technical_intent":
        return "INSUFFICIENT_DISAMBIGUATION"
    if row["primary_rank"] is None:
        return "QUERY_UNDERSTANDING"
    return "SEMANTIC_COLLISION"


def evaluate_collection(collection: str, cases: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Evaluate strict primary intent placement without modifying the collection."""
    _select_collection(collection)
    chroma = rag_service.get_collection()
    expected_ids = sorted({item for case in cases for item in case["expected_source_ids"]})
    expected_records = chroma.get(ids=expected_ids, include=["metadatas"])
    existing_expected = set(expected_records.get("ids", []))
    expected_metadata = dict(zip(expected_records.get("ids", []), expected_records.get("metadatas", [])))
    rows = []
    for case in cases:
        docs = rag_service.search_similar(case["query"], n_results=5, use_reranker=False)
        ids = [str(doc.get("doc_id")) for doc in docs]
        expected = set(case["expected_source_ids"])
        hard_ids = set(case["hard_negative_source_ids"])
        hard_topics = set(case["hard_negative_topics"])
        primary_rank = _rank(ids, expected)
        hard_at_1 = bool(docs) and (
            ids[0] in hard_ids or (docs[0].get("metadata", {}) or {}).get("topic") in hard_topics
        )
        hard_top3 = any(
            doc.get("doc_id") in hard_ids or (doc.get("metadata", {}) or {}).get("topic") in hard_topics
            for doc in docs[:3]
        )
        expected_doc = next((doc for doc in docs if doc.get("doc_id") in expected), None)
        row = {
            "id": case["id"], "category": case["category"], "query": case["query"],
            "technical_facets": infer_technical_facets(case["query"]).public_dict(),
            "primary_expected_source_ids": case["expected_source_ids"],
            "primary_expected_canonical_source_id": [
                (expected_metadata.get(item) or {}).get("canonical_source_id")
                for item in case["expected_source_ids"]
            ],
            "acceptable_supporting_source_ids": case["acceptable_source_ids"],
            "hard_negative_source_ids": case["hard_negative_source_ids"],
            "hard_negative_topics": case["hard_negative_topics"],
            "primary_rank": primary_rank, "retrieved_ids": ids,
            "hard_negative_at_1": hard_at_1, "hard_negative_in_top3": hard_top3,
            "intent_confusion": hard_at_1,
            "rank1": _evidence(docs[0] if docs else None),
            "expected_retrieved": _evidence(expected_doc),
            "hard_negative_retrieved": [_evidence(doc) for doc in docs if doc.get("doc_id") in hard_ids or (doc.get("metadata", {}) or {}).get("topic") in hard_topics],
        }
        row["failure_cause"] = _failure_cause(row, bool(expected & existing_expected))
        rows.append(row)
    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_category[row["category"]].append(row)
    return rows, {"overall": _metrics(rows), "by_category": {key: _metrics(value) for key, value in sorted(by_category.items())}}


def provenance_check(shadow: str, cases: list[dict[str, Any]]) -> dict[str, Any]:
    _select_collection(shadow)
    collection = rag_service.get_collection()
    all_records = collection.get(include=["metadatas"])
    ids = [item for item in all_records.get("ids", []) if str(item).startswith("p0-")]
    metadata_by_id = dict(zip(all_records.get("ids", []), all_records.get("metadatas", [])))
    required = {"canonical_source_id", "source_id", "source_type", "source_url", "content_hash", "topic"}
    invalid = []
    for item_id in ids:
        metadata = metadata_by_id.get(item_id)
        missing = sorted(key for key in required if not (metadata or {}).get(key))
        if missing:
            invalid.append({"doc_id": item_id, "missing": missing})
    return {"expected_p0_chunks": 10, "found_p0_chunks": len(ids), "invalid": invalid,
            "complete": len(ids) == 10 and not invalid}


def run_ab(*, canonical: str, shadow: str, cases_path: Path, output_path: Path) -> dict[str, Any]:
    cases = json.loads(cases_path.read_text(encoding="utf-8"))["cases"]
    v2_rows, v2 = evaluate_collection(canonical, cases)
    v3_rows, v3 = evaluate_collection(shadow, cases)
    report = {"canonical_collection": canonical, "shadow_collection": shadow, "dataset": str(cases_path),
              "case_count": len(cases), "v2": {"metrics": v2, "cases": v2_rows},
              "v3": {"metrics": v3, "cases": v3_rows}, "source_provenance": provenance_check(shadow, cases)}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical", default="helpdesk_kb_multilingual_v2_sentence_transformer")
    parser.add_argument("--shadow", default="helpdesk_kb_multilingual_v3_shadow")
    parser.add_argument("--cases", type=Path, default=ROOT / "eval" / "p0_shadow_v3_hard_negative_cases.json")
    parser.add_argument("--output", type=Path, default=ROOT / "eval" / "results" / "p0_shadow_v3_hard_negative_ab.json")
    args = parser.parse_args()
    print(json.dumps(run_ab(canonical=args.canonical, shadow=args.shadow, cases_path=args.cases, output_path=args.output), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
