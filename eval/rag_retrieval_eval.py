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

    for case in cases:
        retrieved = search_similar(
            query=case["query"],
            category_filter=case.get("category"),
            n_results=top_k,
        )
        titles = [item.get("metadata", {}).get("title", "") for item in retrieved]
        expected = case["expected_title"].casefold()
        rank = next(
            (index for index, title in enumerate(titles, start=1) if expected in title.casefold()),
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
        "mrr": reciprocal_rank_sum / count if count else 0.0,
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
        f"- MRR: {report['mrr']:.3f}",
        "",
        "| Query | Expected | Rank |",
        "|---|---|---:|",
    ]
    for item in report["results"]:
        rank = item["rank"] if item["rank"] is not None else "miss"
        lines.append(f"| {item['query']} | {item['expected_title']} | {rank} |")
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
