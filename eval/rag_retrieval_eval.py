"""Offline retrieval benchmark for the configured help-desk RAG collection."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_settings
from src.services.rag_service import get_collection_count, search_similar


def evaluate(cases: list[dict], top_k: int = 3) -> dict:
    results = []
    reciprocal_rank_sum = 0.0
    hit_at_1 = 0
    hit_at_k = 0
    relevant_retrieved = 0
    retrieved_total = 0
    duplicate_retrieved = 0

    for case in cases:
        retrieved = search_similar(
            query=case["query"],
            category_filter=case.get("category"),
            n_results=top_k,
        )
        titles = [str(item.get("metadata", {}).get("title", "")) for item in retrieved]
        expected_titles = case.get("expected_titles") or [case["expected_title"]]
        expected = [title.casefold() for title in expected_titles]
        expected_source_ids = {str(source_id) for source_id in case.get("expected_source_ids", [])}
        minimum_relevance = float(case.get("minimum_relevance", 0.0))
        relevant = [
            item
            for item in retrieved
            if (
                any(expected_title in str(item.get("metadata", {}).get("title", "")).casefold() for expected_title in expected)
                or str(item.get("doc_id", "")) in expected_source_ids
            ) and float(item.get("relevance_score", 1.0)) >= minimum_relevance
        ]
        source_keys = [
            str(item.get("doc_id") or item.get("metadata", {}).get("title", "")).casefold().strip()
            for item in retrieved
        ]
        duplicates = len(source_keys) - len({key for key in source_keys if key})
        relevant_retrieved += len(relevant)
        retrieved_total += len(retrieved)
        duplicate_retrieved += duplicates
        rank = next(
            (index for index, item in enumerate(retrieved, start=1) if item in relevant),
            None,
        )
        if rank == 1:
            hit_at_1 += 1
        if rank is not None:
            hit_at_k += 1
            reciprocal_rank_sum += 1.0 / rank
        results.append(
            {
                **case,
                "rank": rank,
                "passed": rank is not None,
                "retrieved_titles": titles,
                "source_relevance": len(relevant) / len(retrieved) if retrieved else 0.0,
                "noise_rate": (len(retrieved) - len(relevant)) / len(retrieved) if retrieved else 0.0,
                "duplicate_source_rate": duplicates / len(retrieved) if retrieved else 0.0,
            }
        )

    count = len(cases)
    settings = get_settings()
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "collection": settings.chroma_collection_name,
        "embedding_model": settings.embedding_model,
        "collection_count": get_collection_count(),
        "case_count": count,
        "hit_at_1": hit_at_1 / count if count else 0.0,
        f"hit_at_{top_k}": hit_at_k / count if count else 0.0,
        f"recall_at_{top_k}": hit_at_k / count if count else 0.0,
        "mrr": reciprocal_rank_sum / count if count else 0.0,
        "source_relevance": relevant_retrieved / retrieved_total if retrieved_total else 0.0,
        "noise_rate": (retrieved_total - relevant_retrieved) / retrieved_total if retrieved_total else 0.0,
        "duplicate_source_rate": duplicate_retrieved / retrieved_total if retrieved_total else 0.0,
        "results": results,
    }


def markdown_report(report: dict, top_k: int) -> str:
    lines = [
        "# RAG Retrieval Evaluation",
        "",
        f"- Collection: `{report['collection']}`",
        f"- Embedding model: `{report['embedding_model']}`",
        f"- Documents: {report['collection_count']}",
        f"- Cases: {report['case_count']}",
        f"- Hit@1: {report['hit_at_1']:.1%}",
        f"- Hit@{top_k}: {report[f'hit_at_{top_k}']:.1%}",
        f"- Recall@{top_k}: {report[f'recall_at_{top_k}']:.1%}",
        f"- MRR: {report['mrr']:.3f}",
        f"- Source relevance: {report['source_relevance']:.1%}",
        f"- Noise rate: {report['noise_rate']:.1%}",
        f"- Duplicate source rate: {report['duplicate_source_rate']:.1%}",
        "",
        "| Query | Expected | Rank | Relevance | Noise | Duplicates |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for item in report["results"]:
        rank = item["rank"] if item["rank"] is not None else "miss"
        expected = ", ".join(item.get("expected_titles") or [item["expected_title"]])
        lines.append(
            f"| {item['query']} | {expected} | {rank} | {item['source_relevance']:.0%} | "
            f"{item['noise_rate']:.0%} | {item['duplicate_source_rate']:.0%} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Đánh giá retrieval của Help Desk RAG")
    parser.add_argument(
        "--cases", type=Path, default=Path("eval/rag_retrieval_cases.json")
    )
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--minimum-hit-rate", type=float, default=0.8)
    parser.add_argument(
        "--output-json", type=Path, default=Path("eval/results/rag_retrieval_report.json")
    )
    parser.add_argument(
        "--output-md", type=Path, default=Path("eval/results/rag_retrieval_report.md")
    )
    args = parser.parse_args()

    cases = json.loads(args.cases.read_text(encoding="utf-8"))
    report = evaluate(cases, top_k=args.top_k)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    args.output_md.write_text(markdown_report(report, args.top_k), encoding="utf-8")

    hit_rate = report[f"hit_at_{args.top_k}"]
    print(
        f"Hit@1={report['hit_at_1']:.1%} Hit@{args.top_k}={hit_rate:.1%} "
        f"MRR={report['mrr']:.3f}"
    )
    return 0 if hit_rate >= args.minimum_hit_rate else 1


if __name__ == "__main__":
    raise SystemExit(main())
