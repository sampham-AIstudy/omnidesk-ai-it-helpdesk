# Evaluation Baseline v1.0

## Baseline Metadata

- generated_at: `2026-08-21T05:43:01.536724+00:00`
- golden_dataset: `eval\golden_testset_enterprise.json`
- golden_dataset_sha256: `7eac168c97cc3a0be780add2b0d8a2edf982e9b29346488882503cce62d8e8ec`
- manifest_sha256: `da9cc82957f182226ac79524719e221e60b5cc70369ec59b1539eb2956e51f58`
- context_snapshot: `eval\results\baseline_v1_context_snapshot.json`
- context_snapshot_sha256: `7dde549fed5365072ed80b3266b448dd3538dc286fabb0111cf81db78de71c65`
- git_commit: `0f0cf291bece7d0f54be3dabed6dd8ec1cb73bb5`
- generation_mode: `fixed_context_snapshot`
- answer_source: `reused_snapshot:eval\results\baseline_v1.json`
- generation_model: `configured production default`
- judge_model: `not_run`
- top_k: `5`

## Status

- Cases: 300
- Status: {'PASS': 298, 'FAIL': 2}
- Layer membership: {'routing': 300, 'generation': 300, 'retrieval': 197, 'workflow': 72, 'clarification': 49, 'security': 81}

## Routing

- Accuracy: 1.0 (78/78)

## Retrieval

- See `baseline_v1_retrieval.json` for snapshot Retrieval Hit@k / MRR / relevance / noise metrics.

## Generation

- Fixed-context answers evaluated: 90
- Semantic LLM judge: NOT_RUN (not inferred from retrieval confidence).
- Deterministic citation, action-grounding, partial-answer and clarification checks are included in each case record.

## Workflow

- Golden cases mapped: 72
- DB contract suite: `tests/test_eval/test_baseline_v1_workflow.py`

## Security

- Golden cases mapped: 81
- Security failures: 0 (kept outside any quality average).

## Failure Distribution

| Failure | Count | % cases | Layer | Severity |
|---|---:|---:|---|
| OVER_QUESTIONING | 1 | 0.33% | CLARIFIER | MEDIUM |
| INCOMPLETE_ANSWER | 1 | 0.33% | GENERATOR | MEDIUM |
| INCORRECT_REFUSAL | 1 | 0.33% | GENERATOR | MEDIUM |

## Top Failed Cases

| ID | Question | Expected route | Actual route | Failure | Suspected layer |
|---|---|---|---|---|---|
| GT-006 | Tôi vừa đấm vào màn hình laptop, giờ màn hình đen xì luôn. | incident | incident | OVER_QUESTIONING | CLARIFIER |
| GT-047 | VPN dùng cổng nào và tài khoản bị khóa sau bao nhiêu lần nhập sai? | None | incident | INCOMPLETE_ANSWER, INCORRECT_REFUSAL | GENERATOR |

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
