# production_baseline_v1_0

- Cases: 90
- Raw Judge v1.3: 36 PASS / 54 FAIL / 0 INFRA_ERROR

## Semantic metrics

- faithfulness: 0.6444
- completeness: 0.5722
- relevance: 0.8778
- correct_abstention: 0.4778
- citation_correctness: 1.0

## Failure distribution

| Failure | Count |
| --- | ---: |
| BAD_ABSTENTION | 30 |
| HALLUCINATION | 3 |
| INCOMPLETE_ANSWER | 10 |
| INCORRECT_REFUSAL | 7 |
| UNSUPPORTED_CLAIM | 5 |

## Known Judge limitations

- KNOWN_JUDGE_LIMITATION_EMPTY_CONTEXT: GT-046, GT-077, GT-087. Report raw Judge v1.3 outputs unchanged and list this limitation separately; do not silently adjust scores or remove cases.