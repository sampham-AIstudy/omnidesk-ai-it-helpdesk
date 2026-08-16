# Product current state v1.10.1 — 2026-08-16

This version supersedes v1.10 following the successful resolution and verification of **SEC-GATE-1** (Production Demo Account & Secret Hardening).

## Production Security Hardening (SEC-GATE-1)

- **Environment-Scoped Demo Seeding:**
  - `APP_ENV=production`: Predictable demo accounts (`demo123`, `admin123`) are **disabled by default**. Clean production bootstrap creates 0 demo users.
  - `APP_ENV=development` / `test`: Demo seeding remains enabled for local development workflows.
  - Explicit override: `ENABLE_DEMO_SEED=true/false` is supported.
- **Initial Production Administrator Provisioning:**
  - In production, an administrator account can be securely provisioned via environment variables: `INITIAL_ADMIN_EMAIL`, `INITIAL_ADMIN_USERNAME`, `INITIAL_ADMIN_PASSWORD`, `INITIAL_ADMIN_FULL_NAME`.
  - Zero hardcoded passwords; passwords are never exposed in logs.
- **JWT Secret Validation:**
  - In `APP_ENV=production`, startup validation rejects empty, placeholder, or short (<32 chars) secrets.
- **CORS Hardening:**
  - In `APP_ENV=production`, wildcard `*` with credentials is strictly rejected; an explicit origin whitelist is required.
- **Frontend Demo Login Hardening:**
  - In `APP_ENV=production`, 1-click demo login buttons and hint footnotes are hidden, presenting only the enterprise manual authentication form.

## Runtime Release Gate

The product remains **RUNTIME_STABLE**, **AI_CORE_STABLE**, and **BUSINESS_CORE_STABLE**:

- **SEC-GATE-1 Tests:** 7/7 passed (100%).
- **Production Workflows E2E:** 18/18 passed (100%).
- **Service Request E2E:** 25/25 passed (100%).
- **Frozen Eval:** 93/93 passed (100%).
- **Auth API Tests:** 8/8 passed (100%).
- **Frontend Static Checks & Build:** ESLint 0 errors, TypeScript 0 errors, Product Guards PASS, Webpack production build PASS (46 pages).
- **Python Compilation (`compileall`):** PASS (0 errors).

## Registered Architectural Capabilities

- `ADMIN_USER_LIFECYCLE`: **DONE / DO_NOT_REIMPLEMENT**
- `SERVICE_REQUEST_APPROVAL`: **DONE / DO_NOT_REIMPLEMENT**
- `TECHNICIAN_FULFILLMENT_GROUPS`: **DONE / DO_NOT_REIMPLEMENT**
- `ACTION_GROUNDING`: **DONE / DO_NOT_REIMPLEMENT**
- `SR_ROUTING`: **DONE / DO_NOT_REIMPLEMENT**
- `CANONICAL_CHROMA_EMBEDDING`: **DONE / DO_NOT_REIMPLEMENT**
- `WORKSPACE_RECENT_CONTEXT`: **DONE / DO_NOT_REIMPLEMENT**
- `TICKET_RECENT_CONTEXT`: **DONE / DO_NOT_REIMPLEMENT**
- `CONTEXT_AWARE_RETRIEVAL_QUERY`: **DONE / DO_NOT_REIMPLEMENT**
- `SERVICE_REQUEST_PROCESS_KNOWLEDGE`: **DONE / DO_NOT_REIMPLEMENT**
- `PRODUCTION_SECRET_HARDENING`: **DONE / DO_NOT_REIMPLEMENT**
