# final_knowledge_slice_v1_0

- Cases: 23
- Raw Judge v1.3: 10 PASS / 13 FAIL / 0 INFRA_ERROR

## Semantic metrics

- faithfulness: 0.7174
- completeness: 0.6087
- relevance: 0.913
- correct_abstention: 0.6522
- citation_correctness: 1.0

## Failure distribution

| Failure | Count |
| --- | ---: |
| BAD_ABSTENTION | 5 |
| HALLUCINATION | 1 |
| INCOMPLETE_ANSWER | 7 |

## Known Judge limitations

- KNOWN_JUDGE_LIMITATION_EMPTY_CONTEXT: GT-046, GT-077, GT-087. Report raw Judge v1.3 outputs unchanged and list this limitation separately; do not silently adjust scores or remove cases.