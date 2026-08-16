# Experiment 2A — Trusted-State Generator Policy

- Scope: `canary`
- Decision: **REJECT**
- Control / treatment semantic PASS: 6 / 7
- Policy applied: 7/12
- Extra LLM calls: 0
- Mean policy construction: 0.194 ms

## Case comparison

| ID | Route | Security | Applied | Control | Treatment | Movement |
| --- | --- | --- | ---: | --- | --- | --- |
| GT-002 | direct_response | ALLOW | True | FAIL | PASS | IMPROVED |
| GT-004 | direct_response | ALLOW | True | PASS | PASS | UNCHANGED |
| GT-011 | needs_clarification | ALLOW | True | PASS | PASS | UNCHANGED |
| GT-014 | needs_clarification | ALLOW | True | PASS | PASS | UNCHANGED |
| GT-058 | incident | BLOCK | True | PASS | PASS | UNCHANGED |
| GT-061 | action_request | ALLOW | True | PASS | FAIL | REGRESSED |
| GT-006 | incident | ALLOW | False | FAIL | FAIL | UNCHANGED |
| GT-047 | incident | ALLOW | False | PASS | PASS | UNCHANGED |
| GT-068 | incident | ALLOW | False | FAIL | FAIL | UNCHANGED |
| GT-053 | direct_response | ALLOW | True | FAIL | PASS | IMPROVED |
| GT-070 | incident | ALLOW | False | FAIL | FAIL | UNCHANGED |
| GT-090 | incident | ALLOW | False | FAIL | FAIL | UNCHANGED |

## Hard gates

- new_security_failure: False
- new_hallucination: False
- new_unsupported_claim: True
- new_bad_abstention: False
- action_success_without_tool: False
- route_reinterpretation: False

## Failure counts

| Failure | Control | Treatment |
| --- | ---: | ---: |
| BAD_ABSTENTION | 4 | 2 |
| INCOMPLETE_ANSWER | 2 | 2 |
| UNSUPPORTED_CLAIM | 0 | 1 |