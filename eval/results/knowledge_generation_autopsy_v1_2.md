# Knowledge Generation Failure Slice — clean control v1.2

Read-only analysis; no production generator, retriever, prompt, snapshot, or Judge change.

## Scope

- Knowledge cases: 23
- Semantic pass/fail: 14/9
- Global INCOMPLETE_ANSWER inside/outside slice: 5/16

## Failure distribution

| Failure | Count |
| --- | ---: |
| BAD_ABSTENTION | 3 |
| INCOMPLETE_ANSWER | 5 |
| HALLUCINATION | 1 |

## Failed cases

| ID | Root cause | Side | Judge failure |
| --- | --- | --- | --- |
| GT-020 | OVERLY_GENERIC_FALLBACK | GENERATOR | BAD_ABSTENTION |
| GT-021 | CONTEXT_FACT_MISREAD | GENERATOR | BAD_ABSTENTION |
| GT-029 | SUPPORTED_FACT_OMITTED | GENERATOR | INCOMPLETE_ANSWER |
| GT-046 | OVERLY_GENERIC_FALLBACK | GENERATOR | INCOMPLETE_ANSWER |
| GT-067 | PARTIAL_ANSWER_COLLAPSED_TO_REFUSAL | GENERATOR | INCOMPLETE_ANSWER |
| GT-073 | UNSUPPORTED_DETAIL_ADDED | GENERATOR | BAD_ABSTENTION |
| GT-077 | OVERLY_GENERIC_FALLBACK | GENERATOR | INCOMPLETE_ANSWER |
| GT-086 | POLICY_GENERALIZATION | GENERATOR | HALLUCINATION |
| GT-087 | OVERLY_GENERIC_FALLBACK | GENERATOR | INCOMPLETE_ANSWER |

## Positive controls

- **GT-027**: Grounded password-reset flow without requesting the old password.
- **GT-047**: Answers the supported VPN port and names the unsupported lockout threshold.
- **GT-048**: Lists supported laptop-replacement conditions and abstains on fulfillment time.
- **GT-049**: Surfaces a source conflict without inventing a single SLA value.
- **GT-088**: Short, evidence-supported VPN port answer with a real source ID.

## Recommended next canary

- **KNOWLEDGE_COMPLETENESS_CANARY**
- Target failures: GT-020, GT-029, GT-046, GT-067, GT-077, GT-087
- Positive controls: GT-027, GT-047, GT-048, GT-049, GT-088
- Expected benefit: Replace generic fallback with concise evidence-aware coverage or a precise abstention, without introducing unsupported detail.
- Regression risk: A completeness instruction may pressure the model to invent policy, numeric, or procedural details; preserve the five positive controls and keep GT-086/GT-073 as separate evidence-boundary work.