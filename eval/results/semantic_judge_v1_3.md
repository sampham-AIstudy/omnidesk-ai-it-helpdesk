# Semantic Judge v1.3

Judge-only run over immutable `baseline_v1_1` answers and context.

## Reliability

- Eligible: 90
- Successfully judged: 90
- INFRA_ERROR: 0 (0.0%)
- Semantic pass/fail: 38/52
- Final-pass policy: semantic-hard-gates-v1

## Scores

- faithfulness: 0.55
- completeness: 0.4722
- relevance: 0.6944
- correct_abstention: 0.5
- citation_correctness: 0.9778

## Semantic failure distribution

| Failure | Count |
| --- | ---: |
| INCOMPLETE_ANSWER | 26 |
| BAD_ABSTENTION | 14 |
| UNSUPPORTED_CLAIM | 9 |
| HALLUCINATION | 2 |
| IRRELEVANT_ANSWER | 1 |

## Calibration

- Label source: manual_contract_review_by_evaluator
- Tuning: {'labelled': 14, 'compared': 14, 'agreement': 0.7857, 'false_positive_rate': 0.0714, 'false_negative_rate': 0.1429, 'precision': 0.8333, 'recall': 0.7143}
- Holdout: {'labelled': 12, 'compared': 12, 'agreement': 0.8333, 'false_positive_rate': 0.0833, 'false_negative_rate': 0.0833, 'precision': 0.6667, 'recall': 0.6667}
- Dangerous false pass: 0
- Readiness: READY

### Metric definitions

- **agreement**: Judge final semantic pass equals the reviewed semantic_pass label, divided by comparable labelled cases.
- **false_positive_rate**: Judge final semantic pass is true while reviewed semantic_pass is false, divided by comparable labelled cases.
- **false_negative_rate**: Judge final semantic pass is false while reviewed semantic_pass is true, divided by comparable labelled cases.
- **JUDGE_TOO_STRICT**: A final-pass disagreement where the reviewed label is pass and the Judge fails the case.
- **JUDGE_TOO_LENIENT**: A final-pass disagreement where the reviewed label is fail and the Judge passes the case.
- **dimension_band_difference**: A per-dimension high/medium/low difference while final pass/fail still agrees; it is reported separately and is not a false positive or false negative.

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