# Golden evaluation

`helpdesk_golden_dataset_v2.json` contains synthetic, non-confidential cases for direct troubleshooting, vague reports, temporal/relational history, missing knowledge, current vendor knowledge, RBAC, PII, prompt injection, DLP exfiltration, approval bypass, and critical healthcare incidents.

The evaluator measures three primary axes:

- Context coverage: whether retrieval contains the evidence needed to answer.
- Faithfulness: whether the answer stays within evidence and does not invent unsafe facts.
- Answer focus: whether the answer directly follows the requested/safe behaviour.

Run deterministic evaluation:

```powershell
.\.venv\Scripts\python.exe eval\ragas_assessment_eval.py --cases eval\helpdesk_golden_dataset_v2.json --generate-answers
```

To generate answers with the configured application model, add `--generate-answers`. To have an independent, OpenAI-compatible judge score the same synthetic rows, configure `EVAL_JUDGE_API_KEY` and `EVAL_JUDGE_MODEL`, then explicitly opt in. The judge returns `faithfulness_score`, `relevance_score`, `completeness_score`, `abstention_score`, `overall_score`, `passed`, and diagnostics. The application recalculates the weighted score and hard gates locally, so a provider cannot self-approve a hallucinated answer or an ungrounded action. If those settings are blank, `NVIDIA_API_KEY` automatically uses NVIDIA NIM with the responsive `meta/llama-3.1-8b-instruct`; this affects evaluation only, never production ticket generation. Set `NVIDIA_EVAL_JUDGE_MODEL=meta/llama-3.3-70b-instruct` only for an offline benchmark where its longer latency is acceptable.

```powershell
.\.venv\Scripts\python.exe eval\ragas_assessment_eval.py --cases eval\helpdesk_golden_dataset_v2.json --generate-answers --judge-external --allow-external-judge
```

By default, the external judge receives only synthetic test data, the candidate answer, expected behaviour, and retrieved **titles**. This keeps KB text local, but title-only input cannot reliably validate grounding. Run the faithfulness gate with `--allow-external-evidence` only for a separately approved, synthetic KB fixture; never use it with production KB.

Never use the external judge with real ticket text, confidential KB entries, PII, credentials, or production traces. The evaluator refuses `--judge-external` without the acknowledgement flag.

## Official RAGAS metrics

The deterministic evaluator and NVIDIA external judge are the supported quality gates for this project. Do not pass `--use-ragas` with the current LangChain 1.x dependency stack: current RAGAS releases import a removed LangChain Community VertexAI module. This does not affect the deterministic scores or the NVIDIA external judge.
