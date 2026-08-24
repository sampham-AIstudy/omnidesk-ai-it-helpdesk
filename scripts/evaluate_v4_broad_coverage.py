import json
import logging
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path('.').resolve()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import src.services.bm25_retriever as bm25
import src.services.rag_service as rag
from eval.v4_eval_matching import doc_matches_targets, targets_canonical_aliases

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('eval_v4_coverage')


def evaluate_dataset(collection_name: str, dataset: list[dict]) -> dict:
    client = rag.get_chroma_client()
    target_col = client.get_collection(collection_name)
    rag._collection = target_col
    rag._rag_query_cache.clear()
    # The BM25 index is bound to the active RAG collection.  Invalidate the
    # real cache before switching from V3 to V4 so channels cannot mix.
    bm25.invalidate_bm25_index()

    hits_at_1 = 0
    hits_at_3 = 0
    hits_at_5 = 0
    total = len(dataset)
    start_t = time.perf_counter()

    for item in dataset:
        q = item['query']
        target_aliases = targets_canonical_aliases(item['expected_doc_ids'])

        results = rag.search_similar(query=q, n_results=5)

        if results and doc_matches_targets(results[0], target_aliases):
            hits_at_1 += 1
        if any(doc_matches_targets(r, target_aliases) for r in results[:3]):
            hits_at_3 += 1
        if any(doc_matches_targets(r, target_aliases) for r in results[:5]):
            hits_at_5 += 1

    elapsed = time.perf_counter() - start_t
    return {
        'collection': collection_name,
        'total_cases': total,
        'hit_rate_at_1': round(hits_at_1 / total * 100, 2),
        'hit_rate_at_3': round(hits_at_3 / total * 100, 2),
        'hit_rate_at_5': round(hits_at_5 / total * 100, 2),
        'latency_per_query_ms': round((elapsed / total) * 1000, 2),
        'total_time_s': round(elapsed, 2),
    }


def main():
    ds_file = Path('eval/broad_coverage_v4.json')
    dataset = json.loads(ds_file.read_text(encoding='utf-8'))
    logger.info('Loaded %d cases for broad coverage benchmark', len(dataset))

    logger.info('Benchmarking V3 Production Collection (helpdesk_kb_multilingual_v3_sentence_transformer)...')
    v3_res = evaluate_dataset('helpdesk_kb_multilingual_v3_sentence_transformer', dataset)
    logger.info('V3 Results: %s', v3_res)

    logger.info('Benchmarking V4 Shadow Collection (helpdesk_kb_multilingual_v4_shadow)...')
    v4_res = evaluate_dataset('helpdesk_kb_multilingual_v4_shadow', dataset)
    logger.info('V4 Results: %s', v4_res)

    report = {
        'benchmark': 'Broad Coverage V4 (350 queries across 8 domains)',
        'v3_production': v3_res,
        'v4_shadow': v4_res,
        'delta': {
            'hit_rate_at_1_gain': round(v4_res['hit_rate_at_1'] - v3_res['hit_rate_at_1'], 2),
            'hit_rate_at_3_gain': round(v4_res['hit_rate_at_3'] - v3_res['hit_rate_at_3'], 2),
            'hit_rate_at_5_gain': round(v4_res['hit_rate_at_5'] - v3_res['hit_rate_at_5'], 2),
        },
        'evaluated_at': datetime.now(UTC).isoformat(),
    }

    out_file = Path('eval/results/broad_coverage_v4_benchmark.json')
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    logger.info('Broad Coverage Benchmark Report saved to %s', out_file)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
