# Feedback Preference Evaluation Contract

No DPO, ORPO, reranker, or prompt-optimizer candidate may be trained or promoted
until it has an approved, privacy-filtered dataset manifest and all checks below.

| Requirement | Promotion gate |
|---|---|
| Baseline model | Pinned identifier and immutable baseline report |
| Candidate model | Pinned identifier, training/data manifest hash, reproducible configuration |
| Held-out preference test | Ticket/conversation-disjoint test JSONL split; never used for fitting |
| Golden 300 | 300/300 pass, no new safety failure |
| Retrieval gate | Current threshold pass; zero tenant/forbidden/policy leaks |
| P0 hard-negative | No regression in Hit@3/Hit@5; zero intent confusion at rank one |
| Safety tests | All privacy, prompt-injection, action-grounding, and RBAC tests pass |

Promotion requires an explicit human approval after comparing the candidate against
the baseline. A failed or incomplete gate blocks promotion. This contract does not
authorize model training or production inference changes.
