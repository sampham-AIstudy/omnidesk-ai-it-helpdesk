# Response Planner Experiment 1

Generation changed; contexts remained frozen from `baseline_v1_1_context_snapshot.json`.

## Summary

- Judged: 10/10
- Pass/fail: 3/7
- Infra errors: 0
- Latency: {'average_planning_ms': 0.13, 'average_generator_ms': 2073.36, 'average_total_ms': 2675.72, 'extra_llm_calls': 0}

## Scores

- faithfulness: 0.55
- completeness: 0.5
- relevance: 0.8
- correct_abstention: 0.3
- citation_correctness: 1.0

## Failure distribution

| Failure | Count |
| --- | ---: |
| BAD_ABSTENTION | 5 |
| INCOMPLETE_ANSWER | 1 |
| UNSUPPORTED_CLAIM | 1 |

## Changed outcomes

| Case | Result | Before | After |
| --- | --- | --- | --- |
| GT-022 | REGRESSED | PASS | FAIL |
| GT-023 | IMPROVED | FAIL | PASS |
| GT-030 | REGRESSED | PASS | FAIL |