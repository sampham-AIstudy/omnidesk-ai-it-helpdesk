"""Evaluate V3 and V4 against the versioned Broad Coverage V4 contract."""
from __future__ import annotations

import importlib
import json
import logging
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

bm25 = importlib.import_module("src.services.bm25_retriever")
rag = importlib.import_module("src.services.rag_service")
contract_helpers = importlib.import_module("eval.broad_coverage_contract")
matching = importlib.import_module("eval.v4_eval_matching")
COVERAGE_GAP = contract_helpers.COVERAGE_GAP
case_override = contract_helpers.case_override
case_classifications = contract_helpers.case_classifications
domain_metric_summary = contract_helpers.domain_metric_summary
load_contract = contract_helpers.load_contract
metric_summary = contract_helpers.metric_summary
target_doc_ids = contract_helpers.target_doc_ids
validate_contract = contract_helpers.validate_contract
doc_canonical_aliases = matching.doc_canonical_aliases
doc_matches_targets = matching.doc_matches_targets
targets_canonical_aliases = matching.targets_canonical_aliases

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("eval_v4_coverage")

DATASET_PATH = Path("eval/broad_coverage_v4.json")
OUT_PATH = Path("eval/results/broad_coverage_v4_benchmark.json")
V3_COLLECTION = "helpdesk_kb_multilingual_v3_sentence_transformer"
V4_COLLECTION = "helpdesk_kb_multilingual_v4_shadow"


def activate_collection(collection_name: str) -> Any:
    """Switch evaluator state and invalidate the collection-bound BM25 cache."""
    target = rag.get_chroma_client().get_collection(collection_name)
    rag._collection = target
    rag._rag_query_cache.clear()
    bm25.invalidate_bm25_index()
    return target


def collection_aliases(collection: Any) -> set[str]:
    """Build canonical source aliases from the collection being evaluated."""
    data = collection.get(include=["metadatas"])
    aliases: set[str] = set()
    for doc_id, metadata in zip(data.get("ids", []), data.get("metadatas", []), strict=True):
        aliases |= doc_canonical_aliases({"doc_id": doc_id, "metadata": metadata})
    return aliases


def evaluate_dataset(collection_name: str, dataset: list[dict[str, Any]], contract: dict[str, Any]) -> dict[str, Any]:
    """Evaluate one collection with raw and availability-aware scoring views."""
    target_collection = activate_collection(collection_name)
    aliases_in_collection = collection_aliases(target_collection)
    outcomes: list[dict[str, Any]] = []
    start = time.perf_counter()

    for item in dataset:
        targets = target_doc_ids(item, contract)
        target_aliases = targets_canonical_aliases(targets)
        classification = case_override(contract, item["id"]).get("classification")
        classifications = case_classifications(contract, item["id"])
        target_available = bool(target_aliases & aliases_in_collection)
        if COVERAGE_GAP in classifications and target_available:
            raise ValueError(f"BROAD_CONTRACT_COVERAGE_GAP_IS_AVAILABLE:{item['id']}")

        results = rag.search_similar(query=item["query"], n_results=5)
        rank = next(
            (index for index, result in enumerate(results, start=1) if doc_matches_targets(result, target_aliases)),
            None,
        )
        outcomes.append(
            {
                "case_id": item["id"],
                "domain": item["domain"],
                "query": item["query"],
                "target_doc_ids": targets,
                "classification": classification,
                "classifications": sorted(classifications),
                "target_available": target_available,
                "rank": rank,
                "top5_doc_ids": [result["doc_id"] for result in results],
            }
        )

    summary = metric_summary(outcomes)
    elapsed = time.perf_counter() - start
    return {
        "collection": collection_name,
        **summary,
        "per_domain": domain_metric_summary(outcomes),
        "latency_per_query_ms": round(1000 * elapsed / len(dataset), 2),
        "total_time_s": round(elapsed, 2),
        "outcomes": outcomes,
    }


def compact_summary(result: dict[str, Any]) -> dict[str, Any]:
    """Keep terminal output concise while retaining full case outcomes in JSON."""
    return {key: value for key, value in result.items() if key != "outcomes"}


def main() -> None:
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    contract = load_contract()
    validate_contract(dataset, contract)
    logger.info("Loaded %d broad-coverage cases under contract v%s", len(dataset), contract["schema_version"])

    logger.info("Benchmarking V3 production collection (%s)", V3_COLLECTION)
    v3_result = evaluate_dataset(V3_COLLECTION, dataset, contract)
    logger.info("Benchmarking V4 shadow collection (%s)", V4_COLLECTION)
    v4_result = evaluate_dataset(V4_COLLECTION, dataset, contract)

    report = {
        "benchmark": "Broad Coverage V4",
        "contract_version": contract["schema_version"],
        "contract": contract["scoring_contract"],
        "v3_production": v3_result,
        "v4_shadow": v4_result,
        "delta_raw_all_cases": {
            f"hit_rate_at_{cutoff}_gain": round(
                v4_result["raw_all_cases_metrics"][f"hit_rate_at_{cutoff}"]
                - v3_result["raw_all_cases_metrics"][f"hit_rate_at_{cutoff}"],
                2,
            )
            for cutoff in (1, 3, 5)
        },
        "evaluated_at": datetime.now(UTC).isoformat(),
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Broad Coverage Benchmark Report saved to %s", OUT_PATH)
    print(json.dumps({"v3_production": compact_summary(v3_result), "v4_shadow": compact_summary(v4_result)}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
