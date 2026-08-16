# Empty-Context Abstention Judge Calibration

- Decision: **KEEP_JUDGE_V1_3**
- Calibration examples: 12
- Production changes: none.

## Calibration agreement

| Version | Semantic agreement | Hallucination agreement | Abstention agreement | FP | FN |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1.3 | 0.8333 | 0.5833 | 0.6667 | 0 | 2 |
| 1.3.1 | 0.9167 | 0.5 | 0.9167 | 1 | 0 |

## Targeted regression

| ID | v1.3 | v1.3.1 | v1.3 taxonomy inconsistency |
| --- | --- | --- | --- |
| GT-046 | FAIL | FAIL | True |
| GT-077 | FAIL | FAIL | False |
| GT-087 | FAIL | FAIL | True |
| GT-027 | FAIL | FAIL | False |
| GT-047 | PASS | PASS | False |
| GT-048 | PASS | PASS | False |
| GT-080 | FAIL | PASS | False |
| GT-086 | INFRA_ERROR | PASS | False |
| GT-058 | PASS | PASS | False |

Dangerous false passes v1.3.1: ['GT-080', 'GT-086']