# Generator Evidence-Use Canary

- Decision: **PROMISING**
- Scope: GT-020/GT-029 targets, three positive controls, GT-067 diagnostic only.
- No retrieval refresh, full-90 run or production prompt change.

## Structural change

- Control: [AUTHORIZED_EVIDENCE] followed by [USER QUESTION]
- Treatment: [USER QUESTION] followed by the same verbatim evidence enclosed in AUTHORIZED_SOURCE_DATA markers
- Instruction delta: 0 policy instructions; only evidence-boundary markers and order changed.

## Case comparison

| ID | Group | Control | Treatment | Movement |
| --- | --- | --- | --- | --- |
| GT-020 | target | FAIL | PASS | IMPROVED |
| GT-029 | target | FAIL | PASS | IMPROVED |
| GT-027 | positive_control | PASS | PASS | UNCHANGED |
| GT-047 | positive_control | PASS | PASS | UNCHANGED |
| GT-048 | positive_control | PASS | PASS | UNCHANGED |
| GT-067 | diagnostic | FAIL | FAIL | UNCHANGED |

## Failure counts

| Failure | Control | Treatment |
| --- | ---: | ---: |
| BAD_ABSTENTION | 1 | 0 |
| INCOMPLETE_ANSWER | 2 | 1 |

## Hard gates

- gt_027_retained: True
- gt_047_retained: True
- gt_048_retained: True
- no_new_unsupported_claim: True
- no_new_hallucination: True
- no_new_bad_abstention: True
- no_new_citation_failure: True
- production_target_pass_count_not_decreased: True
- no_infra_error: True