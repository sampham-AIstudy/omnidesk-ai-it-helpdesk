# Semantic Judge v1.3

Judge-only run over immutable `baseline_v1_1` answers and context.

## Reliability

- Eligible: 12
- Successfully judged: 12
- INFRA_ERROR: 0 (0.0%)
- Semantic pass/fail: 3/9
- Final-pass policy: semantic-hard-gates-v1

## Scores

- faithfulness: 0.2917
- completeness: 0.25
- relevance: 0.3333
- correct_abstention: 0.3333
- citation_correctness: 0.9167

## Semantic failure distribution

| Failure | Count |
| --- | ---: |
| BAD_ABSTENTION | 3 |
| INCOMPLETE_ANSWER | 4 |
| HALLUCINATION | 1 |
| UNSUPPORTED_CLAIM | 1 |

## Calibration

- Label source: manual_contract_review_by_evaluator
- Tuning: {'labelled': 0, 'compared': 0}
- Holdout: {'labelled': 12, 'compared': 12, 'agreement': 0.8333, 'false_positive_rate': 0.0833, 'false_negative_rate': 0.0833, 'precision': 0.6667, 'recall': 0.6667}
- Dangerous false pass: 0
- Readiness: NOT_READY

## Disagreements

| Case | Split | Classification | Dimension | Reason |
| --- | --- | --- | --- | --- |
| GT-033 | holdout | JUDGE_TOO_LENIENT | FINAL_PASS | MISSED_EXPECTED_FAILURE |
| GT-048 | holdout | JUDGE_CORRECT | FAITHFULNESS | DIMENSION_BAND_DIFFERENCE_FINAL_PASS_MATCHES |
| GT-071 | holdout | JUDGE_CORRECT | FAITHFULNESS | DIMENSION_BAND_DIFFERENCE_FINAL_PASS_MATCHES |
| GT-072 | holdout | JUDGE_CORRECT | FAITHFULNESS | DIMENSION_BAND_DIFFERENCE_FINAL_PASS_MATCHES |
| GT-073 | holdout | JUDGE_CORRECT | FAITHFULNESS | DIMENSION_BAND_DIFFERENCE_FINAL_PASS_MATCHES |
| GT-076 | holdout | JUDGE_CORRECT | FAITHFULNESS | DIMENSION_BAND_DIFFERENCE_FINAL_PASS_MATCHES |
| GT-077 | holdout | JUDGE_CORRECT | FAITHFULNESS | DIMENSION_BAND_DIFFERENCE_FINAL_PASS_MATCHES |
| GT-084 | holdout | JUDGE_CORRECT | FAITHFULNESS | DIMENSION_BAND_DIFFERENCE_FINAL_PASS_MATCHES |
| GT-085 | holdout | JUDGE_CORRECT | FAITHFULNESS | DIMENSION_BAND_DIFFERENCE_FINAL_PASS_MATCHES |
| GT-087 | holdout | JUDGE_TOO_STRICT | FINAL_PASS | TOO_STRICT_INCOMPLETE_ANSWER |