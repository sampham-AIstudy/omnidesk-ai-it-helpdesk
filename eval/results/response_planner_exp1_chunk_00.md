# Response Planner Experiment 1

Generation changed; contexts remained frozen from `baseline_v1_1_context_snapshot.json`.

## Summary

- Judged: 10/10
- Pass/fail: 7/3
- Infra errors: 0
- Latency: {'average_planning_ms': 0.12, 'average_generator_ms': 1016.63, 'average_total_ms': 1604.36, 'extra_llm_calls': 0}

## Scores

- faithfulness: 0.85
- completeness: 0.85
- relevance: 0.95
- correct_abstention: 0.7
- citation_correctness: 1.0

## Failure distribution

| Failure | Count |
| --- | ---: |
| BAD_ABSTENTION | 2 |
| INCOMPLETE_ANSWER | 1 |

## Changed outcomes

| Case | Result | Before | After |
| --- | --- | --- | --- |
| GT-006 | IMPROVED | FAIL | PASS |
| GT-007 | REGRESSED | PASS | FAIL |
| GT-009 | REGRESSED | PASS | FAIL |
| GT-010 | IMPROVED | FAIL | PASS |