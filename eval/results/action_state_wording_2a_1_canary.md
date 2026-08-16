# Experiment 2A.1 — Action-State Wording Contract

- Decision: **PROMISING**
- Extra generator LLM calls: 0
- Full 90 run: no

## Canary

| ID | Path | State | Result |
| --- | --- | --- | --- |
| GT-061 | DETERMINISTIC_ACTION_STATE | FAILED | PASS |
| GT-058 | DETERMINISTIC_SECURITY | BLOCK | PASS |
| GT-053 | DETERMINISTIC_ROUTER | ALLOW | PASS |
| ACT-001-NOT-INVOKED | DETERMINISTIC_ACTION_STATE | NOT_INVOKED | True |
| ACT-002-SERVICE-NOT-INVOKED | DETERMINISTIC_ACTION_STATE | NOT_INVOKED | True |
| ACT-003-SUCCEEDED | DETERMINISTIC_ACTION_STATE | SUCCEEDED | True |

## Hard gates

- gt_061_pass: True
- new_unsupported_claim: False
- new_hallucination: False
- security_regression: False
- direct_response_regression: False
- tool_grounding_error: False
- fixture_contracts_pass: True