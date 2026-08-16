# Semantic Judge v1.3

Judge-only run over immutable `baseline_v1_1` answers and context.

## Reliability

- Eligible: 14
- Successfully judged: 14
- INFRA_ERROR: 0 (0.0%)
- Semantic pass/fail: 6/8
- Final-pass policy: semantic-hard-gates-v1

## Scores

- faithfulness: 0.5714
- completeness: 0.4286
- relevance: 0.8214
- correct_abstention: 0.4286
- citation_correctness: 1.0

## Semantic failure distribution

| Failure | Count |
| --- | ---: |
| BAD_ABSTENTION | 2 |
| INCOMPLETE_ANSWER | 4 |
| UNSUPPORTED_CLAIM | 2 |

## Calibration

- Label source: manual_contract_review_by_evaluator
- Tuning: {'labelled': 14, 'compared': 14, 'agreement': 0.7857, 'false_positive_rate': 0.0714, 'false_negative_rate': 0.1429, 'precision': 0.8333, 'recall': 0.7143}
- Holdout: {'labelled': 0, 'compared': 0}
- Dangerous false pass: 0
- Readiness: NOT_READY

## Disagreements

| Case | Split | Classification | Dimension | Reason |
| --- | --- | --- | --- | --- |
| GT-006 | tuning | JUDGE_TOO_STRICT | FINAL_PASS | TOO_STRICT_BAD_ABSTENTION |
| GT-015 | tuning | JUDGE_TOO_STRICT | FINAL_PASS | TOO_STRICT_INCOMPLETE_ANSWER |
| GT-023 | tuning | JUDGE_CORRECT | FAITHFULNESS | DIMENSION_BAND_DIFFERENCE_FINAL_PASS_MATCHES |
| GT-027 | tuning | JUDGE_CORRECT | FAITHFULNESS | DIMENSION_BAND_DIFFERENCE_FINAL_PASS_MATCHES |
| GT-040 | tuning | JUDGE_CORRECT | FAITHFULNESS | DIMENSION_BAND_DIFFERENCE_FINAL_PASS_MATCHES |
| GT-047 | tuning | JUDGE_CORRECT | COMPLETENESS | DIMENSION_BAND_DIFFERENCE_FINAL_PASS_MATCHES |
| GT-056 | tuning | JUDGE_CORRECT | FAITHFULNESS | DIMENSION_BAND_DIFFERENCE_FINAL_PASS_MATCHES |
| GT-068 | tuning | JUDGE_CORRECT | FAITHFULNESS | DIMENSION_BAND_DIFFERENCE_FINAL_PASS_MATCHES |
| GT-086 | tuning | JUDGE_CORRECT | FAITHFULNESS | DIMENSION_BAND_DIFFERENCE_FINAL_PASS_MATCHES |
| GT-088 | tuning | JUDGE_TOO_LENIENT | FINAL_PASS | MISSED_EXPECTED_FAILURE |