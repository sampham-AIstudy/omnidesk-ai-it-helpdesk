# Zero-Mem episodic memory

The system keeps two distinct retrieval domains:

- Knowledge memory: enterprise KB/runbooks in the existing Chroma collection.
- Episodic memory: original ticket reports and conversation messages.

Episodic text is never summarized, rewritten, classified, or reranked by an LLM. `episodic_memory_traces` only holds provenance, access boundary, ordering and a content hash. The original text remains in `tickets` and `ticket_messages`.

For each query, deterministic parsing creates a query profile. Dense retrieval uses the existing Chroma client and embedding backend; lexical retrieval uses SQLite FTS5 when available; entity-to-trace rows provide the relational view. The system normalizes and fuses those signals, adds a bounded same-ticket message neighbourhood, then rechecks tenant/RBAC/provenance before the final QA LLM sees evidence. Historical text is explicitly labelled as data, never as instructions.

Run a one-time backfill after deployment for legacy history:

```powershell
.\.venv\Scripts\python.exe scripts\rebuild_episodic_memory.py
```

New tickets, all ticket messages, and resolved ticket updates are indexed automatically. The `memory_retrieved` audit action stores latency/candidate/evidence counts and the invariant `memory_llm_calls = memory_llm_tokens = 0`; it does not store the raw query.

The paper's headline latency reduction is benchmark-specific and is not claimed for this application. Use production audit telemetry and the existing retrieval evaluation suite to compare before/after on representative Help Desk queries.
