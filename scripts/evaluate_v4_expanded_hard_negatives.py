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
from eval.v4_eval_matching import (
    doc_canonical_aliases,
    doc_matches_targets,
    targets_canonical_aliases,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('eval_v4_hn')


def evaluate_hn_dataset(collection_name: str, dataset: list[dict]) -> dict:
    client = rag.get_chroma_client()
    target_col = client.get_collection(collection_name)
    rag._collection = target_col
    rag._rag_query_cache.clear()
    # The BM25 index is bound to the active RAG collection.  Invalidate the
    # real cache before switching from V3 to V4 so channels cannot mix.
    bm25.invalidate_bm25_index()

    # Collect all available document alias keys in the collection
    all_col_aliases: set[str] = set()
    col_data = target_col.get(include=['metadatas'])
    for d_id, meta in zip(col_data.get('ids', []), col_data.get('metadatas', [])):
        all_col_aliases |= doc_canonical_aliases({'doc_id': d_id, 'metadata': meta})

    total = len(dataset)
    target_available = 0
    target_missing = 0

    rank1_target_only = 0
    rank1_hard_negative_only = 0
    rank1_both = 0
    rank1_neither = 0

    target_hit_top3_count = 0
    hn_in_top3_count = 0
    hn_before_target_count = 0
    target_missing_with_negative_top3_count = 0

    start_t = time.perf_counter()

    for item in dataset:
        q = item['query']
        exp_ids = item['primary_expected_source_ids']
        neg_ids = item['hard_negative_source_ids']

        target_aliases = targets_canonical_aliases(exp_ids)
        neg_aliases = targets_canonical_aliases(neg_ids)

        # Sanity check: expected and negative sets must not overlap
        assert not (target_aliases & neg_aliases), f"Overlapping aliases in case {item['id']}"

        has_target_in_col = bool(target_aliases & all_col_aliases)
        if has_target_in_col:
            target_available += 1
        else:
            target_missing += 1

        results = rag.search_similar(query=q, n_results=5)
        r1 = results[0] if results else None

        r1_is_target = doc_matches_targets(r1, target_aliases) if r1 else False
        r1_is_hn = doc_matches_targets(r1, neg_aliases) if r1 else False

        if r1_is_target and r1_is_hn:
            rank1_both += 1
        elif r1_is_target:
            rank1_target_only += 1
        elif r1_is_hn:
            rank1_hard_negative_only += 1
        else:
            rank1_neither += 1

        if any(doc_matches_targets(r, target_aliases) for r in results[:3]):
            target_hit_top3_count += 1

        has_hn_top3 = any(doc_matches_targets(r, neg_aliases) for r in results[:3])
        if has_hn_top3:
            hn_in_top3_count += 1

        target_rank = next((idx for idx, r in enumerate(results) if doc_matches_targets(r, target_aliases)), None)
        hn_rank = next((idx for idx, r in enumerate(results) if doc_matches_targets(r, neg_aliases)), None)

        if hn_rank is not None and (target_rank is None or hn_rank < target_rank):
            hn_before_target_count += 1

        if not has_target_in_col and has_hn_top3:
            target_missing_with_negative_top3_count += 1

    elapsed = time.perf_counter() - start_t

    # Invariant: rank1 confusion matrix must total exactly total cases
    assert rank1_target_only + rank1_hard_negative_only + rank1_both + rank1_neither == total
    assert rank1_both == 0, f"Spurious target/negative overlap in {collection_name}"

    return {
        'collection': collection_name,
        'total_cases': total,
        'target_available_cases': target_available,
        'target_missing_cases': target_missing,
        'target_hit_at_1': round(rank1_target_only / total * 100, 2),
        'target_hit_at_3': round(target_hit_top3_count / total * 100, 2),
        'rank1_target_only': rank1_target_only,
        'rank1_hard_negative_only': rank1_hard_negative_only,
        'rank1_both': rank1_both,
        'rank1_neither': rank1_neither,
        'hard_negative_at_1_rate': round(rank1_hard_negative_only / total * 100, 2),
        'hard_negative_before_target_rate': round(hn_before_target_count / total * 100, 2),
        'hard_negative_in_top3_rate': round(hn_in_top3_count / total * 100, 2),
        'target_missing_with_negative_top3_rate': round(target_missing_with_negative_top3_count / total * 100, 2),
        'latency_per_query_ms': round((elapsed / total) * 1000, 2),
        'total_time_s': round(elapsed, 2),
    }


def print_summary_table(v3_res: dict, v4_res: dict) -> None:
    print("\n=================================================================")
    print("EXPANDED HARD-NEGATIVE BENCHMARK SUMMARY (100 CROSS-DOMAIN CASES)")
    print("=================================================================")
    print(f"{'Metric':<38} | {'V3 Production':<13} | {'V4 Shadow':<13} | {'Delta':<10}")
    print("-" * 80)
    print(f"{'Total Cases':<38} | {v3_res['total_cases']:<13} | {v4_res['total_cases']:<13} | -")
    print(f"{'Target Available Cases':<38} | {v3_res['target_available_cases']:<13} | {v4_res['target_available_cases']:<13} | +{v4_res['target_available_cases'] - v3_res['target_available_cases']}")
    print(f"{'Target Missing Cases':<38} | {v3_res['target_missing_cases']:<13} | {v4_res['target_missing_cases']:<13} | {v4_res['target_missing_cases'] - v3_res['target_missing_cases']}")
    print(f"{'Target Hit@1':<38} | {v3_res['target_hit_at_1']:>5.1f}% ({v3_res['rank1_target_only']:>2})  | {v4_res['target_hit_at_1']:>5.1f}% ({v4_res['rank1_target_only']:>2})  | {v4_res['target_hit_at_1'] - v3_res['target_hit_at_1']:>+5.1f} pp")
    print(f"{'Target Hit@3':<38} | {v3_res['target_hit_at_3']:>5.1f}%        | {v4_res['target_hit_at_3']:>5.1f}%        | {v4_res['target_hit_at_3'] - v3_res['target_hit_at_3']:>+5.1f} pp")
    print(f"{'Rank-1 Hard Negative Only':<38} | {v3_res['hard_negative_at_1_rate']:>5.1f}% ({v3_res['rank1_hard_negative_only']:>2})  | {v4_res['hard_negative_at_1_rate']:>5.1f}% ({v4_res['rank1_hard_negative_only']:>2})  | {v4_res['hard_negative_at_1_rate'] - v3_res['hard_negative_at_1_rate']:>+5.1f} pp")
    print(f"{'Rank-1 Both (Overlapping Bug)':<38} | {v3_res['rank1_both']:>5}         | {v4_res['rank1_both']:>5}         | 0")
    print(f"{'Rank-1 Neither (Neutral / Distant)':<38} | {v3_res['rank1_neither']:>5}         | {v4_res['rank1_neither']:>5}         | {v4_res['rank1_neither'] - v3_res['rank1_neither']:>+5}")
    print(f"{'Hard Negative Before Target':<38} | {v3_res['hard_negative_before_target_rate']:>5.1f}%        | {v4_res['hard_negative_before_target_rate']:>5.1f}%        | {v4_res['hard_negative_before_target_rate'] - v3_res['hard_negative_before_target_rate']:>+5.1f} pp")
    print(f"{'Hard Negative in Top-3':<38} | {v3_res['hard_negative_in_top3_rate']:>5.1f}%        | {v4_res['hard_negative_in_top3_rate']:>5.1f}%        | {v4_res['hard_negative_in_top3_rate'] - v3_res['hard_negative_in_top3_rate']:>+5.1f} pp")
    print(f"{'Target Missing w/ HN in Top-3':<38} | {v3_res['target_missing_with_negative_top3_rate']:>5.1f}%        | {v4_res['target_missing_with_negative_top3_rate']:>5.1f}%        | {v4_res['target_missing_with_negative_top3_rate'] - v3_res['target_missing_with_negative_top3_rate']:>+5.1f} pp")
    print("=================================================================\n")


def main():
    ds_file = Path('eval/expanded_hard_negatives_v4.json')
    dataset = json.loads(ds_file.read_text(encoding='utf-8'))
    logger.info('Loaded %d cases for expanded hard negatives benchmark', len(dataset))

    logger.info('Benchmarking V3 Production Collection...')
    v3_res = evaluate_hn_dataset('helpdesk_kb_multilingual_v3_sentence_transformer', dataset)

    logger.info('Benchmarking V4 Shadow Collection...')
    v4_res = evaluate_hn_dataset('helpdesk_kb_multilingual_v4_shadow', dataset)

    print_summary_table(v3_res, v4_res)

    report = {
        'benchmark': 'Expanded Hard Negatives V4 (100 cross-domain cases)',
        'v3_production': v3_res,
        'v4_shadow': v4_res,
        'delta': {
            'target_hit_rate_at_1_gain': round(v4_res['target_hit_at_1'] - v3_res['target_hit_at_1'], 2),
            'target_hit_rate_at_3_gain': round(v4_res['target_hit_at_3'] - v3_res['target_hit_at_3'], 2),
            'hard_negative_at_1_reduction': round(v3_res['hard_negative_at_1_rate'] - v4_res['hard_negative_at_1_rate'], 2),
            'hard_negative_before_target_reduction': round(v3_res['hard_negative_before_target_rate'] - v4_res['hard_negative_before_target_rate'], 2),
        },
        'evaluated_at': datetime.now(UTC).isoformat(),
    }

    out_file = Path('eval/results/expanded_hard_negatives_v4_benchmark.json')
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    logger.info('Expanded Hard Negatives Report saved to %s', out_file)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
