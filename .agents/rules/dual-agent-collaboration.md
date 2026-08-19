---
activation: always
---

# AGY + Codex Collaboration

Follow the Dual-Agent Collaboration policy in `/AGENTS.md`.

When this AGY session is PRIMARY and receives a non-trivial coding task:

1. Analyze the task independently first.
2. Invoke Codex exactly once for an independent read-only review.
3. On Windows / PowerShell, invoke Codex using:

   `$null | codex exec "<SECONDARY_REVIEW_ONLY prompt>"`

   Do NOT use plain:

   `codex exec "<prompt>"`

   because stdin may remain open and cause the Codex child process to hang or return `context canceled`.

4. Every delegated Codex prompt MUST start with:

   `[SECONDARY_REVIEW_ONLY]`

5. The Codex child is READ-ONLY by policy. It must:
   - inspect the same repository
   - analyze independently
   - not edit files
   - not mutate the database
   - not run destructive commands
   - not call AGY again
   - return concise findings:
     - ROOT_CAUSE
     - EVIDENCE
     - RECOMMENDATION
     - RISKS
     - TESTS

6. AGY remains the PRIMARY and the only source-code writer by default.

7. After receiving the Codex result:
   - compare AGY's own finding with Codex's finding
   - resolve disagreements using source code, runtime reproduction, and tests
   - choose the final implementation
   - then modify the source only once

8. After implementation, AGY may invoke Codex one additional time for final diff/regression review.

9. Maximum Codex calls per user task = 2.

10. Maximum delegation depth = 1.

11. Never allow:

   AGY
   → Codex
   → AGY
   → Codex

   Only allow:

   AGY PRIMARY
   → Codex SECONDARY
   → AGY PRIMARY

12. Never let AGY and Codex modify repository files concurrently.

13. Parallel work is allowed only for:
   - reading
   - searching
   - reasoning
   - root-cause analysis
   - test design
   - code review

14. If the task is trivial, such as:
   - simple explanation
   - reading a file
   - formatting text
   - answering a straightforward question

   AGY does not need to invoke Codex.

15. If this AGY invocation itself contains:

   `[SECONDARY_REVIEW_ONLY]`

   then AGY is already the delegated SECONDARY.

   In that case:
   - DO NOT call Codex
   - DO NOT modify files
   - DO NOT mutate databases
   - DO NOT perform destructive operations
   - return review findings only

16. For non-trivial coding tasks, final output should include:

   PRIMARY:
   SECONDARY:
   PRIMARY_FINDING:
   SECONDARY_FINDING:
   FINAL_DECISION:
   WRITER:
   FILES_CHANGED:
   TEST_RESULT: