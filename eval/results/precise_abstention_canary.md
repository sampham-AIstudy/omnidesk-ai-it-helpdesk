# Precise Abstention Canary

- Decision: **REJECT**
- Generator calls: 0.

| ID | Route | Context | Applied | Control | Treatment | Movement |
| --- | --- | --- | --- | --- | --- | --- |
| GT-046 | knowledge | EMPTY | True | FAIL | FAIL | UNCHANGED |
| GT-077 | knowledge | EMPTY | True | FAIL | FAIL | UNCHANGED |
| GT-087 | knowledge | EMPTY | True | FAIL | FAIL | UNCHANGED |
| GT-027 | incident | NONEMPTY | False | PASS | PASS | UNCHANGED |
| GT-047 | incident | NONEMPTY | False | PASS | PASS | UNCHANGED |
| GT-048 | incident | NONEMPTY | False | PASS | PASS | UNCHANGED |

## Hard gates

- targets_apply_path: True
- gt_027_retained: True
- gt_047_retained: True
- gt_048_retained: True
- no_unsupported_claim: True
- no_hallucination: False
- no_bad_abstention_increase: True
- no_citation_error: True
- no_infra_error: True