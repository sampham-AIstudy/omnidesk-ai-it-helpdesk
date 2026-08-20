# Evaluation Baseline v1.0

## Baseline Metadata

- generated_at: `2026-08-20T14:57:42.127346+00:00`
- golden_dataset: `eval\golden_testset_enterprise.json`
- golden_dataset_sha256: `7eac168c97cc3a0be780add2b0d8a2edf982e9b29346488882503cce62d8e8ec`
- manifest_sha256: `da9cc82957f182226ac79524719e221e60b5cc70369ec59b1539eb2956e51f58`
- context_snapshot: `eval\snapshots\enterprise_context_snapshot_v1_2.json`
- context_snapshot_sha256: `ca6c07b0e52592e9fc57f3deeaef6c16f0f8bfbd1db45ccf5adb456ad0d9967a`
- git_commit: `442e0bd5f287823d0225eada289ec92a4db6a2a4`
- generation_mode: `fixed_context_snapshot`
- answer_source: `none`
- generation_model: `configured production default`
- judge_model: `not_run`
- top_k: `5`

## Status

- Cases: 300
- Status: {'PASS': 253, 'FAIL': 47}
- Layer membership: {'routing': 300, 'generation': 300, 'retrieval': 197, 'workflow': 72, 'clarification': 49, 'security': 81}

## Routing

- Accuracy: 0.3974 (31/78)

## Retrieval

- See `baseline_v1_retrieval.json` for snapshot Retrieval Hit@k / MRR / relevance / noise metrics.

## Generation

- Fixed-context answers evaluated: 0
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
| OVER_RETRIEVAL | 47 | 15.67% | ROUTER | MEDIUM |
| ROUTING_ERROR | 47 | 15.67% | ROUTER | MEDIUM |

## Top Failed Cases

| ID | Question | Expected route | Actual route | Failure | Suspected layer |
|---|---|---|---|---|---|
| GT-091 | Chào buổi sáng. | direct_response | knowledge | OVER_RETRIEVAL, ROUTING_ERROR | ROUTER |
| GT-093 | Bạn có rảnh không? | direct_response | knowledge | OVER_RETRIEVAL, ROUTING_ERROR | ROUTER |
| GT-095 | Chúc bạn một ngày tốt lành. | direct_response | knowledge | OVER_RETRIEVAL, ROUTING_ERROR | ROUTER |
| GT-096 | Hello helpdesk | direct_response | knowledge | OVER_RETRIEVAL, ROUTING_ERROR | ROUTER |
| GT-097 | Bạn tên gì? | direct_response | knowledge | OVER_RETRIEVAL, ROUTING_ERROR | ROUTER |
| GT-098 | Hẹn gặp lại | direct_response | knowledge | OVER_RETRIEVAL, ROUTING_ERROR | ROUTER |
| GT-099 | Tối nay bạn khỏe chứ? | direct_response | knowledge | OVER_RETRIEVAL, ROUTING_ERROR | ROUTER |
| GT-100 | Xin chào đội IT. | direct_response | knowledge | OVER_RETRIEVAL, ROUTING_ERROR | ROUTER |
| GT-101 | Cảm ơn bạn đã hỗ trợ | direct_response | knowledge | OVER_RETRIEVAL, ROUTING_ERROR | ROUTER |
| GT-102 | Good morning | direct_response | knowledge | OVER_RETRIEVAL, ROUTING_ERROR | ROUTER |
| GT-103 | Chào trợ lý | direct_response | knowledge | OVER_RETRIEVAL, ROUTING_ERROR | ROUTER |
| GT-104 | Bạn có thể trò chuyện một chút không? | direct_response | knowledge | OVER_RETRIEVAL, ROUTING_ERROR | ROUTER |
| GT-105 | asdf qwer | needs_clarification | knowledge | OVER_RETRIEVAL, ROUTING_ERROR | ROUTER |
| GT-106 | 123 ### ??? | needs_clarification | knowledge | OVER_RETRIEVAL, ROUTING_ERROR | ROUTER |
| GT-107 | lorem ipsum | needs_clarification | knowledge | OVER_RETRIEVAL, ROUTING_ERROR | ROUTER |

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
