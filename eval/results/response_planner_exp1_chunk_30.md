# Response Planner Experiment 1

Generation changed; contexts remained frozen from `baseline_v1_1_context_snapshot.json`.

## Summary

- Judged: 10/10
- Pass/fail: 2/8
- Infra errors: 0
- Latency: {'average_planning_ms': 0.14, 'average_generator_ms': 975.18, 'average_total_ms': 1586.79, 'extra_llm_calls': 0}

## Scores

- faithfulness: 0.5
- completeness: 0.45
- relevance: 0.9
- correct_abstention: 0.3
- citation_correctness: 1.0

## Failure distribution

| Failure | Count |
| --- | ---: |
| INCOMPLETE_ANSWER | 4 |
| INCORRECT_REFUSAL | 1 |
| UNSUPPORTED_CLAIM | 2 |
| BAD_ABSTENTION | 1 |

## Changed outcomes

| Case | Result | Before | After |
| --- | --- | --- | --- |
| GT-032 | REGRESSED | PASS | FAIL |
| GT-034 | REGRESSED | PASS | FAIL |
| GT-039 | REGRESSED | PASS | FAIL |