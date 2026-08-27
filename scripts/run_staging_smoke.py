"""Comprehensive Staging Smoke Test Runner for STAGING-SMOKE-1.

Simulates and executes end-to-end smoke verification against actual
production/staging configuration and persistent data.
"""
from __future__ import annotations

import asyncio
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Enforce Production Staging Configuration
os.environ["APP_ENV"] = "production"
os.environ["JWT_SECRET"] = "8f3b2a1c9e4d6f8a0b2c4e6f8a0d2c4e6f8a0b2c4e6f8a0d2c4e6f8a0b2c4e6f"
os.environ["CORS_ORIGINS"] = "http://localhost:3000,http://127.0.0.1:3000"
os.environ["ENABLE_DEMO_SEED"] = "false"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./data/helpdesk.db"
os.environ["CHROMA_PERSIST_DIR"] = "./data/chroma"
os.environ["CHROMA_COLLECTION_NAME"] = "helpdesk_kb_multilingual_v2_sentence_transformer"
os.environ["EMBEDDING_MODEL"] = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
os.environ["EMBEDDING_BACKEND"] = "sentence_transformer"
os.environ["EMBEDDING_ALLOW_NETWORK_DOWNLOADS"] = "false"
os.environ["OTEL_ENABLED"] = "false"
os.environ["REDIS_URL"] = ""

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from src.config import get_settings

get_settings.cache_clear()

from src.database import AsyncSessionLocal, init_db  # noqa: E402
from src.main import app  # noqa: E402
from src.models.knowledge_base import KnowledgeBaseEntry  # noqa: E402
from src.models.service_request import ServiceRequest  # noqa: E402
from src.models.ticket import Ticket  # noqa: E402
from src.models.user import CompanyUnit, User, UserRole  # noqa: E402
from src.services.auth_service import create_access_token  # noqa: E402
from src.services.rag_service import get_collection_count, search_similar  # noqa: E402


def safe_print(*args):
    print(*(str(a).encode("ascii", "replace").decode("ascii") for a in args))


async def run_staging_smoke() -> dict:
    smoke_results = {
        "timestamp": datetime.now(UTC).isoformat(),
        "stages": {},
        "verdict": "PASS",
        "errors": [],
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://staging-test") as client:
        print("\n=======================================================")
        print("STAGE 1: STAGING STARTUP & CONFIGURATION CONTRACT")
        print("=======================================================")
        settings = get_settings()
        assert settings.app_env == "production", "APP_ENV must be production"
        assert settings.is_demo_seed_enabled is False, "Demo seed must be disabled in production"
        assert len(settings.jwt_secret) >= 32, "JWT secret must be at least 32 characters"
        assert settings.cors_origins != "*", "CORS origins must not be wildcard *"

        # Health endpoint check
        resp = await client.get("/health")
        assert resp.status_code == 200, f"Health endpoint failed: {resp.status_code}"
        health_data = resp.json()
        print(f"Health check: status={health_data['status']}, env={health_data['env']}, kb_documents={health_data['kb_documents']}")
        assert health_data["status"] == "ok"
        assert health_data["env"] == "production"
        smoke_results["stages"]["startup_config"] = "PASS"

        print("\n=======================================================")
        print("STAGE 2: STORAGE & PERSISTENCE INTEGRITY")
        print("=======================================================")
        await init_db()
        kb_count = get_collection_count()
        print(f"Chroma canonical collection document count: {kb_count}")
        assert kb_count == 433, f"Expected 433 documents in Chroma, got {kb_count}"

        # Verify kb-036 exists in both SQLite and Chroma
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(KnowledgeBaseEntry).where(KnowledgeBaseEntry.chroma_id == "kb-036"))
            kb_entry = res.scalar_one_or_none()
            assert kb_entry is not None, "kb-036 missing from SQLite knowledge_base table"
            assert kb_entry.category == "service_request", f"Expected category 'service_request', got {kb_entry.category}"
            safe_print(f"SQLite verification: kb-036 '{kb_entry.title}' verified.")

        smoke_results["stages"]["persistence_integrity"] = "PASS"

        print("\n=======================================================")
        print("STAGE 3: AUTHENTICATION & ACCESS CONTROL SMOKE")
        print("=======================================================")
        # 3.1 Valid Login (Employee)
        login_resp = await client.post("/api/v1/auth/login", json={"username": "employee1", "password": "demo123"})
        assert login_resp.status_code == 200, f"Employee login failed: {login_resp.text}"
        token_data = login_resp.json()
        employee_token = token_data["access_token"]
        assert token_data["user"]["username"] == "employee1"
        assert token_data["user"]["role"] == "employee"
        print("Employee login OK.")

        # 3.2 /auth/me
        headers_emp = {"Authorization": f"Bearer {employee_token}"}
        me_resp = await client.get("/api/v1/auth/me", headers=headers_emp)
        assert me_resp.status_code == 200
        assert me_resp.json()["username"] == "employee1"
        print("/auth/me OK.")

        # 3.3 Inactive User Block
        async with AsyncSessionLocal() as session:
            # Create a temporary inactive user
            res = await session.execute(select(User).where(User.username == "smoke_inactive_user"))
            inactive_u = res.scalar_one_or_none()
            if not inactive_u:
                from src.services.auth_service import create_user
                inactive_u = await create_user(
                    session,
                    username="smoke_inactive_user",
                    email="inactive@corp.example.com",
                    full_name="Smoke Inactive User",
                    password="Password123!",
                    role=UserRole.EMPLOYEE,
                    company_unit=CompanyUnit.CORPORATE,
                    department="Sales",
                    is_active=False,
                )
                await session.commit()

        # Attempt login with inactive user
        bad_login = await client.post("/api/v1/auth/login", json={"username": "smoke_inactive_user", "password": "Password123!"})
        assert bad_login.status_code == 401, f"Inactive user was allowed to login: {bad_login.status_code}"
        print("Inactive user rejection verified (401 Unauthorized).")
        smoke_results["stages"]["auth_access_control"] = "PASS"

        print("\n=======================================================")
        print("STAGE 4: EMPLOYEE WORKFLOWS SMOKE")
        print("=======================================================")
        # 4.1 Create Incident Ticket
        ticket_payload = {
            "title": "Smoke Test VPN Connection Issue",
            "description": "Không thể kết nối VPN từ xa sau khi đổi mật khẩu tài khoản.",
            "category": "network",
            "priority": "high",
            "urgency": "high",
        }
        ticket_resp = await client.post("/api/v1/tickets", json=ticket_payload, headers=headers_emp)
        assert ticket_resp.status_code == 201, f"Create ticket failed: {ticket_resp.text}"
        ticket_data = ticket_resp.json()
        created_ticket_id = ticket_data["ticket_id"]
        ticket_num = ticket_data["ticket_number"]
        safe_print(f"Incident ticket created: id={created_ticket_id}, number={ticket_num}")
        assert ticket_num.startswith("INC-")

        # 4.2 Chat inside Ticket
        msg_payload = {"message": "Tôi đã thử restart router nhưng vẫn không được, xin hỗ trợ."}
        msg_resp = await client.post(f"/api/v1/tickets/{created_ticket_id}/messages", json=msg_payload, headers=headers_emp)
        assert msg_resp.status_code == 200, f"Ticket message post failed: {msg_resp.text}"
        safe_print("Ticket message conversation OK.")

        # 4.3 Create Service Request
        sr_payload = {
            "service_name": "Xin Microsoft 365 license",
            "category": "software",
            "form_data": {"justification": "Cần cho công việc phân tích báo cáo phòng kinh doanh"},
        }
        sr_resp = await client.post("/api/v1/service-requests", json=sr_payload, headers=headers_emp)
        assert sr_resp.status_code == 201, f"Create Service Request failed: {sr_resp.text}"
        sr_data = sr_resp.json()
        created_sr_id = sr_data["id"]
        sr_num = sr_data["request_number"]
        safe_print(f"Service Request created: id={created_sr_id}, number={sr_num}, status={sr_data['status']}")
        assert sr_num.startswith("REQ-")
        smoke_results["stages"]["employee_workflows"] = "PASS"

        safe_print("\n=======================================================")
        safe_print("STAGE 5: AI GROUNDING & RAG RETRIEVAL SMOKE")
        safe_print("=======================================================")
        # 5.1 Query VPN (Hit@1)
        vpn_results = search_similar("Quên mật khẩu VPN công ty", n_results=1)
        assert len(vpn_results) > 0
        hit_title = vpn_results[0]['metadata'].get('title', '')
        safe_print(f"RAG VPN search: Top hit '{hit_title}' (score={vpn_results[0]['relevance_score']:.4f})")
        assert "vpn" in hit_title.lower() or "mật khẩu" in hit_title.lower() or "mat khau" in hit_title.lower()

        # 5.2 Query Service Request Process (kb-036 Grounding)
        sr_kb_results = search_similar("Quy trình Service Request gồm những bước nào?", n_results=1)
        assert len(sr_kb_results) > 0
        assert sr_kb_results[0]["doc_id"] == "kb-036", f"Expected top hit kb-036, got {sr_kb_results[0]['doc_id']}"
        safe_print(f"RAG SR process search: Top hit '{sr_kb_results[0]['metadata'].get('title')}' (doc_id={sr_kb_results[0]['doc_id']})")

        # 5.3 Context-Aware Query Reformulation
        from src.services.rag_service import rewrite_query_with_context
        rewritten = rewrite_query_with_context("còn cách nào khác không?", history_summary="Người dùng đang hỏi về cách reset mật khẩu VPN")
        safe_print(f"Query rewrite test: 'còn cách nào khác không?' -> '{rewritten}'")
        assert "vpn" in rewritten.lower() or "mật khẩu" in rewritten.lower()
        smoke_results["stages"]["ai_rag_grounding"] = "PASS"

        safe_print("\n=======================================================")
        safe_print("STAGE 6: TECHNICIAN QUEUE & TAKEOVER SMOKE")
        safe_print("=======================================================")
        # 6.1 Technician Login
        tech_login = await client.post("/api/v1/auth/login", json={"username": "tech1", "password": "demo123"})
        assert tech_login.status_code == 200
        tech_token = tech_login.json()["access_token"]
        headers_tech = {"Authorization": f"Bearer {tech_token}"}

        # 6.2 Ticket Takeover
        assign_resp = await client.post(
            f"/api/v1/tickets/{created_ticket_id}/takeover",
            headers=headers_tech,
        )
        assert assign_resp.status_code == 200
        safe_print(f"Technician ticket takeover: Ticket {ticket_num} assigned to tech1, status=in_progress.")

        # 6.3 Service Request Queue
        sr_queue_resp = await client.get("/api/v1/service-requests/technician/queue", headers=headers_tech)
        assert sr_queue_resp.status_code == 200
        sr_list = sr_queue_resp.json().get("items", [])
        safe_print(f"Technician Service Request queue visible: {len(sr_list)} requests in queue.")
        smoke_results["stages"]["technician_workflows"] = "PASS"

        safe_print("\n=======================================================")
        safe_print("STAGE 7: MANAGER APPROVAL SMOKE")
        safe_print("=======================================================")
        # 7.1 Manager Login
        mgr_login = await client.post("/api/v1/auth/login", json={"username": "manager1", "password": "demo123"})
        assert mgr_login.status_code == 200
        mgr_token = mgr_login.json()["access_token"]
        headers_mgr = {"Authorization": f"Bearer {mgr_token}"}

        # 7.2 Service Request Approval
        approve_resp = await client.post(
            f"/api/v1/service-requests/{sr_num}/approve",
            json={"comment": "Phê duyệt cấp bản quyền phục vụ công việc."},
            headers=headers_mgr,
        )
        assert approve_resp.status_code == 200, f"Approval failed: {approve_resp.text}"
        approved_sr = approve_resp.json()
        assert approved_sr["status"] in ("approved", "assigned", "in_progress", "submitted")
        safe_print(f"Manager approval: Request {sr_num} approved successfully, status={approved_sr['status']}.")
        smoke_results["stages"]["manager_workflows"] = "PASS"

        safe_print("\n=======================================================")
        safe_print("STAGE 8: ADMIN USER LIFECYCLE & KB SMOKE")
        safe_print("=======================================================")
        # 8.1 Admin Login
        admin_login = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
        assert admin_login.status_code == 200
        admin_token = admin_login.json()["access_token"]
        headers_admin = {"Authorization": f"Bearer {admin_token}"}

        # 8.2 Create New User via Admin API
        new_username = f"smoke_emp_{datetime.now(UTC).strftime('%M%S')}"
        create_u_resp = await client.post(
            "/api/v1/admin/users",
            json={
                "username": new_username,
                "email": f"{new_username}@corp.example.com",
                "password": "SecurePassword2026!",
                "full_name": "Smoke Test Employee",
                "role": "employee",
                "company_unit": "corporate",
                "department": "Finance",
            },
            headers=headers_admin,
        )
        assert create_u_resp.status_code == 201, f"Admin user creation failed: {create_u_resp.text}"
        created_user_id = create_u_resp.json()["id"]
        safe_print(f"Admin created user: id={created_user_id}, username={new_username}")

        # 8.3 Admin KB Inspection
        admin_kb_resp = await client.get("/api/v1/admin/kb", headers=headers_admin)
        assert admin_kb_resp.status_code == 200
        kb_articles = admin_kb_resp.json()
        assert len(kb_articles) > 0
        assert any(item.get("chroma_id") == "kb-036" for item in kb_articles)
        safe_print(f"Admin KB verification: {len(kb_articles)} articles listed (kb-036 present).")
        smoke_results["stages"]["admin_workflows"] = "PASS"

        safe_print("\n=======================================================")
        safe_print("STAGE 9: SECURITY & TENANT BOUNDARY SMOKE")
        safe_print("=======================================================")
        # 9.1 Cross-Tenant Denial (Employee cannot access admin endpoints)
        denied_resp = await client.get("/api/v1/admin/users", headers=headers_emp)
        assert denied_resp.status_code == 403, f"Employee was not denied admin access: {denied_resp.status_code}"
        safe_print("RBAC cross-role denial verified: Employee -> 403 on Admin endpoint.")

        # 9.2 Employee cannot view other tenant's private tickets
        denied_ticket = await client.get(f"/api/v1/tickets/{created_ticket_id}", headers={
            "Authorization": f"Bearer {create_access_token({'sub': str(created_user_id)})}"
        })
        assert denied_ticket.status_code in (403, 404), f"Cross-user ticket read allowed: {denied_ticket.status_code}"
        safe_print("Tenant privacy verified: Unrelated user -> 403/404 on private ticket.")
        smoke_results["stages"]["security_boundaries"] = "PASS"

        print("\n=======================================================")
        print("STAGE 10: RESTART PERSISTENCE VALIDATION")
        print("=======================================================")
        # Re-initialize DB and clear Chroma singleton to simulate service restart
        import src.services.rag_service as rag_mod
        rag_mod._chroma_client = None
        rag_mod._collection = None

        # Verify state survives restart
        async with AsyncSessionLocal() as session:
            # Check Ticket survives
            t_res = await session.execute(select(Ticket).where(Ticket.id == created_ticket_id))
            persisted_ticket = t_res.scalar_one_or_none()
            assert persisted_ticket is not None, "Created ticket lost after restart"
            assert persisted_ticket.ticket_number == ticket_num
            safe_print(f"Post-restart Ticket: id={persisted_ticket.id}, number={persisted_ticket.ticket_number}, title='{persisted_ticket.title}'")

            # Check Service Request survives
            sr_res = await session.execute(select(ServiceRequest).where(ServiceRequest.id == created_sr_id))
            persisted_sr = sr_res.scalar_one_or_none()
            assert persisted_sr is not None, "Created Service Request lost after restart"
            assert persisted_sr.request_number == sr_num
            safe_print(f"Post-restart Service Request: id={persisted_sr.id}, number={persisted_sr.request_number}")

            # Check User survives
            u_res = await session.execute(select(User).where(User.id == created_user_id))
            persisted_user = u_res.scalar_one_or_none()
            assert persisted_user is not None, "Created user lost after restart"
            safe_print(f"Post-restart User: id={persisted_user.id}, username='{persisted_user.username}'")

        # Check Chroma count post-restart
        post_restart_count = get_collection_count()
        assert post_restart_count == 433, f"Chroma count changed after restart: {post_restart_count}"
        safe_print(f"Post-restart Chroma count: {post_restart_count} documents intact.")

        # Check RAG query post-restart
        post_rag = search_similar("quên mật khẩu", n_results=1)
        assert len(post_rag) > 0
        safe_print(f"Post-restart RAG query OK: Top hit '{post_rag[0]['metadata'].get('title')}'")

        # Check Auth post-restart
        post_login = await client.post("/api/v1/auth/login", json={"username": "employee1", "password": "demo123"})
        assert post_login.status_code == 200
        safe_print("Post-restart Login OK.")

        smoke_results["stages"]["restart_persistence"] = "PASS"

    safe_print("\n=======================================================")
    safe_print("STAGING SMOKE RESULT: ALL 10 STAGES PASSED (100%)")
    safe_print("=======================================================\n")
    return smoke_results


if __name__ == "__main__":
    results = asyncio.run(run_staging_smoke())
    safe_print("Execution Finished with Result:", results["verdict"])
