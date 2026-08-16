# Response Planner correction experiment 1.1 — Canary

Fixed v1.1 context snapshot; retrieval was not refreshed.

| Case | Old | New | Delta |
| --- | --- | --- | --- |
| GT-006 | FAIL | FAIL | UNCHANGED |
| GT-023 | FAIL | FAIL | UNCHANGED |
| GT-047 | PASS | PASS | UNCHANGED |
| GT-048 | FAIL | FAIL | UNCHANGED |
| GT-068 | FAIL | FAIL | UNCHANGED |

## Planner states

| Case | Workflow | Coverage | Part support |
| --- | --- | --- | --- |
| GT-006 | INCIDENT | FULL_ANSWER | Tôi vừa đấm vào màn hình laptop, giờ màn hình đen xì luôn: SUPPORTED |
| GT-023 | INCIDENT | CLARIFY | Tôi không kết nối được VPN: NEEDS_USER_INPUT |
| GT-047 | INCIDENT | PARTIAL_ANSWER | VPN dùng cổng nào: SUPPORTED; tài khoản bị khóa sau bao nhiêu lần nhập sai: UNSUPPORTED |
| GT-048 | INCIDENT | ABSTAIN | Điều kiện xin laptop mới là gì: ACTION_DEPENDENT; mất bao lâu để được cấp: UNSUPPORTED |
| GT-068 | MULTI_INTENT | PARTIAL_ANSWER | Laptop tôi hỏng rồi: SUPPORTED; tôi muốn xin laptop thay thế: ACTION_DEPENDENT |

- Canary gate: **FAIL**
- Normal generator calls: 2; extra planner LLM calls: 0
- Mean planner latency: 0.164 ms

## Stop decision

The canary failed; no full-90 run was permitted and the experiment runtime changes were rolled back.

- GT-006: unchanged. The fixed-context semantic contract still treats the existing incident triage wording as `BAD_ABSTENTION`; this is not caused by workflow/coverage exclusivity.
- GT-023: the experimental planner applied a hardware `device` requirement to a VPN incident.
- GT-047: remains PASS and demonstrates `PARTIAL_ANSWER` correctly preserves the supported VPN-port answer and the precise abstention.
- GT-048: the immutable v1.1 snapshot is empty although the golden contract says conditions are present; this is a fixture/contract inconsistency, not a production-planner failure to solve by guessing.
- GT-068: lexical detection treated Vietnamese `r?i` as the `roi` physical-impact marker, producing an unsupported physical-impact claim; the planner also lacked a specific action-dependent presentation.

No retrieval or Judge configuration was changed.
