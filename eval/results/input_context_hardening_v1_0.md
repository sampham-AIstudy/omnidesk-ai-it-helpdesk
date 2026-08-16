# HARDEN-1 — Input & Context Hardening Audit Report

**Date:** 2026-08-16  
**Milestone:** HARDEN-1  
**Status:** PASS  

---

## 1. Input Limits (Authoritative & Frontend)

- **Max Message Characters (`MAX_CHAT_MESSAGE_CHARS`):** 8,000 characters.
- **Max Message Encoded Bytes (`MAX_CHAT_MESSAGE_BYTES`):** 32,768 bytes (32 KB).
- **Max Chat Request Body Bytes (`MAX_CHAT_REQUEST_BYTES`):** 65,536 bytes (64 KB).
- **Enforcement:**
  - Fast fail with HTTP 413 (`INPUT_TOO_LARGE`) executed **before** router, embedding, RAG, ZeroMem, query rewrite, or LLM invocation.
  - Pydantic schema validation updated to `max_length=8000`.

---

## 2. Frontend Protection & User Experience

- **Workspace Chat (`frontend/src/app/employee/chatbot/page.tsx`):**
  - Interactive live character counter (`{input.length} / 8.000`).
  - Warning styling applied when `input.length >= 7000`.
  - Send button disabled when `input.length > 8000`.
  - `onPaste` handler detects oversized clipboard payloads and displays an explicit error toast/banner without silently truncating user input.
- **Ticket Chat (`frontend/src/app/employee/tickets/[id]/page.tsx`):**
  - Character counter (`{message.length} / 8.000`), warning state at 7000 chars, send button disabled if > 8000.
  - `onPaste` handler warns on oversized pasted content.
- **Quick Floating Widget (`frontend/src/components/AIChatWidget.tsx`):**
  - Character counter and 8000 character limit enforcement.

---

## 3. Request Body Size Guard (ASGI Middleware)

- **Middleware (`src/guardrails/request_size_guard.py`):**
  - Intercepts requests before reaching downstream FastAPI routes.
  - Checks `Content-Length` header against 64 KB (chat endpoints) / 1 MB (general endpoints).
  - Streams incoming body chunks; if accumulated byte count exceeds the threshold (e.g., chunked transfer or omitted header), immediately aborts and returns HTTP 413 (`INPUT_TOO_LARGE`).

---

## 4. History Resource Limits & Memory Preservation

- **Recent Message Limits:**
  - Workspace: max 8 messages.
  - Ticket: max 5 messages.
- **Character Budgets:**
  - `MAX_HISTORY_MESSAGE_CHARS`: 4,000 characters per history message.
  - `MAX_WORKSPACE_RECENT_HISTORY_CHARS`: 16,000 characters total history budget.
  - `MAX_TICKET_RECENT_HISTORY_CHARS`: 12,000 characters total history budget.
- **Bounding Strategy:**
  - Messages loaded newest-first; older turns are dropped when the character budget is reached (prioritizing newest messages).
  - Current user query is never truncated or dropped.
  - Zero LLM summarization used (preserves exact verbatim transcript integrity).

---

## 5. Rate & Concurrency Abuse Protection

- **Guard (`src/guardrails/ai_abuse_guard.py`):**
  - **Rate Limit:** 20 AI requests / minute / authenticated user (sliding window).
  - **Concurrency Limit:** Max 2 concurrent active AI generations per authenticated user.
  - **Response:** HTTP 429 (`RATE_LIMITED` / `CONCURRENCY_LIMIT_EXCEEDED`) with no LLM invocation.
  - **Architecture:** Thread-safe, asyncio-native in-memory tracker (zero mandatory Redis dependency).

---

## 6. Timeouts & SSE Resilience

- **LLM Timeout:** `ChatMistralAI`, `ChatOpenAI`, `ChatGroq`, and `ChatGoogleGenerativeAI` configured with 30s finite timeouts.
- **Web Research:** `DuckDuckGoHtmlProvider` runs with 8s finite timeout.
- **SSE Client Disconnect:** `stream_chat_with_agent` checks `await request.is_disconnected()` per token emission to break immediately upon client disconnect, avoiding runaway background generation loops.

---

## 7. Other User Text Field Schema Hardening

- `TicketCreate.title`: `max_length=200`
- `TicketCreate.description`: `max_length=5000` (reduced from unbounded 100,000)
- `DuplicateCheckRequest.title`: `max_length=200`
- `DuplicateCheckRequest.description`: `max_length=5000`
- `ServiceRequestCreate.service_name`: `max_length=200`
- `ServiceRequestApprovalDecision.comment`: `max_length=2000`
- `ServiceRequestRejectionDecision.reason`: `max_length=2000`
- `KBEntryCreate.content` / `KBEntryUpdate.content`: `max_length=50000`

---

## 8. Verification & Test Results

- **Hardening Suite (`tests/test_hardening.py`):** 13/13 tests PASSED (100%).
- **Service & Retrieval Suite:** 33/33 tests PASSED (100%).
- **Production & E2E Suites:** 41/41 tests PASSED (100%).
- **Frozen Eval Suites:** 93/93 tests PASSED (100%).
- **Frontend Quality:**
  - ESLint: 0 errors.
  - TypeScript (`tsc --noEmit`): 0 errors.
  - Product Guards: PASSED.
  - Webpack Production Build: PASSED.

---

## 9. Blockers

- **0 BLOCKERS**: All input and context attack vectors, multi-MB payload bloats, and AI generation abuse patterns are completely mitigated.

---

## 10. Verdicts

```
INPUT_ABUSE_PROTECTION: PASS
CONTEXT_RESOURCE_PROTECTION: PASS
FINAL_SECURITY_HARDENING: PASS
PRODUCTION_DEPLOY_READY: YES
```
