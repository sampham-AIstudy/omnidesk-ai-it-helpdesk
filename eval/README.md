# Evaluation Framework & Quality Assurance

This directory contains the authoritative evaluation framework, golden datasets, fixtures, deterministic context snapshots, and release gate locks for the VinAI Help Desk AI Agent system.

---

## 1. System Overview & Architecture

The evaluation framework follows a strict **layer-separated, regression-locked architecture** designed to verify enterprise contracts independently without confounding variables:

- **Routing Layer**: Evaluates intent classification, tool invocation decisions, knowledge retrieval necessity, web research fallback, and memory usage.
- **Retrieval Layer**: Evaluates dense semantic, lexical BM25, Reciprocal Rank Fusion (RRF), source authority weighting, and cross-tenant / ACL isolation against ChromaDB collections.
- **Generation & Grounding Layer**: Evaluates response faithfulness, citation validity (`[doc-id]`), precise partial-answer grounding, and correct abstention under missing knowledge.
- **Security & Guardrail Layer**: Evaluates defenses against prompt injection, unauthorized privilege escalation, secret/credential leakage, and cross-tenant data exfiltration.
- **Workflow & Action State Machine**: Evaluates ticket creation, state transitions, human-in-the-loop (HITL) escalations, and strict confirmation semantics.

---

## 2. Canonical Evaluators & Gate Commands

| Evaluator / Gate | Entrypoint Command | Output Report / Lock | Core Responsibility |
|---|---|---|---|
| **Golden Enterprise 300** | `.\.venv\Scripts\python.exe eval\baseline_v1.py --output-json eval\results\golden_300_evaluation_current.json --output-md eval\results\golden_300_evaluation_current.md` | `eval/results/golden_300_evaluation_current.json` & `.md` | Evaluates all 300 enterprise cases against frozen deterministic context snapshot. Baseline target: **300 PASS / 0 FAIL**. |
| **Enterprise Controlled Runtime** | `.\.venv\Scripts\python.exe eval\enterprise_runtime_v1_0.py` | `eval/results/enterprise_runtime_v1_0.json` | Comprehensive 10-layer runtime harness with isolated fixtures. Target: **298 PASS / 0 PRODUCT_FAILURE / 0 FIXTURE_INCOMPLETE / 2 CONTRACT_CONFLICT**. |
| **Retrieval Regression Gate** | `.\.venv\Scripts\python.exe scripts\run_retrieval_gate.py` | `eval/results/retrieval_authority_lock_v1_0.json` & `.md` | Evaluates 44 scorable cases directly against active Chroma collection (`helpdesk_kb_multilingual_v3_sentence_transformer`). Enforces zero cross-tenant leaks and zero policy violations. |
| **Behavior Regression Gate** | `.\.venv\Scripts\python.exe scripts\run_behavior_gate.py` | Console Summary & Pytest Report | Enforces 130 behavioral invariant tests across single-turn and critical multi-turn chat flows. Target: **130 / 130 PASS**. |
| **Hard-Negative A/B Gate** | `.\.venv\Scripts\python.exe scripts\evaluate_p0_hard_negatives.py` | `eval/results/p0_shadow_v3_hard_negative_ab.json` | Evaluates 50 hard-negative confusable query pairs to ensure top-1 intent precision and rank-1 hard-negative avoidance. |
| **Production Gate v3 (Release Orchestrator)** | `.\.venv\Scripts\python.exe scripts\run_production_gate_v3.py` | `eval/results/production_gate_v3.json` | Top-level release gate orchestrating Enterprise runtime, Behavior gate, Retrieval gate, Hard-negative locks, and Full Pytest. |
| **Full Pytest Suite** | `.\.venv\Scripts\python.exe -m pytest -q` | Console Report | Full unit and integration regression suite. Target: **933 passed**. |

---

## 3. Directory Layout

```
eval/
├── README.md                                    # This framework documentation
├── RAG_EVALUATION_STRATEGY.md                   # RAG evaluation strategy and methodology
├── baseline_v1.py                               # Canonical Golden 300 baseline evaluator
├── enterprise_runtime_v1_0.py                   # Canonical Enterprise controlled runtime coordinator
├── enterprise_runtime_fixtures.py               # Enterprise evaluation database & mocking fixtures
├── contract_kb_fixture.py                       # Contract Chroma collection builder
├── retrieval_metrics.py                         # Shared retrieval evaluation & metric utilities
├── benchmark_ticket_async_evidence.py           # Repeatable benchmark for async evidence acquisition
├── benchmark_graph_assisted_rag.py              # Graph-assisted RAG benchmark (EXPERIMENT_ONLY non-promoted)
│
├── behavior/
│   ├── behavior_validator.py                    # Behavioral regression manifest validator
│   └── chat_behavior_manifest.json              # Canonical 30-case behavior regression manifest
│
├── judge/
│   ├── __init__.py                              # Judge package initialization
│   └── semantic_judge.py                        # Authoritative semantic LLM judge implementation
│
├── fixtures/
│   └── enterprise_contract_kb_v1.json           # Canonical contract KB documents fixture
│
├── snapshots/
│   ├── enterprise_runtime_snapshot_v1_0.json    # Canonical runtime snapshot for enterprise evaluation
│   ├── enterprise_context_snapshot_v1_2.json    # Canonical context snapshot for enterprise baseline
│   ├── canary_contract_v1_2_context_snapshot.json # Context snapshot for contract canary
│   ├── evaluation_lock_v1_2.json                # Locked evaluation snapshot
│   ├── evaluation_lock_v1_2_full.json           # Full locked evaluation snapshot
│   └── production_evaluation_lock_v1_0.json     # Production evaluation lock snapshot
│
├── results/                                     # Authoritative release evidence and regression locks
│   ├── enterprise_runtime_v1_0.json             # Current Enterprise runtime gate results
│   ├── golden_300_evaluation_current.json       # Current Golden 300 JSON report
│   ├── golden_300_evaluation_current.md         # Current Golden 300 Markdown report
│   ├── retrieval_authority_lock_v1_0.json       # Current Retrieval gate results JSON
│   ├── retrieval_authority_lock_v1_0.md         # Current Retrieval gate report Markdown
│   ├── production_gate_v3.json                  # Production gate v3 release report
│   ├── p0_v3_promotion.json                     # Knowledge base v3 promotion provenance
│   ├── adaptive_hard_negative_50_ab.json        # Hard-negative baseline regression lock
│   ├── adaptive_p0_11_ab.json                   # P0 shadow baseline regression lock
│   └── graph_rag_benchmark_v1_0.json            # Graph RAG experiment decision record
│
├── golden_testset_enterprise.json               # Canonical 300 Golden Enterprise test cases
├── evaluation_manifest.json                     # Canonical manifest locking test hashes & layer rules
├── retrieval_golden_v1.json                     # Canonical 44-case retrieval golden dataset
├── p0_shadow_v3_hard_negative_cases.json        # Canonical 50-case hard-negative test dataset
├── p0_shadow_v3_cases.json                      # Canonical 11-case P0 retrieval test dataset
├── context_completeness_v1.json                 # Context completeness evaluation dataset
├── calibration_enterprise_runtime_v1_0.json     # Semantic judge calibration dataset
└── known_judge_limitations_v1_0.json            # Documented known judge boundary conditions
```

---

## 4. Authoritative Datasets

1. **`golden_testset_enterprise.json`**: 300 comprehensive test cases covering employee self-service, IT troubleshooting, healthcare VIP incidents, policy queries, security red-teaming, approval workflows, and multi-turn conversations.
2. **`evaluation_manifest.json`**: Manifest locking dataset SHA-256 hashes, evaluation layers, fixture integrity requirements, and regression metric thresholds.
3. **`behavior/chat_behavior_manifest.json`**: Positive/negative paired behavior test cases verifying refusal, routing, tool safety, and clarification boundaries.
4. **`retrieval_golden_v1.json`**: 44 retrieval test cases spanning exact keyword tokens, typos, semantic queries, cross-lingual requests, and cross-tenant isolation probes.
5. **`p0_shadow_v3_hard_negative_cases.json`**: 50 challenging test cases with paired confusable documents to verify intent-routing discrimination.

---

## 5. Artifact Lifecycle & Cleanliness Policies

- **Ephemeral Cache Files**: Local LLM judge caches (`eval/results/judge_cache*/`) are ephemeral and ignored by `.gitignore`. Do not commit judge cache files to the repository.
- **No Intermediate Chunk Dumps**: Evaluators output consolidated, final reports (`golden_300_evaluation_current.json`, `retrieval_authority_lock_v1_0.json`, etc.). Intermediate slice or chunk files must be cleaned up after experiments.
- **Single-Writer Collaboration**: Per `AGENTS.md`, modifications to evaluation code, fixtures, and datasets must follow the primary agent workflow with independent secondary review.
