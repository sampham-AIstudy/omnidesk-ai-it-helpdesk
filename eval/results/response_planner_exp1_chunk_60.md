# Response Planner Experiment 1

Generation changed; contexts remained frozen from `baseline_v1_1_context_snapshot.json`.

## Summary

- Judged: 10/10
- Pass/fail: 2/8
- Infra errors: 0
- Latency: {'average_planning_ms': 0.15, 'average_generator_ms': 1403.16, 'average_total_ms': 2019.24, 'extra_llm_calls': 0}

## Scores

- faithfulness: 0.45
- completeness: 0.4
- relevance: 0.65
- correct_abstention: 0.4
- citation_correctness: 1.0

## Failure distribution

| Failure | Count |
| --- | ---: |
| UNSUPPORTED_CLAIM | 2 |
| HALLUCINATION | 2 |
| INCOMPLETE_ANSWER | 1 |
| BAD_ABSTENTION | 3 |

## Changed outcomes

| Case | Result | Before | After |
| --- | --- | --- | --- |
| GT-068 | IMPROVED | FAIL | PASS |
| GT-069 | REGRESSED | PASS | FAIL |
| GT-070 | IMPROVED | FAIL | PASS |