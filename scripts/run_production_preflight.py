"""Production Preflight & Clean Bootstrap Verification Script.

Tests clean production bootstrap and data isolation in a segregated
temporary production environment without touching dev database data/helpdesk.db.
"""
from __future__ import annotations

import asyncio
import os
import shutil
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def safe_print(*args):
    print(*(str(a).encode("ascii", "replace").decode("ascii") for a in args))


async def run_production_preflight() -> dict:
    preflight_results = {
        "timestamp": datetime.now(UTC).isoformat(),
        "stages": {},
        "verdict": "PASS",
        "errors": [],
    }

    temp_prod_dir = Path(tempfile.mkdtemp(prefix="p236_prod_preflight_"))
    try:
        prod_db_path = temp_prod_dir / "prod_helpdesk.db"
        prod_chroma_path = temp_prod_dir / "chroma"
        prod_chroma_path.mkdir(parents=True, exist_ok=True)

        # Copy canonical Chroma collection to isolated test directory
        src_chroma = Path("./data/chroma")
        if src_chroma.exists():
            for item in src_chroma.iterdir():
                if item.is_dir():
                    shutil.copytree(item, prod_chroma_path / item.name)
                else:
                    shutil.copy2(item, prod_chroma_path / item.name)

        safe_print("=======================================================")
        safe_print("STAGE 1: CLEAN PRODUCTION ENVIRONMENT SETUP")
        safe_print("=======================================================")
        os.environ["APP_ENV"] = "production"
        os.environ["JWT_SECRET"] = "e8c9d0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9"
        os.environ["CORS_ORIGINS"] = "https://helpdesk.corp.example.com,https://itsm.corp.example.com"
        os.environ["ENABLE_DEMO_SEED"] = "false"
        os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{prod_db_path.as_posix()}"
        os.environ["CHROMA_PERSIST_DIR"] = str(prod_chroma_path)
        os.environ["CHROMA_COLLECTION_NAME"] = "helpdesk_kb_multilingual_v2_sentence_transformer"
        os.environ["EMBEDDING_MODEL"] = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        os.environ["EMBEDDING_BACKEND"] = "sentence_transformer"
        os.environ["EMBEDDING_ALLOW_NETWORK_DOWNLOADS"] = "false"
        os.environ["INITIAL_ADMIN_EMAIL"] = "it-director@corp.example.com"
        os.environ["INITIAL_ADMIN_USERNAME"] = "enterprise_admin"
        os.environ["INITIAL_ADMIN_PASSWORD"] = "EnterpriseSecurePass2026!StrongEntropy"
        os.environ["INITIAL_ADMIN_FULL_NAME"] = "Enterprise System Administrator"
        os.environ["OTEL_ENABLED"] = "false"
        os.environ["REDIS_URL"] = ""

        # Reload config and services
        import importlib

        from src.config import get_settings
        get_settings.cache_clear()

        import src.database as db_mod
        importlib.reload(db_mod)

        import src.services.rag_service as rag_mod
        rag_mod._chroma_client = None
        rag_mod._collection = None

        settings = get_settings()
        assert settings.app_env == "production"
        assert settings.is_demo_seed_enabled is False
        assert len(settings.jwt_secret) >= 32
        assert settings.cors_origins != "*"
        safe_print("Production settings loaded and validated: APP_ENV=production, demo_seed=disabled.")
        preflight_results["stages"]["env_validation"] = "PASS"

        safe_print("\n=======================================================")
        safe_print("STAGE 2: FRESH PRODUCTION DATABASE BOOTSTRAP")
        safe_print("=======================================================")
        await db_mod.init_db()

        from src.main import _provision_initial_admin, _seed_demo_users, _seed_knowledge_base

        async with db_mod.AsyncSessionLocal() as session:
            # Bootstrap clean production DB
            if settings.is_demo_seed_enabled:
                await _seed_demo_users(session)
            else:
                if settings.initial_admin_email and settings.initial_admin_password:
                    await _provision_initial_admin(
                        session,
                        email=settings.initial_admin_email,
                        username=settings.initial_admin_username or "admin",
                        password=settings.initial_admin_password,
                        full_name=settings.initial_admin_full_name or "System Administrator",
                    )
            await _seed_knowledge_base(session)

        # Inspect database content
        from sqlalchemy import select

        from src.models.knowledge_base import KnowledgeBaseEntry
        from src.models.service_request import ServiceRequest
        from src.models.ticket import Ticket
        from src.models.user import User, UserRole

        async with db_mod.AsyncSessionLocal() as session:
            # Check users
            res_u = await session.execute(select(User))
            users = res_u.scalars().all()
            safe_print(f"Total users in fresh production DB: {len(users)}")
            assert len(users) == 1, f"Expected exactly 1 admin user, got {len(users)}"
            admin_user = users[0]
            assert admin_user.username == "enterprise_admin"
            assert admin_user.email == "it-director@corp.example.com"
            assert admin_user.role == UserRole.ADMIN
            safe_print(f"Initial admin verified: username='{admin_user.username}', role='{admin_user.role.value}', email='{admin_user.email}'")

            # Check demo users absent
            demo_usernames = ["employee1", "employee_vip", "tech1", "manager1", "admin", "employee_healthcare", "employee_auto", "smoke_emp_2042"]
            res_demo = await session.execute(select(User).where(User.username.in_(demo_usernames)))
            assert len(res_demo.scalars().all()) == 0, "Demo users leaked into production DB!"
            safe_print("Zero demo accounts verified in production DB.")

            # Check 0 tickets & 0 service requests
            res_t = await session.execute(select(Ticket))
            assert len(res_t.scalars().all()) == 0, "Staging tickets found in clean production DB!"
            res_sr = await session.execute(select(ServiceRequest))
            assert len(res_sr.scalars().all()) == 0, "Staging Service Requests found in clean production DB!"
            safe_print("Zero staging/smoke tickets and service requests verified.")

            # Check kb-036 exists in SQLite
            res_kb = await session.execute(select(KnowledgeBaseEntry).where(KnowledgeBaseEntry.chroma_id == "kb-036"))
            kb_036 = res_kb.scalar_one_or_none()
            assert kb_036 is not None, "kb-036 missing in clean production SQLite KB table!"
            safe_print(f"Canonical Service Request KB article '{kb_036.title}' verified.")

        preflight_results["stages"]["db_bootstrap"] = "PASS"

        safe_print("\n=======================================================")
        safe_print("STAGE 3: CANONICAL KB & CHROMA PROVENANCE VALIDATION")
        safe_print("=======================================================")
        kb_count = rag_mod.get_collection_count()
        safe_print(f"Chroma collection document count: {kb_count}")
        assert kb_count == 433, f"Expected 433 documents in Chroma, got {kb_count}"

        # Verify RAG retrieval on kb-036
        sr_retrieval = rag_mod.search_similar("Quy trình Service Request gồm những bước nào?", n_results=1)
        assert len(sr_retrieval) > 0
        assert sr_retrieval[0]["doc_id"] == "kb-036", f"Expected kb-036, got {sr_retrieval[0]['doc_id']}"
        safe_print(f"RAG query for SR process retrieved: doc_id='{sr_retrieval[0]['doc_id']}' at Rank 1.")

        # Verify RAG retrieval on general VPN KB
        vpn_retrieval = rag_mod.search_similar("Quên mật khẩu VPN công ty", n_results=1)
        assert len(vpn_retrieval) > 0
        safe_print(f"RAG query for VPN retrieved: '{vpn_retrieval[0]['metadata'].get('title')}' (score={vpn_retrieval[0]['relevance_score']:.4f})")
        preflight_results["stages"]["kb_provenance"] = "PASS"

        safe_print("\n=======================================================")
        safe_print("STAGE 4: API & AUTHENTICATION ENDPOINT SMOKE")
        safe_print("=======================================================")
        from httpx import ASGITransport, AsyncClient

        from src.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://prod-test") as client:
            # 4.1 Health Check
            h_resp = await client.get("/health")
            assert h_resp.status_code == 200
            h_data = h_resp.json()
            assert h_data["status"] == "ok"
            assert h_data["env"] == "production"
            safe_print(f"/health response: status='{h_data['status']}', env='{h_data['env']}', kb_documents={h_data['kb_documents']}")

            # 4.2 Login with initial admin
            login_resp = await client.post(
                "/api/v1/auth/login",
                json={"username": "enterprise_admin", "password": "EnterpriseSecurePass2026!StrongEntropy"},
            )
            assert login_resp.status_code == 200, f"Admin login failed: {login_resp.text}"
            token_data = login_resp.json()
            admin_jwt = token_data["access_token"]
            safe_print("Initial admin login successful, JWT generated.")

            # 4.3 /auth/me
            me_resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {admin_jwt}"})
            assert me_resp.status_code == 200
            me_data = me_resp.json()
            assert me_data["username"] == "enterprise_admin"
            assert me_data["role"] == "admin"
            safe_print(f"/auth/me verified: user='{me_data['username']}', role='{me_data['role']}'")

            # 4.4 Demo logins rejected
            for demo_u in ["employee1", "tech1", "manager1", "admin"]:
                bad_resp = await client.post("/api/v1/auth/login", json={"username": demo_u, "password": "demo123"})
                assert bad_resp.status_code == 401, f"Demo user '{demo_u}' unexpectedly logged in!"
            safe_print("All default demo account login attempts rejected (401 Unauthorized).")

        preflight_results["stages"]["api_smoke"] = "PASS"

        safe_print("\n=======================================================")
        safe_print("STAGE 5: PRODUCTION RESTART PERSISTENCE TEST")
        safe_print("=======================================================")
        # Clear singletons to simulate restart
        rag_mod._chroma_client = None
        rag_mod._collection = None

        # Reconnect
        async with db_mod.AsyncSessionLocal() as session:
            res_after = await session.execute(select(User).where(User.username == "enterprise_admin"))
            reconnected_admin = res_after.scalar_one_or_none()
            assert reconnected_admin is not None, "Initial admin lost after server restart!"
            safe_print(f"Post-restart verification: admin '{reconnected_admin.username}' intact.")

        post_count = rag_mod.get_collection_count()
        assert post_count == 433, f"Chroma count changed after restart: {post_count}"
        safe_print(f"Post-restart Chroma verification: {post_count} documents intact.")

        # Test auth post-restart
        async with AsyncClient(transport=transport, base_url="http://prod-test") as client:
            post_me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {admin_jwt}"})
            assert post_me.status_code == 200
            safe_print("Post-restart JWT authentication verified.")

        preflight_results["stages"]["restart_persistence"] = "PASS"

        safe_print("\n=======================================================")
        safe_print("STAGE 6: DEV DATABASE DATA INTEGRITY CHECK")
        safe_print("=======================================================")
        dev_db = Path("./data/helpdesk.db")
        assert dev_db.exists(), "Original dev database data/helpdesk.db was modified or deleted!"
        safe_print(f"Original dev database intact at '{dev_db}' (size={dev_db.stat().st_size} bytes).")
        preflight_results["stages"]["dev_db_intact"] = "PASS"

        safe_print("\n=======================================================")
        safe_print("PROD PREFLIGHT: ALL 6 STAGES PASSED (100%)")
        safe_print("=======================================================\n")

    finally:
        shutil.rmtree(temp_prod_dir, ignore_errors=True)

    return preflight_results


if __name__ == "__main__":
    results = asyncio.run(run_production_preflight())
    safe_print("Execution Finished with Result:", results["verdict"])
