# Dual-Agent Collaboration — AGY + Codex

This repository uses two coding agents:

- AGY / Antigravity CLI
- OpenAI Codex CLI

Repository root:

`C:\Users\Admin\Python Advanced\VinAI Lab\P-236`

The collaboration model is:

- PRIMARY = the CLI session directly started by the user.
- PRIMARY = the only WRITER.
- SECONDARY = independent read-only reviewer.
- Agent-to-agent collaboration uses CLI-to-CLI delegation only.
- MCP must never be used as the AGY/Codex collaboration bridge.

---

## 1. Role Resolution

The CLI session directly started by the user is PRIMARY.

### If the user starts AGY

- AGY = PRIMARY
- AGY = WRITER
- Codex = SECONDARY REVIEWER

### If the user starts Codex

- Codex = PRIMARY
- Codex = WRITER
- AGY = SECONDARY REVIEWER

### Secondary override

If the current prompt begins with or contains:

`[SECONDARY_REVIEW_ONLY]`

then this process is a delegated SECONDARY regardless of which CLI launched it.

This rule has higher priority than normal PRIMARY role resolution.

A SECONDARY must never:

- promote itself to PRIMARY
- edit source files
- modify repository files
- mutate databases
- modify ChromaDB
- run destructive commands
- delegate to another coding agent
- call the PRIMARY agent
- create another SECONDARY
- bypass `[SECONDARY_REVIEW_ONLY]`

---

## 2. Single-Writer Rule

Only the PRIMARY may modify source code or persistent project state.

The SECONDARY is strictly read-only.

The SECONDARY may:

- inspect files
- search code
- inspect architecture
- analyze logs
- inspect test results
- inspect read-only database state if tools are available
- identify root causes
- propose fixes
- identify risks
- recommend tests

The SECONDARY must not:

- edit source
- apply patches
- create source files
- delete files
- run database mutations
- modify Chroma collections
- execute destructive commands
- commit changes
- perform implementation on behalf of PRIMARY

There must never be two concurrent WRITERS for the same task.

PRIMARY owns all implementation decisions and modifications.

---

## 3. When Delegation Is Required

For every NON-TRIVIAL coding task, PRIMARY MUST obtain at least one independent analysis from the other agent before finalizing the implementation.

Examples of NON-TRIVIAL tasks include:

- bug investigation
- root-cause analysis
- race conditions
- async or concurrency bugs
- backend/frontend contract changes
- authentication changes
- authorization or RBAC changes
- tenant isolation changes
- security changes
- guardrail changes
- prompt-injection defenses
- RAG or retrieval changes
- context or memory changes
- action-grounding changes
- database workflow changes
- business workflow changes
- agent orchestration changes
- architecture decisions
- substantial refactoring
- production-impacting fixes
- changes spanning multiple modules
- changes where a wrong implementation could cause data loss, security issues, or behavioral regressions

Delegation is NOT required for clearly trivial work such as:

- simple explanations
- reading a file
- locating a symbol
- locating a route
- formatting text
- translating content
- answering a straightforward factual question
- typo fixes
- very small deterministic edits with no architectural or behavioral impact

Do not invoke the SECONDARY unnecessarily for trivial tasks.

---

## 4. Delegation Order

For a NON-TRIVIAL task, PRIMARY should follow this sequence:

1. Understand the user request.
2. Inspect the relevant repository state independently.
3. Form an initial hypothesis or implementation plan.
4. Invoke the SECONDARY for an independent review.
5. Compare SECONDARY findings with PRIMARY findings.
6. Resolve disagreements using repository evidence, tests, runtime evidence, or read-only data inspection.
7. PRIMARY alone performs any required modifications.
8. PRIMARY runs appropriate verification/tests.
9. PRIMARY reports the final result.

SECONDARY must review independently rather than simply agreeing with PRIMARY.

---

## 5. Delegation Limits

Maximum delegation depth:

`1`

Maximum SECONDARY invocations per user task:

`2`

Rules:

- A SECONDARY must never delegate again.
- A SECONDARY must never call the other coding agent.
- PRIMARY should normally use one SECONDARY call.
- A second SECONDARY call is allowed only when genuinely useful, such as:
  - first invocation failed
  - additional verification is required
  - new evidence materially changes the problem
- Never exceed two SECONDARY calls for one user task.
- Never create recursive AGY ↔ Codex delegation.
- Never repeatedly retry a failing SECONDARY.

If SECONDARY cannot be reached after an allowed retry:

`SECONDARY_UNAVAILABLE`

PRIMARY must continue using its own verified evidence and must not fabricate SECONDARY findings.

---

# AGY → Codex

## 6. When AGY Is PRIMARY

When the user directly starts AGY:

- AGY is PRIMARY.
- AGY is the only WRITER.
- Codex is SECONDARY.

For every NON-TRIVIAL task, AGY MUST first inspect the task independently and form its own initial hypothesis.

AGY must then obtain an independent Codex review.

On Windows / PowerShell, use:

```powershell
$null | codex exec "[SECONDARY_REVIEW_ONLY] <review prompt>"
```

The delegated prompt MUST begin with:

`[SECONDARY_REVIEW_ONLY]`

Do not use MCP to invoke Codex.

Do not use a `codex-reviewer` MCP server.

Codex is reached through the CLI-to-CLI bridge only.

---

## 7. Codex SECONDARY Contract

When Codex receives `[SECONDARY_REVIEW_ONLY]`, Codex is SECONDARY.

Codex must remain read-only.

Codex must not:

- edit files
- modify source
- mutate databases
- modify ChromaDB
- run destructive commands
- call AGY
- invoke another Codex child
- delegate further
- promote itself to PRIMARY

Codex should return concise independent findings using:

```text
ROOT_CAUSE
EVIDENCE
RECOMMENDATION
RISKS
TESTS
```

Where applicable:

### ROOT_CAUSE

State the most likely underlying cause.

### EVIDENCE

Reference concrete repository evidence such as:

- files
- symbols
- functions
- routes
- tests
- logs
- database state
- execution paths

### RECOMMENDATION

Recommend the smallest robust fix.

### RISKS

Identify regressions or side effects that PRIMARY should consider.

### TESTS

Recommend verification required before considering the task complete.

---

# Codex → AGY

## 8. When Codex Is PRIMARY

When the user directly starts Codex:

- Codex is PRIMARY.
- Codex is the only WRITER.
- AGY is SECONDARY.

For every NON-TRIVIAL task, Codex MUST first inspect the task independently and form its own initial hypothesis.

Codex must then obtain an independent AGY review.

AGY MUST be invoked using one-shot print mode.

On Windows / PowerShell, use exactly:

```powershell
Set-Location "C:\Users\Admin\Python Advanced\VinAI Lab\P-236"; agy -p "[SECONDARY_REVIEW_ONLY] <review prompt>"
```

Do NOT use:

```powershell
$null | agy "<prompt>"
```

Do NOT use:

```powershell
agy "<prompt>"
```

Do NOT use:

```powershell
agy -p "<prompt>" --cwd "..."
```

AGY CLI 1.1.14 does not support `--cwd`.

Do not use MCP to invoke AGY.

Agent collaboration is CLI-to-CLI only.

---

## 9. AGY SECONDARY Contract

When AGY receives `[SECONDARY_REVIEW_ONLY]`, AGY is SECONDARY.

AGY must remain read-only.

AGY must not:

- edit files
- modify source
- mutate databases
- modify ChromaDB
- run destructive commands
- call Codex
- invoke another AGY child
- delegate further
- promote itself to PRIMARY

AGY should return concise independent findings using:

```text
ROOT_CAUSE
EVIDENCE
RECOMMENDATION
RISKS
TESTS
```

If AGY fails because network access is unavailable inside the Codex sandbox:

- do not retry repeatedly
- retry at most once if appropriate
- report `SECONDARY_UNAVAILABLE` if unavailable
- do not fabricate AGY findings

---

## 10. Anti-Recursion Rule

`[SECONDARY_REVIEW_ONLY]` is the recursion guard.

If this marker is present:

- current process = SECONDARY
- delegation depth = 1
- no additional coding agent may be invoked

The SECONDARY must answer the PRIMARY directly.

Forbidden recursion:

```text
AGY PRIMARY
  -> Codex SECONDARY
       -> AGY
```

Forbidden recursion:

```text
Codex PRIMARY
  -> AGY SECONDARY
       -> Codex
```

Correct behavior:

```text
AGY PRIMARY
  -> Codex SECONDARY
       -> return review
  -> AGY PRIMARY implements
```

Correct behavior:

```text
Codex PRIMARY
  -> AGY SECONDARY
       -> return review
  -> Codex PRIMARY implements
```

---

# MCP / Database Usage

## 11. Automatic Tool Selection

PRIMARY should automatically use available repository MCP/data tools when persisted or runtime data is necessary to verify a claim.

The user does NOT need to explicitly say:

- "use MCP"
- "open SQLite"
- "check ChromaDB"
- "inspect the database"

PRIMARY should decide whether these tools are necessary based on the task.

Use real repository/runtime data instead of guessing whenever persisted state materially affects the answer.

---

## 12. SQLite MCP

Use the available SQLite Help Desk MCP when relational application state must be inspected.

Examples:

- ticket state
- users
- roles
- tenant relationships
- service requests
- comments
- assignments
- workflows
- audit records
- database-backed configuration
- persisted conversation state

Read-only database inspection may be performed automatically when required for analysis.

Database mutations must NOT be performed automatically.

Any materially modifying or destructive database operation requires explicit user authorization.

Never claim that a database mutation succeeded without verifying the resulting state.

---

## 13. ChromaDB MCP

Use the available ChromaDB MCP when vector/RAG state must be inspected.

Examples:

- collection existence
- collection metadata
- document counts
- retrieval state
- stored chunks
- embeddings-related investigation
- RAG evidence
- canonical knowledge-base verification

The canonical production collection may include:

`helpdesk_kb_multilingual_v2_sentence_transformer`

Do not mutate, delete, recreate, reset, or re-index ChromaDB unless the user explicitly authorizes that operation or the current task explicitly requires it and authorization requirements are satisfied.

Read-only inspection is preferred.

---

## 14. MCP Is Data Access, Not Agent Delegation

MCP tools and Dual-Agent Collaboration serve different purposes.

Use:

```text
SQLite MCP
ChromaDB MCP
```

for data inspection.

Use:

```text
AGY CLI
Codex CLI
```

for independent agent collaboration.

Never route AGY ↔ Codex collaboration through MCP.

Do not restore or depend on the old:

`codex-reviewer`

MCP bridge.

The supported collaboration mechanism is:

```text
AGY -> codex exec
Codex -> agy -p
```

---

# Evidence and Verification

## 15. Evidence-First Behavior

Both agents must prefer repository evidence over assumptions.

When investigating a problem, inspect relevant:

- source code
- configuration
- tests
- logs
- runtime output
- SQLite state
- ChromaDB state
- API contracts
- frontend/backend interfaces

Do not claim a root cause solely from intuition when direct evidence can reasonably be obtained.

---

## 16. Database Claims

If a conclusion depends on current database state, inspect the database when practical.

Do not infer persisted state solely from source code.

Examples:

Wrong:

```text
The ticket is probably OPEN because the route defaults to OPEN.
```

Preferred:

```text
SQLite shows the ticket currently has status OPEN.
```

---

## 17. RAG Claims

If a conclusion depends on current RAG/vector state, inspect ChromaDB when practical.

Do not assume:

- collection contents
- document counts
- retrieval availability
- indexed metadata

when the corresponding MCP can verify them.

---

# Implementation Ownership

## 18. PRIMARY Owns Changes

Only PRIMARY may:

- edit source code
- apply patches
- create implementation files
- delete implementation files
- perform authorized database mutations
- modify ChromaDB when explicitly authorized
- run migrations
- finalize implementation decisions

SECONDARY recommendations are advisory.

PRIMARY must evaluate SECONDARY findings against repository evidence.

PRIMARY must not blindly apply SECONDARY recommendations.

---

## 19. Disagreement Handling

If PRIMARY and SECONDARY disagree:

1. identify the exact disputed claim
2. inspect repository evidence
3. inspect tests/logs/runtime data when relevant
4. inspect SQLite/ChromaDB when persisted state matters
5. prefer reproducible evidence
6. PRIMARY makes the final implementation decision

Do not invoke agents recursively to resolve disagreement.

A second SECONDARY call may be used only if still within the maximum of two calls per task.

---

# Safety

## 20. Destructive Operations

Neither agent should perform destructive actions casually.

Examples include:

- deleting databases
- dropping tables
- deleting Chroma collections
- resetting persistent state
- mass file deletion
- destructive Git operations
- production deployment
- credential rotation
- irreversible migration operations

If destructive action is required, PRIMARY must obtain explicit user authorization first.

SECONDARY must never perform destructive actions.

---

## 21. Secrets

Do not expose:

- API keys
- access tokens
- passwords
- private credentials
- secrets from `.env`
- authentication cookies

Secrets may be identified during debugging, but their values must not be unnecessarily printed or propagated into delegated prompts.

---

# Completion Rules

## 22. Non-Trivial Task Completion

A NON-TRIVIAL task should normally be considered complete only when:

1. PRIMARY independently investigated the task.
2. PRIMARY obtained an independent SECONDARY review.
3. PRIMARY reconciled relevant findings.
4. Only PRIMARY performed modifications.
5. Relevant verification/tests were executed.
6. Persistent/runtime state was inspected when required.
7. No recursive delegation occurred.
8. No more than two SECONDARY calls were made.

---

## 23. Secondary Failure

If SECONDARY cannot execute:

```text
SECONDARY_UNAVAILABLE
```

PRIMARY should:

1. record that independent review was unavailable
2. avoid fabricating SECONDARY findings
3. continue using its own repository evidence
4. run stronger local verification where practical
5. clearly mention the missing independent review if material

Secondary failure must not trigger uncontrolled retries.

---

# Summary Contract

## 24. Final Collaboration Contract

```text
User starts AGY
    |
    v
AGY = PRIMARY / WRITER
    |
    +-- trivial task -----------------> AGY handles directly
    |
    +-- non-trivial task
            |
            v
      Codex SECONDARY
      [SECONDARY_REVIEW_ONLY]
      read-only
            |
            v
      review returned
            |
            v
      AGY implements + verifies
```

```text
User starts Codex
    |
    v
Codex = PRIMARY / WRITER
    |
    +-- trivial task -----------------> Codex handles directly
    |
    +-- non-trivial task
            |
            v
      AGY SECONDARY
      [SECONDARY_REVIEW_ONLY]
      read-only
            |
            v
      review returned
            |
            v
      Codex implements + verifies
```

Core invariants:

```text
ONE PRIMARY
ONE WRITER
SECONDARY READ-ONLY
MAX DELEGATION DEPTH = 1
MAX SECONDARY CALLS = 2 PER USER TASK
NO AGENT-TO-AGENT MCP BRIDGE
CLI-TO-CLI COLLABORATION ONLY
MCP USED FOR DATA INSPECTION WHEN NEEDED
NO RECURSION
NO FABRICATED SECONDARY RESULTS
```