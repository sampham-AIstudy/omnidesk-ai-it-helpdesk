# Semantic Judge v1.2

Judge-only run over immutable `baseline_v1_1` answers and context.

## Reliability

- Eligible: 90
- Successfully judged: 89
- INFRA_ERROR: 1 (1.1%)
- Semantic pass/fail: 58/31

## Scores

- faithfulness: 0.8258
- completeness: 0.8371
- relevance: 0.9438
- correct_abstention: 0.6517
- citation_correctness: 1.0

## Infrastructure errors

| Type | Count |
| --- | ---: |
| SCHEMA_MISMATCH | 1 |

## Calibration

- Rubric-labelled subset: 20; compared: 20
- Semantic pass agreement: 0.65
- False positive rate: 0.0
- False negative rate: 0.35

## Readiness: NOT_READY

## Original v1.1 infrastructure audit

| Case | Error type | HTTP status | Attempt | Raw length | Provider | Model |
| --- | --- | --- | --- | --- | --- | --- |
| GT-001 | INVALID_JSON | unavailable | unavailable | unavailable | nvidia | meta/llama-3.1-8b-instruct |
| GT-035 | UNKNOWN_PROVIDER_ERROR | unavailable | unavailable | unavailable | nvidia | meta/llama-3.1-8b-instruct |
| GT-040 | UNKNOWN_PROVIDER_ERROR | unavailable | unavailable | unavailable | nvidia | meta/llama-3.1-8b-instruct |
| GT-041 | UNKNOWN_PROVIDER_ERROR | unavailable | unavailable | unavailable | nvidia | meta/llama-3.1-8b-instruct |
| GT-042 | UNKNOWN_PROVIDER_ERROR | unavailable | unavailable | unavailable | nvidia | meta/llama-3.1-8b-instruct |
| GT-044 | UNKNOWN_PROVIDER_ERROR | unavailable | unavailable | unavailable | nvidia | meta/llama-3.1-8b-instruct |
| GT-045 | UNKNOWN_PROVIDER_ERROR | unavailable | unavailable | unavailable | nvidia | meta/llama-3.1-8b-instruct |
| GT-046 | UNKNOWN_PROVIDER_ERROR | unavailable | unavailable | unavailable | nvidia | meta/llama-3.1-8b-instruct |
| GT-047 | UNKNOWN_PROVIDER_ERROR | unavailable | unavailable | unavailable | nvidia | meta/llama-3.1-8b-instruct |
| GT-049 | UNKNOWN_PROVIDER_ERROR | unavailable | unavailable | unavailable | nvidia | meta/llama-3.1-8b-instruct |
| GT-051 | UNKNOWN_PROVIDER_ERROR | unavailable | unavailable | unavailable | nvidia | meta/llama-3.1-8b-instruct |
| GT-082 | UNKNOWN_PROVIDER_ERROR | unavailable | unavailable | unavailable | nvidia | meta/llama-3.1-8b-instruct |
| GT-083 | UNKNOWN_PROVIDER_ERROR | unavailable | unavailable | unavailable | nvidia | meta/llama-3.1-8b-instruct |
| GT-084 | UNKNOWN_PROVIDER_ERROR | unavailable | unavailable | unavailable | nvidia | meta/llama-3.1-8b-instruct |
| GT-085 | UNKNOWN_PROVIDER_ERROR | unavailable | unavailable | unavailable | nvidia | meta/llama-3.1-8b-instruct |
| GT-086 | UNKNOWN_PROVIDER_ERROR | unavailable | unavailable | unavailable | nvidia | meta/llama-3.1-8b-instruct |
| GT-087 | UNKNOWN_PROVIDER_ERROR | unavailable | unavailable | unavailable | nvidia | meta/llama-3.1-8b-instruct |
| GT-088 | UNKNOWN_PROVIDER_ERROR | unavailable | unavailable | unavailable | nvidia | meta/llama-3.1-8b-instruct |
| GT-089 | UNKNOWN_PROVIDER_ERROR | unavailable | unavailable | unavailable | nvidia | meta/llama-3.1-8b-instruct |
| GT-090 | UNKNOWN_PROVIDER_ERROR | unavailable | unavailable | unavailable | nvidia | meta/llama-3.1-8b-instruct |