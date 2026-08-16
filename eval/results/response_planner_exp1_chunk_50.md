# Response Planner Experiment 1

Generation changed; contexts remained frozen from `baseline_v1_1_context_snapshot.json`.

## Summary

- Judged: 10/10
- Pass/fail: 7/3
- Infra errors: 0
- Latency: {'average_planning_ms': 0.12, 'average_generator_ms': 367.95, 'average_total_ms': 978.77, 'extra_llm_calls': 0}

## Scores

- faithfulness: 0.7
- completeness: 0.7
- relevance: 0.9
- correct_abstention: 0.7
- citation_correctness: 1.0

## Failure distribution

| Failure | Count |
| --- | ---: |
| INCOMPLETE_ANSWER | 1 |
| BAD_ABSTENTION | 1 |
| UNSUPPORTED_CLAIM | 1 |

## Changed outcomes

| Case | Result | Before | After |
| --- | --- | --- | --- |
| GT-053 | IMPROVED | FAIL | PASS |
| GT-056 | IMPROVED | FAIL | PASS |