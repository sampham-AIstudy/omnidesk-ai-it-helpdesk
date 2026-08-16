# Response Planner Experiment 1

Generation changed; contexts remained frozen from `baseline_v1_1_context_snapshot.json`.

## Summary

- Judged: 10/10
- Pass/fail: 9/1
- Infra errors: 0
- Latency: {'average_planning_ms': 0.1, 'average_generator_ms': 171.19, 'average_total_ms': 746.79, 'extra_llm_calls': 0}

## Scores

- faithfulness: 0.95
- completeness: 0.95
- relevance: 1.0
- correct_abstention: 1.0
- citation_correctness: 1.0

## Failure distribution

| Failure | Count |
| --- | ---: |
| INCOMPLETE_ANSWER | 1 |

## Changed outcomes

| Case | Result | Before | After |
| --- | --- | --- | --- |
| GT-012 | IMPROVED | FAIL | PASS |
| GT-013 | IMPROVED | FAIL | PASS |
| GT-014 | IMPROVED | FAIL | PASS |
| GT-015 | IMPROVED | FAIL | PASS |
| GT-020 | REGRESSED | PASS | FAIL |