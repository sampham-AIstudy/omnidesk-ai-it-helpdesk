# Response Planner Experiment 1

Generation changed; contexts remained frozen from `baseline_v1_1_context_snapshot.json`.

## Summary

- Judged: 10/10
- Pass/fail: 2/8
- Infra errors: 0
- Latency: {'average_planning_ms': 0.13, 'average_generator_ms': 1099.38, 'average_total_ms': 1691.4, 'extra_llm_calls': 0}

## Scores

- faithfulness: 0.3
- completeness: 0.25
- relevance: 0.4
- correct_abstention: 0.2
- citation_correctness: 1.0

## Failure distribution

| Failure | Count |
| --- | ---: |
| UNSUPPORTED_CLAIM | 3 |
| BAD_ABSTENTION | 3 |
| INCOMPLETE_ANSWER | 2 |

## Changed outcomes

| Case | Result | Before | After |
| --- | --- | --- | --- |
| GT-081 | REGRESSED | PASS | FAIL |
| GT-090 | REGRESSED | PASS | FAIL |