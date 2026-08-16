# Evaluation Contract & Domain Fact Repair v1.2

- Lock errors: none
- v1.1 global fixture audit: 66/90 pass; 24 EVAL_FIXTURE_ERROR

## Routing reporting

- Canonical: routing_contract_pass = 21 IDs
- Additional route assertions: route_assertion_pass = 22 IDs (adds GT-033)

## Canary preconditions

| Case | Pass |
| --- | ---: |
| GT-006 | PASS |
| GT-023 | PASS |
| GT-047 | PASS |
| GT-048 | PASS |
| GT-068 | PASS |

**PRECONDITION 5/5: PASS**

## GT-006 classification

- JUDGE_CALIBRATION_EDGE_CASE: Incident is workflow-actionable despite no complete root-cause diagnosis; the answer contains triage rather than an abstention.