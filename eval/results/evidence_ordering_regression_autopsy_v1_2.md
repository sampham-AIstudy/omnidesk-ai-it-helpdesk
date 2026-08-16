# Evidence-Ordering Regression Autopsy

- Decision: **ABANDON_EVIDENCE_ORDERING_CHANGE**
- Production changes: none.
- New LLM calls: 0.

## Case profiles

| ID | Movement | Query | Support shape | Sources | Primary cause |
| --- | --- | --- | --- | ---: | --- |
| GT-020 | IMPROVED | incident_guidance | FULL_SUPPORT | 1 | QUERY_ANCHOR_HELPED |
| GT-021 | IMPROVED | incident_guidance | NONEMPTY_BUT_LIMITED | 1 | OTHER_VERIFIED |
| GT-029 | IMPROVED | account_status | PARTIAL_SUPPORT | 1 | GENERIC_FALLBACK_SUPPRESSED |
| GT-073 | IMPROVED | incident_guidance | FULL_SUPPORT | 1 | PROCEDURAL_TARGET_CLARIFIED |
| GT-026 | REGRESSED | incident_guidance | FULL_SUPPORT | 1 | CONDITIONAL_EVIDENCE_MISREAD |
| GT-045 | REGRESSED | procedure | NONEMPTY_BUT_LIMITED | 1 | PROCEDURAL_EVIDENCE_MISREAD |
| GT-072 | REGRESSED | policy | NONEMPTY_BUT_LIMITED | 1 | QUESTION_SCOPE_MISREAD |
| GT-076 | REGRESSED | procedure | NONEMPTY_BUT_LIMITED | 1 | QUESTION_SCOPE_MISREAD |

## Claim coverage

### GT-020

| Requested claim | Supported | Control | Treatment |
| --- | --- | --- | --- |
| Outlook repair/troubleshooting steps | True | answered_partially | answered |

The source supplies concrete Outlook recovery steps, though it does not establish the exact crash cause.
### GT-021

| Requested claim | Supported | Control | Treatment |
| --- | --- | --- | --- |
| Teams sign-in remediation | False | not_answered | not_answered |

The supplied source concerns meeting audio/video rather than sign-in. The treatment PASS is a Judge/context edge case, not evidence of safely improved support use.
### GT-029

| Requested claim | Supported | Control | Treatment |
| --- | --- | --- | --- |
| Account can be unlocked after repeated failed attempts | True | not_answered | answered |
| Exact lockout threshold | False | not_answered | not_answered |

Question-first made the account-unlock fact salient; exact thresholds remain unsupported and must not be inferred.
### GT-073

| Requested claim | Supported | Control | Treatment |
| --- | --- | --- | --- |
| Hard reset / Safe Mode / Startup Repair | True | answered | answered |
| Adapter, outlet, or external-monitor checks | False | answered | not_answered |

Treatment concentrated on supported recovery steps and removed unsupported hardware-detail expansion.
### GT-026

| Requested claim | Supported | Control | Treatment |
| --- | --- | --- | --- |
| DNS/proxy troubleshooting steps | True | answered | answered |
| A whole-Sales outage diagnosis or escalation | False | not_answered | not_answered |

The source is endpoint-oriented while the question describes a shared outage. Treatment foregrounded the broader scope and treated the available troubleshooting as insufficient.
### GT-045

| Requested claim | Supported | Control | Treatment |
| --- | --- | --- | --- |
| VPN authentication/connection troubleshooting | True | answered | answered_partially |
| Initial company VPN configuration | False | answered | not_answered |

The KB is a VPN failure runbook, not an initial configuration guide. Question-first exposed this mismatch and resulted in over-abstention rather than a clean bounded answer.
### GT-072

| Requested claim | Supported | Control | Treatment |
| --- | --- | --- | --- |
| Manager approval and shared-mailbox access process | True | answered | answered_partially |
| General shared-mailbox policy | False | not_answered | not_answered |

The context establishes a provisioning process, not the requested general policy. Treatment focused on the broader policy wording and under-covered the supported process.
### GT-076

| Requested claim | Supported | Control | Treatment |
| --- | --- | --- | --- |
| VPN troubleshooting | True | answered_partially | answered_partially |
| Internal VPN configuration | False | not_answered | not_answered |

The source has troubleshooting information but no internal configuration. The apparent treatment regression is chiefly a prompt/Judge edge case around a legitimately unsupported request.

## Feature comparison

| Feature | Improved | Regressed |
| --- | --- | --- |
| source_count | [1, 1, 1, 1] | [1, 1, 1, 1] |
| context_characters | [321, 348, 314, 286] | [354, 386, 267, 386] |
| support_shape | {'FULL_SUPPORT': 2, 'NONEMPTY_BUT_LIMITED': 1, 'PARTIAL_SUPPORT': 1} | {'FULL_SUPPORT': 1, 'NONEMPTY_BUT_LIMITED': 3} |
| live_route | {'incident': 4} | {'knowledge': 2, 'incident': 2} |
| query_type | {'incident_guidance': 3, 'account_status': 1} | {'incident_guidance': 1, 'procedure': 2, 'policy': 1} |
| requires_multi_source_synthesis | 0 | 0 |
| conditions_or_exceptions | 0 | 3 |

## Conclusion

Question-first helps when a short user goal has a directly usable, concrete action in the source (GT-020/029/073). It harms broad policy/configuration or scope-mismatched questions by foregrounding the unmet goal over adjacent evidence (GT-026/045/072/076). GT-021 is not reliable supporting evidence because its source does not cover the stated sign-in problem.

Route, source count, context size, and evidence presence overlap across both groups. The apparent separator is semantic material-match/answer scope, which would require a new support or question classifier and would recreate the rejected planner failure surface.

Recommended next step: **PRECISE_ABSTENTION_CANARY for intentionally empty-context GT-046, GT-077, and GT-087; keep the control evidence ordering.**