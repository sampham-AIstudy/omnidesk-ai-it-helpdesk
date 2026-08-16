# Response Planner Exp1.2 — Clean A/B on Context v1.2

Both arms used `evaluation_lock_v1_2_full.json`: identical golden dataset,
fixed context snapshot, generator configuration, Judge v1.3, and retrieval
configuration. Retrieval was not refreshed.

| Metric | Control | Treatment | Delta |
| --- | ---: | ---: | ---: |
| Semantic pass | 40 | 29 | -11 |
| Semantic fail | 50 | 61 | +11 |
| Infra error | 0 | 0 | 0 |
| Faithfulness | 0.5444 | 0.4889 | -0.0555 |
| Completeness | 0.5111 | 0.4111 | -0.1000 |
| Relevance | 0.6944 | 0.6889 | -0.0055 |
| Correct abstention | 0.4889 | 0.3444 | -0.1445 |
| Citation correctness | 0.9889 | 1.0000 | +0.0111 |
| INCOMPLETE_ANSWER | 21 | 29 | +8 |
| BAD_ABSTENTION | 15 | 18 | +3 |
| UNSUPPORTED_CLAIM | 13 | 15 | +2 |
| HALLUCINATION | 2 | 1 | -1 |

## Case movement

- Improved: 5 (`GT-021`, `GT-053`, `GT-070`, `GT-086`, `GT-090`)
- Regressed: 16 (`GT-004`, `GT-010`, `GT-011`, `GT-014`, `GT-019`, `GT-024`, `GT-030`, `GT-031`, `GT-034`, `GT-058`, `GT-060`, `GT-061`, `GT-062`, `GT-066`, `GT-069`, `GT-082`)
- Unchanged: 69

## Decision

**REJECT.** The planner reduced normal generator calls from 90 to 86, but did
not meet quality acceptance: semantic pass count decreased, incomplete answer,
bad abstention, and unsupported claims all increased. Its runtime changes were
rolled back after this measured run. The context v1.2 fixture repair remains.
