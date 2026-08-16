# Knowledge Evidence-Salience Slice

- Decision: **REJECT**
- Full-90: not run.
- Treatment eligible: 20/23; intentionally empty cases retain control.

## Case movement

| ID | Applied | Control | Treatment | Movement |
| --- | --- | --- | --- | --- |
| GT-020 | True | FAIL | PASS | IMPROVED |
| GT-021 | True | FAIL | PASS | IMPROVED |
| GT-022 | True | PASS | PASS | UNCHANGED |
| GT-023 | True | PASS | PASS | UNCHANGED |
| GT-024 | True | PASS | PASS | UNCHANGED |
| GT-025 | True | PASS | PASS | UNCHANGED |
| GT-026 | True | PASS | FAIL | REGRESSED |
| GT-027 | True | PASS | PASS | UNCHANGED |
| GT-029 | True | FAIL | PASS | IMPROVED |
| GT-045 | True | PASS | FAIL | REGRESSED |
| GT-046 | False | FAIL | FAIL | UNCHANGED |
| GT-047 | True | PASS | PASS | UNCHANGED |
| GT-048 | True | PASS | PASS | UNCHANGED |
| GT-049 | True | PASS | PASS | UNCHANGED |
| GT-067 | True | FAIL | FAIL | UNCHANGED |
| GT-071 | True | PASS | PASS | UNCHANGED |
| GT-072 | True | PASS | FAIL | REGRESSED |
| GT-073 | True | FAIL | PASS | IMPROVED |
| GT-076 | True | PASS | FAIL | REGRESSED |
| GT-077 | False | FAIL | FAIL | UNCHANGED |
| GT-086 | True | FAIL | FAIL | UNCHANGED |
| GT-087 | False | FAIL | FAIL | UNCHANGED |
| GT-088 | True | PASS | PASS | UNCHANGED |

## Full 23-case slice

| Metric | Control | Treatment |
| --- | ---: | ---: |
| Semantic pass | 14 | 14 |
| Semantic fail | 9 | 9 |
| Generic fallback | 11 | 8 |
| faithfulness | 0.6522 | 0.7174 |
| completeness | 0.6304 | 0.6522 |
| relevance | 0.8043 | 0.8261 |
| correct_abstention | 0.6087 | 0.7391 |
| citation_correctness | 1.0 | 1.0 |

## Treatment-eligible subset

| Metric | Control | Treatment |
| --- | ---: | ---: |
| Semantic pass | 14 | 14 |
| Semantic fail | 6 | 6 |
| Generic fallback | 8 | 5 |
| faithfulness | 0.75 | 0.825 |
| completeness | 0.725 | 0.75 |
| relevance | 0.875 | 0.9 |
| correct_abstention | 0.7 | 0.85 |
| citation_correctness | 1.0 | 1.0 |

## Hard gates

- fixture_integrity_90_90: True
- gt_027_retained: True
- gt_047_retained: True
- gt_048_retained: True
- unsupported_claim_not_increased: True
- hallucination_not_increased: True
- bad_abstention_not_increased: True
- citation_error_not_increased: True
- no_dangerous_regression: False
- no_infra_error: True