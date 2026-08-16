# Evaluation Baseline v1.0

## Baseline Metadata

- generated_at: `2026-08-13T08:43:36.363610+00:00`
- golden_dataset: `eval\golden_testset_enterprise.json`
- golden_dataset_sha256: `4f950b3712c2c620530c9223ee0c484417ef3d12d78869ca97f63ca53d6a2858`
- manifest_sha256: `51b805c742cab972e6b6da7e7595855e6560fbe453dad3dd13629365c7f802fb`
- context_snapshot: `eval\results\baseline_v1_1_context_snapshot.json`
- context_snapshot_sha256: `e466c7f853afa35ce6d7ccd65f1ad62bf89c9e34cbc23c8401cc7f05f99d6eb6`
- git_commit: `f13cec3807f5058de6eb41289e1369e60ff97c80`
- generation_mode: `fixed_context_snapshot`
- answer_source: `reused_snapshot:eval\results\baseline_v1_1.json`
- generation_model: `configured production default`
- judge_model: `not_run`
- top_k: `5`

## Status

- Cases: 90
- Status: {'PASS': 90}
- Layer membership: {'routing': 90, 'generation': 90, 'retrieval': 71, 'workflow': 16, 'clarification': 7, 'security': 11}

## Routing

- Accuracy: 1.0 (22/22)

## Retrieval

- See `baseline_v1_retrieval.json` for snapshot Retrieval Hit@k / MRR / relevance / noise metrics.

## Generation

- Fixed-context answers evaluated: 90
- Semantic LLM judge: NOT_RUN (not inferred from retrieval confidence).
- Deterministic citation, action-grounding, partial-answer and clarification checks are included in each case record.

## Workflow

- Golden cases mapped: 16
- DB contract suite: `tests/test_eval/test_baseline_v1_workflow.py`

## Security

- Golden cases mapped: 11
- Security failures: 0 (kept outside any quality average).

## Failure Distribution

| Failure | Count | % cases | Layer | Severity |
|---|---:|---:|---|

## Top Failed Cases

| ID | Question | Expected route | Actual route | Failure | Suspected layer |
|---|---|---|---|---|---|

## Proposed Experiments (not executed)

| Experiment | Target failure | Layer | Expected benefit | Risk | Cost |
|---|---|---|---|---|---|
| Harden injection gate patterns | PROMPT_INJECTION_FAILURE | GUARDRAIL | Block unsafe inputs before retrieval/tooling | False positives | Low |
| Bind action claims to tool result | TOOL_GROUNDING_ERROR | TOOL_LAYER | Prevent false completion claims | Extra tool-state handling | Medium |
| Slot-aware clarification state | OVER_QUESTIONING | CLARIFIER | Avoid re-asking known facts | Slot extraction regressions | Medium |
| Partial-answer evidence contract | INCOMPLETE_ANSWER, INCORRECT_REFUSAL | GENERATOR | Answer supported facets and abstain only missing ones | More response complexity | Low |
| Retriever ranking experiment | Low MRR / source relevance | RETRIEVER | Improve evidence order and noise | Needs controlled A/B | Medium |

## Reproducibility Notes

- Generation uses only the persisted context snapshot in this run; it does not execute live retrieval.
- `NOT_APPLICABLE` means a layer was intentionally not run for that case. `INFRA_ERROR` is never included as a model-quality failure.
- Semantic generation judging is deliberately marked `NOT_RUN` until a separately configured judge is available; no retrieval metric is substituted for it.
- No production retrieval, model, prompt, threshold, or chunking setting was changed by this evaluation.
