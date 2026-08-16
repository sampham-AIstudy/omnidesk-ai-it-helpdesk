# Response Planner Exp1.2 — Regression Autopsy

## Decision

**ABANDON_PLANNER.** This is an artifact-only review; production code, evaluation fixtures, Judge v1.3, and model outputs were not changed.

## Case movement

- Regressed (16): GT-004, GT-010, GT-011, GT-014, GT-019, GT-024, GT-030, GT-031, GT-034, GT-058, GT-060, GT-061, GT-062, GT-066, GT-069, GT-082
- Improved (5): GT-021, GT-053, GT-070, GT-086, GT-090
- Unchanged: 69

## Root causes

| Primary root cause | Count | % of 16 | Error class |
| --- | ---: | ---: | --- |
| WRONG_WORKFLOW_MODE | 9 | 56.2% | PLAN_STATE_ERROR |
| WRONG_COVERAGE_MODE | 4 | 25.0% | PLAN_STATE_ERROR |
| GENERATOR_PLAN_NONCOMPLIANCE | 1 | 6.2% | PLAN_COMPLIANCE_ERROR |
| NEEDS_USER_INPUT_MISCLASSIFIED | 1 | 6.2% | PLAN_STATE_ERROR |
| PART_UNDER_DECOMPOSITION | 1 | 6.2% | PLAN_STATE_ERROR |

Plan-state vs plan-compliance: PLAN_COMPLIANCE_ERROR=1, PLAN_STATE_ERROR=15

## Failure transitions

| Control state | Treatment state | Count |
| --- | --- | ---: |
| PASS | BAD_ABSTENTION | 6 |
| PASS | INCOMPLETE_ANSWER | 7 |
| PASS | INCOMPLETE_ANSWER + BAD_ABSTENTION | 1 |
| PASS | UNSUPPORTED_CLAIM | 2 |

## Per-case autopsy

| ID | First divergence | Primary cause | Class | Transition |
| --- | --- | --- | --- | --- |
| GT-004 | WORKFLOW_MODE | WRONG_WORKFLOW_MODE | PLAN_STATE_ERROR | PASS -> INCOMPLETE_ANSWER |
| GT-010 | GENERATOR_INTERPRETATION | GENERATOR_PLAN_NONCOMPLIANCE | PLAN_COMPLIANCE_ERROR | PASS -> BAD_ABSTENTION |
| GT-011 | COVERAGE_MODE | WRONG_COVERAGE_MODE | PLAN_STATE_ERROR | PASS -> BAD_ABSTENTION |
| GT-014 | COVERAGE_MODE | WRONG_COVERAGE_MODE | PLAN_STATE_ERROR | PASS -> INCOMPLETE_ANSWER |
| GT-019 | WORKFLOW_MODE | WRONG_WORKFLOW_MODE | PLAN_STATE_ERROR | PASS -> BAD_ABSTENTION |
| GT-024 | REQUEST_DECOMPOSITION | PART_UNDER_DECOMPOSITION | PLAN_STATE_ERROR | PASS -> BAD_ABSTENTION |
| GT-030 | WORKFLOW_MODE | WRONG_WORKFLOW_MODE | PLAN_STATE_ERROR | PASS -> INCOMPLETE_ANSWER |
| GT-031 | COVERAGE_MODE | WRONG_COVERAGE_MODE | PLAN_STATE_ERROR | PASS -> INCOMPLETE_ANSWER |
| GT-034 | WORKFLOW_MODE | WRONG_WORKFLOW_MODE | PLAN_STATE_ERROR | PASS -> INCOMPLETE_ANSWER + BAD_ABSTENTION |
| GT-058 | WORKFLOW_MODE | WRONG_WORKFLOW_MODE | PLAN_STATE_ERROR | PASS -> BAD_ABSTENTION |
| GT-060 | WORKFLOW_MODE | WRONG_WORKFLOW_MODE | PLAN_STATE_ERROR | PASS -> UNSUPPORTED_CLAIM |
| GT-061 | WORKFLOW_MODE | WRONG_WORKFLOW_MODE | PLAN_STATE_ERROR | PASS -> BAD_ABSTENTION |
| GT-062 | WORKFLOW_MODE | WRONG_WORKFLOW_MODE | PLAN_STATE_ERROR | PASS -> UNSUPPORTED_CLAIM |
| GT-066 | SUPPORT_CLASSIFICATION | NEEDS_USER_INPUT_MISCLASSIFIED | PLAN_STATE_ERROR | PASS -> INCOMPLETE_ANSWER |
| GT-069 | COVERAGE_MODE | WRONG_COVERAGE_MODE | PLAN_STATE_ERROR | PASS -> INCOMPLETE_ANSWER |
| GT-082 | WORKFLOW_MODE | WRONG_WORKFLOW_MODE | PLAN_STATE_ERROR | PASS -> INCOMPLETE_ANSWER |

## Payload finding

Every regressed case invoked the generator once. The serialized plan averaged 494.3 characters (range 391–667), excluding shared evidence and instructions. The primary issue is semantic duplication, not token volume.

## Useful primitives to retain independently

| Primitive | Improved cases | Regression risk |
| --- | --- | --- |
| Preserve explicit physical-incident facts for concise triage | GT-070 | Safe only when a trusted incident extractor already establishes the facts; do not infer missing incident facts. |
| State a precise evidence boundary instead of inventing a broader policy | GT-021, GT-086 | Keep as a generator/evidence instruction, not as global requested-part classification. |
| Short acknowledgement for social turns | GT-053 | The plan itself was wrong (KNOWLEDGE + ABSTAIN); retain only the existing direct-response route, not this planner behavior. |
| Use trusted VPN incident facts to avoid restarting the conversation | GT-090 | Do not retain the treatment's request for a password; only preserve trusted prior facts and targeted diagnostics. |

## Recommended next experiment (not implemented)

Run a small generator-policy canary for non-KB modes using only trusted existing routing, authorization, and tool state. It must not create a second requested-parts/support classifier. Keep evidence-binding as a separate later experiment.
