# Response Planner Experiment 1

Generation changed; contexts remained frozen from `baseline_v1_1_context_snapshot.json`.

## Summary

- Judged: 10/10
- Pass/fail: 1/9
- Infra errors: 0
- Latency: {'average_planning_ms': 0.14, 'average_generator_ms': 1023.2, 'average_total_ms': 1645.0, 'extra_llm_calls': 0}

## Scores

- faithfulness: 0.3
- completeness: 0.2
- relevance: 0.45
- correct_abstention: 0.5
- citation_correctness: 1.0

## Failure distribution

| Failure | Count |
| --- | ---: |
| UNSUPPORTED_CLAIM | 4 |
| INCOMPLETE_ANSWER | 4 |
| BAD_ABSTENTION | 1 |

## Changed outcomes

| Case | Result | Before | After |
| --- | --- | --- | --- |
| GT-041 | REGRESSED | PASS | FAIL |
| GT-042 | REGRESSED | PASS | FAIL |
| GT-045 | REGRESSED | PASS | FAIL |