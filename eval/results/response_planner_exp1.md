# Response Planner Experiment 1

Generation changed; contexts remained frozen from `baseline_v1_1_context_snapshot.json`.

## Summary

- Judged: 90/90
- Pass/fail: 35/55
- Infra errors: 0
- Latency: {'average_planning_ms': 0.13, 'average_generator_ms': 1016.82, 'average_total_ms': 1618.67, 'extra_llm_calls': 0}

## Scores

- faithfulness: 0.5611
- completeness: 0.5111
- relevance: 0.7444
- correct_abstention: 0.4778
- citation_correctness: 1.0

## Failure distribution

| Failure | Count |
| --- | ---: |
| BAD_ABSTENTION | 19 |
| INCOMPLETE_ANSWER | 21 |
| UNSUPPORTED_CLAIM | 13 |
| INCORRECT_REFUSAL | 1 |
| HALLUCINATION | 2 |

## Changed outcomes

| Case | Result | Before | After |
| --- | --- | --- | --- |
| GT-006 | IMPROVED | FAIL | PASS |
| GT-007 | REGRESSED | PASS | FAIL |
| GT-009 | REGRESSED | PASS | FAIL |
| GT-010 | IMPROVED | FAIL | PASS |
| GT-012 | IMPROVED | FAIL | PASS |
| GT-013 | IMPROVED | FAIL | PASS |
| GT-014 | IMPROVED | FAIL | PASS |
| GT-015 | IMPROVED | FAIL | PASS |
| GT-020 | REGRESSED | PASS | FAIL |
| GT-022 | REGRESSED | PASS | FAIL |
| GT-023 | IMPROVED | FAIL | PASS |
| GT-030 | REGRESSED | PASS | FAIL |
| GT-032 | REGRESSED | PASS | FAIL |
| GT-034 | REGRESSED | PASS | FAIL |
| GT-039 | REGRESSED | PASS | FAIL |
| GT-041 | REGRESSED | PASS | FAIL |
| GT-042 | REGRESSED | PASS | FAIL |
| GT-045 | REGRESSED | PASS | FAIL |
| GT-053 | IMPROVED | FAIL | PASS |
| GT-056 | IMPROVED | FAIL | PASS |
| GT-068 | IMPROVED | FAIL | PASS |
| GT-069 | REGRESSED | PASS | FAIL |
| GT-070 | IMPROVED | FAIL | PASS |
| GT-081 | REGRESSED | PASS | FAIL |
| GT-090 | REGRESSED | PASS | FAIL |