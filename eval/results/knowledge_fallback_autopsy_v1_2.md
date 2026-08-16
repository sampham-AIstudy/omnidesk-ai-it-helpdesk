# Knowledge Fallback Mechanism Autopsy v1.2

Read-only trace: no production behavior, retrieval, prompt, Judge, golden or snapshot change.

## Fallback locations

| Location | Trigger | Origin | Used by |
| --- | --- | --- | --- |
| src/prompts/helpdesk_rag.py:28-29 | Authorized evidence is incomplete or does not support an important requested part. | PROMPT_INSTRUCTED_FALLBACK | standard chat, streaming chat, ticket conversation, ticket RAG synthesis |
| src/api/chat.py:413,598 | No retained internal RAG document after retrieval/filtering. | CONTEXT_EMPTY_FALLBACK | standard and streaming chat prompt construction; placeholder context only, not final answer |
| src/api/chat.py:457,633 | LLM invocation raises, or streaming emits no raw content. | DETERMINISTIC_PRE_GENERATION_FALLBACK | standard and streaming chat final reply |
| src/agents/nodes/rag_node.py:40-94 | No ticket KB documents, low relevance, unavailable external research, or failed external synthesis. | RETRIEVAL_CONFIDENCE_FALLBACK | ticket-agent RAG workflow only |
| src/agents/nodes/rag_node.py:220-233 | Ticket-agent synthesis emits an INSUFFICIENT_KB_MARKER. | POST_GENERATION_REPLACEMENT | ticket-agent RAG workflow only |
| src/services/ticket_conversation_service.py:497-501 | Ticket conversation LLM invocation raises. | DETERMINISTIC_PRE_GENERATION_FALLBACK | ticket conversation only |
| eval/knowledge_completeness_canary.py:generation_prompt | Never: fixed context is passed directly; no answerability, confidence, template, or post-generation fallback branch exists. | NO_DETERMINISTIC_FALLBACK | clean-control-equivalent canary evaluation only |

## Case timelines

| ID | Snapshot | Route | First wrong decision | Root cause |
| --- | --- | --- | --- | --- |
| GT-020 | FULL_SUPPORT | incident | LLM_IGNORED_VALID_CONTEXT | LLM_IGNORED_VALID_CONTEXT |
| GT-029 | PARTIAL_SUPPORT | incident | LLM_IGNORED_VALID_CONTEXT | LLM_IGNORED_VALID_CONTEXT |
| GT-046 | EMPTY | knowledge | GENERIC_FALLBACK_TOO_EAGER | GENERIC_FALLBACK_TOO_EAGER |
| GT-067 | PARTIAL_SUPPORT | action_request | LLM_IGNORED_VALID_CONTEXT | LLM_IGNORED_VALID_CONTEXT |
| GT-077 | EMPTY | knowledge | GENERIC_FALLBACK_TOO_EAGER | GENERIC_FALLBACK_TOO_EAGER |
| GT-087 | EMPTY | knowledge | GENERIC_FALLBACK_TOO_EAGER | GENERIC_FALLBACK_TOO_EAGER |
| GT-049 | FULL_SUPPORT | knowledge | OTHER_VERIFIED | OTHER_VERIFIED |
| GT-047 | PARTIAL_SUPPORT | incident | NONE | NONE |
| GT-048 | PARTIAL_SUPPORT | incident | NONE | NONE |
| GT-027 | FULL_SUPPORT | incident | NONE | NONE |

## Findings

- **standard_chat_answerability_gate**: No pre-generation answerability or retrieval-confidence branch returns a generic fallback. retrieval confidence is only used for document filtering, web-research decision and telemetry.
- **fixed_context_evaluation_path**: No deterministic fallback/template/answerability branch exists after fixed context is supplied. The generator receives every retained snapshot source through build_authorized_evidence.
- **sanitizer**: No inspected frozen target/reference source was modified by redact_untrusted_instructions.
- **postprocessing**: content_filter and citation cleanup redact/format/remove invalid citation labels; neither selects a generic insufficient-information answer.
- **ticket_agent_separation**: Ticket-agent rag_node does contain deterministic relevance and post-synthesis fallback branches, but the v1.2 fixed-context generation suite does not execute that graph.

## Root causes

| Root cause | Count | Cases |
| --- | ---: | --- |
| GENERIC_FALLBACK_TOO_EAGER | 3 | GT-046, GT-077, GT-087 |
| LLM_IGNORED_VALID_CONTEXT | 3 | GT-020, GT-029, GT-067 |
| OTHER_VERIFIED | 1 | GT-049 |

## One recommended next canary

- **GENERATOR_EVIDENCE_USE_CANARY**
- Scope: Only nonempty valid-context cases GT-020, GT-029 and GT-067, with GT-027, GT-047 and GT-048 as controls.
- Reason: The fixed-context trace preserves evidence and contains no deterministic fallback gate; the first wrong decision is the generator selecting broad abstention despite valid context. Empty-context claim-specific abstention is a separate primitive and must not be bundled.