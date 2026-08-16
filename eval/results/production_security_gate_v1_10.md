# SEC-GATE-1 — Production Demo Account & Secret Hardening Report

**Date:** 2026-08-16  
**Milestone:** SEC-GATE-1  
**Status:** PASS / HARDENED  
**Deployment State:** STAGING & PRODUCTION BOOTSTRAP READY  

---

## 1. Executive Summary & Verdict

| Security Invariant | Requirement | Status | Verification Reference |
|---|---|---|---|
| **Demo Account Seeding Boundary** | `APP_ENV=production` must NOT auto-seed predictable demo accounts (`demo123`, `admin123`) | **ENFORCED** | `test_sec_prod_01_production_disables_demo_seed_by_default` (PASS) |
| **Initial Admin Provisioning** | Clean production DB provisions admin securely via `INITIAL_ADMIN_*` env vars | **ENFORCED** | `test_sec_prod_07_initial_admin_provisioning` (PASS) |
| **JWT Secret Enforcement** | `APP_ENV=production` rejects empty, default, or placeholder secrets (<32 chars) | **ENFORCED** | `test_sec_prod_03`, `test_sec_prod_04`, `test_sec_prod_05` (PASS) |
| **CORS Wildcard Rejection** | `APP_ENV=production` rejects wildcard `*` with credentials | **ENFORCED** | `test_sec_prod_06_production_wildcard_cors_rejected` (PASS) |
| **Frontend Demo Login UI** | Demo 1-click accounts & password hints hidden in production mode | **ENFORCED** | `frontend/src/app/login/page.tsx` conditional rendering (PASS) |
| **Development Convenience** | `APP_ENV=development` retains 1-click demo login & seed data | **PRESERVED** | `test_sec_prod_02` + E2E workflows pass |

```
SEC_GATE_1:              PASS
PRODUCTION_DEPLOY_READY: YES
```

---

## 2. Root Cause Analysis: Pre-Hardening Behavior

- **Previous Bootstrap Contract:** In `src/main.py` (`lifespan`), `_seed_demo_users(db)` was executed unconditionally on every startup.
- **Identified Production Risk:** A newly deployed production instance with an empty database would automatically create 7 demo accounts (`employee1`, `employee_vip`, `tech1`, `manager1`, `admin`, `employee_healthcare`, `employee_auto`) with static, predictable passwords (`demo123`, `admin123`), creating an immediate critical vulnerability.
- **Frontend Risk:** The login page displayed 1-click demo login buttons exposing demo usernames and passwords.

---

## 3. Hardening Changes Implemented

### 3.1 Backend Configuration (`src/config.py`)
- Added `enable_demo_seed: bool | None = None` with `@field_validator` supporting string booleans (`true`/`false`/`1`/`0`) and empty strings.
- Added computed property `is_demo_seed_enabled`: Defaults to `False` in `production`, and `True` in `development`/`test`.
- Added environment-based initial admin parameters:
  - `initial_admin_email: str = ""`
  - `initial_admin_username: str = "admin"`
  - `initial_admin_password: str = ""`
  - `initial_admin_full_name: str = "System Administrator"`
- Added `@model_validator(mode="after")` to enforce production security:
  - Rejects empty, short (<32 chars), or known placeholder JWT secrets.
  - Rejects wildcard `*` CORS origins.

### 3.2 Backend Lifespan (`src/main.py`)
- Wrapped demo user seeding with `if settings.is_demo_seed_enabled: await _seed_demo_users(db)`.
- Added `_provision_initial_admin(db, email, username, password, full_name)` to initialize a secure administrator in production without hardcoded credentials. Passwords are never logged.

### 3.3 Frontend Hardening (`frontend/src/app/login/page.tsx`, `frontend/next.config.ts`)
- Added `isDemoLoginEnabled = process.env.NEXT_PUBLIC_ENABLE_DEMO_LOGIN !== 'false' && process.env.NEXT_PUBLIC_APP_ENV !== 'production'`.
- Wrapped role tabs, demo 1-click account cards, and `DEMO123` footer hint inside `{isDemoLoginEnabled && (...)}`.
- In production, users see only the clean enterprise username/password form.

### 3.4 Pre-Deployment Audit Script (`scripts/audit_demo_accounts.py`)
- Scans database for known demo accounts.
- Outputs status (ACTIVE/INACTIVE) and provides non-destructive remediation guidelines (deactivation/password reset instead of hard deletion).

---

## 4. Verification & Regression Matrix

### 4.1 Production Security Tests (`tests/test_security_gate_prod.py`)
- **Total:** **7 / 7 PASSED (100%)**
  - `SEC-PROD-01` (Production disables demo seed by default): **PASS**
  - `SEC-PROD-02` (Development enables demo seed): **PASS**
  - `SEC-PROD-03` (Production missing JWT secret rejected): **PASS**
  - `SEC-PROD-04` (Production placeholder JWT secret rejected): **PASS**
  - `SEC-PROD-05` (Production valid 256-bit JWT secret accepted): **PASS**
  - `SEC-PROD-06` (Production wildcard CORS rejected): **PASS**
  - `SEC-PROD-07` (Initial admin provisioning & idempotency): **PASS**

### 4.2 Clean Production Boot Simulation
- Executed with `APP_ENV=production`, secure 256-bit `JWT_SECRET`, and `INITIAL_ADMIN_*` credentials in an isolated temp directory:
  - Demo accounts created: **0**
  - Initial admin created: **1** (`it_admin`)
  - Chroma KB collection count: **36** (test seed)
  - RAG query execution: **PASS**

### 4.3 Full Canonical Test Regression Gate
- **Production E2E Suites:** **18 / 18 PASSED (100%)**
- **Service Request E2E Suites:** **25 / 25 PASSED (100%)**
- **Frozen Eval Contract:** **93 / 93 PASSED (100%)**
- **Auth API Suite:** **8 / 8 PASSED (100%)**
- **Python Compilation (`compileall`):** **PASS**
- **Frontend ESLint:** **0 errors** (120 warnings)
- **Frontend Product Guards:** **PASS** (12 guarded routes, 2 fulfillment routes)
- **Frontend TypeScript (`tsc --noEmit`):** **PASS**
- **Frontend Webpack Production Build (`next build`):** **PASS** (46 pages generated)

---

## 5. Non-Destructive Existing Data Strategy

If an existing database being promoted to production already contains demo records:
1. Run `python scripts/audit_demo_accounts.py` to identify demo accounts.
2. Do **not** execute `DELETE FROM users` (preserves historical audit logs and ticket foreign keys).
3. Set `is_active = False` on demo accounts or reset their passwords to high-entropy strings.
4. Set `APP_ENV=production` on the server to prevent re-seeding.

---

## 6. Verdict

```
SEC_GATE_1:              PASS
PRODUCTION_DEPLOY_READY: YES
```
