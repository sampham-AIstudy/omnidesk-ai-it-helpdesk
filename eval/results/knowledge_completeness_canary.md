# Knowledge Completeness Canary

- Decision: **REJECT**
- Scope: 11 knowledge cases only; no full-90 run.
- Frozen context snapshot: v1.2; retrieval was not refreshed.
- Extra LLM calls: 0 (one existing generator call per treatment case).

## Case comparison

| ID | Group | Control | Treatment | Movement |
| --- | --- | --- | --- | --- |
| GT-020 | target | FAIL | PASS | IMPROVED |
| GT-029 | target | FAIL | FAIL | UNCHANGED |
| GT-046 | target | FAIL | FAIL | UNCHANGED |
| GT-067 | target | FAIL | FAIL | UNCHANGED |
| GT-077 | target | FAIL | FAIL | UNCHANGED |
| GT-087 | target | FAIL | FAIL | UNCHANGED |
| GT-027 | positive_control | PASS | PASS | UNCHANGED |
| GT-047 | positive_control | PASS | PASS | UNCHANGED |
| GT-048 | positive_control | PASS | PASS | UNCHANGED |
| GT-049 | positive_control | PASS | FAIL | REGRESSED |
| GT-088 | positive_control | PASS | PASS | UNCHANGED |

## Failure counts

| Failure | Control | Treatment |
| --- | ---: | ---: |
| BAD_ABSTENTION | 1 | 1 |
| INCOMPLETE_ANSWER | 5 | 5 |

## Usage and performance

- Generic fallback: 7 → 7
- Mean generation latency: 1827.846 ms → 1780.451 ms

## Hard gates

- targets_improved_at_least_3: False
- positive_control_pass_retained: False
- gt_047_retained: True
- gt_048_retained: True
- unsupported_claim_not_increased: True
- hallucination_not_increased: True
- bad_abstention_not_increased: True
- citation_failure_not_increased: True
- no_regression: False
- no_infra_error: True

## Target diagnostics

- GT-029: GENERIC_FALLBACK_STILL_DOMINATES
- GT-046: GENERIC_FALLBACK_STILL_DOMINATES
- GT-067: GENERIC_FALLBACK_STILL_DOMINATES
- GT-077: GENERIC_FALLBACK_STILL_DOMINATES
- GT-087: GENERIC_FALLBACK_STILL_DOMINATES