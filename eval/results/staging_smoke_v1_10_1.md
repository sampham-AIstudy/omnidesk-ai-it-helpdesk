# STAGING-SMOKE-1 — Staging Environment Smoke & Persistence Report

**Date:** 2026-08-16  
**Milestone:** STAGING-SMOKE-1  
**Status:** PASS  
**Verdict:** `STAGING_SMOKE: PASS` | `PRODUCTION_RELEASE_CANDIDATE: YES`  

---

## 1. Executive Summary

The P-236 Help Desk system has successfully completed comprehensive staging smoke testing using the exact production topology, strict security invariants, real persistent storage (SQLite & ChromaDB with SentenceTransformer embeddings), and multi-role end-to-end workflows.

All 10 verification stages passed with zero regressions.

```
STAGING_SMOKE:                PASS
PRODUCTION_RELEASE_CANDIDATE: YES
```

---

## 2. Staging Startup & Configuration Contract (Stage 1)

- **Runtime Profile:** `APP_ENV=production`
- **Security Secret:** 256-bit high-entropy `JWT_SECRET` (validated ≥32 chars)
- **CORS Whitelist:** Explicit `http://localhost:3000,http://127.0.0.1:3000` (wildcard `*` blocked)
- **Demo Seeding:** Disabled (`is_demo_seed_enabled=False`)
- **Health Check (`GET /health`):** Returns `status="ok"`, `env="production"`, `kb_documents=433`

---

## 3. Storage & Persistence Integrity (Stage 2)

- **SQLite Database:** Connected to `data/helpdesk.db` with WAL mode and schema integrity.
- **ChromaDB Vector Store:** Connected to `data/chroma`, active collection `helpdesk_kb_multilingual_v2_sentence_transformer`.
- **Knowledge Base Document Count:** Exactly **433 documents** indexed.
- **Canonical Service Request Knowledge ([`kb-036`](file:///C:/Users/Admin/Python%20Advanced/VinAI%20Lab/P-236/src/data/service_request_kb.py)): Verified present in both SQLite and ChromaDB.

---

## 4. Authentication & Access Control (Stage 3)

- **Valid Authentication:** Employee login (`employee1`) succeeds with JWT generation and claims.
- **Identity Endpoint:** `GET /api/v1/auth/me` returns identity profile and company unit (`real_estate`).
- **Inactive Account Enforcement:** Inactive user (`is_active=False`) login attempts immediately rejected with `401 Unauthorized`.

---

## 5. Employee Workflows (Stage 4)

- **Incident Creation:** Successfully created ticket (`INC-20260816-5358`, priority: `high`, category: `network`).
- **Ticket Conversation:** User posted follow-up troubleshooting message; thread persisted.
- **Service Request Creation:** Created request (`REQ-20260816-7A0536B0`, service: `Xin Microsoft 365 license`, status: `pending_approval`).

---

## 6. AI Grounding & RAG Retrieval (Stage 5)

- **Domain Retrieval (VPN):** `search_similar("Quên mật khẩu VPN công ty")` retrieved top hit at Rank 1 (Score: `0.7955`).
- **Process Grounding (kb-036):** `search_similar("Quy trình Service Request gồm những bước nào?")` retrieved `kb-036` at Rank 1.
- **Context-Aware Query Rewriting:** Ambiguous follow-up `"còn cách nào khác không?"` successfully augmented with conversational context `"Người dùng đang hỏi về cách reset mật khẩu VPN"`.

---

## 7. Technician Queue & Takeover (Stage 6)

- **Technician Authentication:** `tech1` authenticated successfully.
- **Ticket Takeover:** `POST /api/v1/tickets/{id}/takeover` assigned ticket to `tech1` and updated status to `in_progress`.
- **Service Request Queue:** `GET /api/v1/service-requests/technician/queue` returned tenant-scoped fulfillment queue.

---

## 8. Manager Approval Workflow (Stage 7)

- **Manager Authentication:** `manager1` authenticated successfully.
- **Approval Decision:** `POST /api/v1/service-requests/{request_number}/approve` approved request with comment `"Phê duyệt cấp bản quyền phục vụ công việc."` Status transitioned to `submitted` for technician fulfillment.

---

## 9. Admin User Lifecycle & KB Management (Stage 8)

- **Admin Authentication:** `admin` authenticated successfully.
- **User Provisioning:** `POST /api/v1/admin/users` created new employee user (`smoke_emp_2042`).
- **Admin KB Inspection:** `GET /api/v1/admin/kb` confirmed access to 228 articles including `kb-036`.

---

## 10. Security & Tenant Boundaries (Stage 9)

- **Cross-Role RBAC:** Employee attempting to access `GET /api/v1/admin/users` returned `403 Forbidden`.
- **Tenant Isolation:** Unrelated user attempting to read another user's private ticket returned `403 Forbidden`.

---

## 11. Restart Persistence Validation (Stage 10)

Services were reloaded and singletons cleared to simulate a server restart:
- **Created Incident Ticket:** Persisted intact (`id=88`, number=`INC-20260816-5358`, title=`"Smoke Test VPN Connection Issue"`).
- **Created Service Request:** Persisted intact (`id=4`, number=`REQ-20260816-7A0536B0`).
- **Created Admin User:** Persisted intact (`id=9`, username=`smoke_emp_2042`).
- **Chroma Collection Count:** Exactly **433 documents** intact.
- **RAG Semantic Query:** Functional post-restart (`"Quên mật khẩu Windows / tài khoản domain"`).
- **Authentication:** Token verification and login functional post-restart.

---

## 12. Verdict

```
STAGING_SMOKE:                PASS
PRODUCTION_RELEASE_CANDIDATE: YES
```
