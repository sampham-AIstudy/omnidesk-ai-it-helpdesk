"""Read-only A/B measurement of anchor-only versus expanded KB evidence."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.services import bm25_retriever, rag_service  # noqa: E402
from src.services.context_expansion_service import expand_ranked_anchors  # noqa: E402


def _tokens(documents: list[dict[str, Any]]) -> int:
    return sum((len(str(item.get("content") or "")) + 3) // 4 for item in documents)


def _measure(documents: list[dict[str, Any]], case: dict[str, Any]) -> dict[str, float | int]:
    text = "\n".join(str(item.get("content") or "").casefold() for item in documents)
    required = [str(item).casefold() for item in case["required_context_facts"]]
    optional = [str(item).casefold() for item in case["optional_context_facts"]]
    forbidden = [str(item).casefold() for item in case["forbidden_unrelated_context"]]
    required_hits = sum(item in text for item in required)
    relevant = set(required + optional)
    irrelevant_docs = sum(not any(fact in str(item.get("content") or "").casefold() for fact in relevant) for item in documents)
    content_keys = [str((item.get("metadata") or {}).get("content_hash") or item.get("content") or "").casefold() for item in documents]
    return {
        "required_fact_recall": required_hits / len(required) if required else 1.0,
        "context_precision": (len(documents) - irrelevant_docs) / len(documents) if documents else 1.0,
        "irrelevant_context_rate": irrelevant_docs / len(documents) if documents else 0.0,
        "duplicate_context_rate": (len(content_keys) - len(set(content_keys))) / len(content_keys) if content_keys else 0.0,
        "forbidden_context_count": sum(term in text for term in forbidden),
        "evidence_token_cost": _tokens(documents),
    }


def _select_collection(name: str) -> None:
    """Select an evaluator-only collection without changing process configuration."""
    rag_service.settings = rag_service.settings.model_copy(update={"chroma_collection_name": name})
    rag_service._collection = None
    rag_service._rag_query_cache.clear()
    bm25_retriever.invalidate_bm25_index()


def evaluate(dataset: dict[str, Any], *, collection: str | None = None) -> dict[str, Any]:
    if collection:
        _select_collection(collection)
    rows: list[dict[str, Any]] = []
    for case in dataset["cases"]:
        anchors = rag_service.search_similar(case["query"], n_results=3, use_reranker=False)
        expanded, metrics = expand_ranked_anchors(case["query"], anchors)
        rows.append({
            "id": case["id"],
            "expected_anchor": case["anchor_expected_source"],
            "anchor_ids": [str(item.get("doc_id")) for item in anchors],
            "expanded_ids": [str(item.get("doc_id")) for item in expanded],
            "anchor_only": _measure(anchors, case),
            "expanded": _measure(expanded, case),
            "expansion": {
                "neighbor_count": metrics.expanded_neighbor_count,
                "parent_count": metrics.expanded_parent_count,
                "dropped_neighbor_count": metrics.dropped_neighbor_count,
                "expansion_token_cost": metrics.neighbor_tokens + metrics.parent_tokens,
            },
        })

    def summary(key: str) -> dict[str, float]:
        measures = [row[key] for row in rows]
        return {
            metric: sum(float(item[metric]) for item in measures) / len(measures)
            for metric in ("required_fact_recall", "context_precision", "irrelevant_context_rate", "duplicate_context_rate", "evidence_token_cost")
        }

    return {
        "collection": collection or rag_service.settings.chroma_collection_name,
        "case_count": len(rows),
        "anchor_only": summary("anchor_only"),
        "expanded": summary("expanded"),
        "cases": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=ROOT / "eval" / "context_completeness_v1.json")
    parser.add_argument("--collection", help="Evaluator-only Chroma collection override")
    args = parser.parse_args()
    print(json.dumps(evaluate(json.loads(args.dataset.read_text(encoding="utf-8")), collection=args.collection), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
