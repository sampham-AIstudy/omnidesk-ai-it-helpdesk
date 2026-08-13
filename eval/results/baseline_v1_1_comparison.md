# Baseline v1 vs v1.1

| Metric | v1 | v1.1 | Delta |
|---|---:|---:|---:|
| Deterministic golden PASS | 81 / 90 | 90 / 90 | +9 |
| Deterministic golden FAIL | 9 / 90 | 0 / 90 | -9 |
| Routing contract | 21 / 21 | 21 / 21 | 0 |
| Prompt/security gate failures | 5 | 0 | -5 |
| Confirmed tool-grounding failures | 0 | 0 | 0 |
| Over-questioning | 1 | 0 | -1 |
| Incomplete answer | 1 | 0 | -1 |
| Incorrect refusal | 1 | 0 | -1 |
| Hit@1 | 25.0% | 25.0% | 0 |
| Hit@5 / Recall@5 | 100% | 100% | 0 |
| MRR | 0.533 | 0.533 | 0 |
| Source relevance | 53.3% | 53.3% | 0 |
| Noise rate | 46.7% | 46.7% | 0 |

## Semantic Judge run

The semantic judge was run on the v1.1 fixed-context answer snapshot with the configured NVIDIA fallback judge at temperature 0.

| Metric | Result |
|---|---:|
| Cases with semantic result | 70 / 90 |
| Judge infrastructure errors | 20 / 90 |
| Faithfulness | 0.3571 |
| Completeness | 0.3429 |
| Relevance | 0.3714 |
| Correct abstention | 0.6714 |
| Semantic PASS | 25 |
| Semantic FAIL | 45 |

`INFRA_ERROR` remains separate from model-quality failures. The semantic run is a baseline measurement, not a release gate until judge availability and output-schema reliability are fixed.
