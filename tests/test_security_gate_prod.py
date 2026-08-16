"""Tests for SEC-GATE-1: Production Security Gate, Demo Account Hardening & Secret Validation."""
from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from src.config import Settings
from src.database import AsyncSessionLocal, Base, create_async_engine, init_db
from src.main import _provision_initial_admin, _seed_demo_users
from src.models.user import User, UserRole


def test_sec_prod_01_production_disables_demo_seed_by_default():
    """SEC-PROD-01: In production mode, demo seeding is disabled by default."""
    settings = Settings(
        app_env="production",
        jwt_secret="a" * 32,
        cors_origins="https://example.com",
    )
    assert settings.app_env == "production"
    assert settings.is_demo_seed_enabled is False


def test_sec_prod_02_development_and_explicit_override_enable_demo_seed():
    """SEC-PROD-02: In development/test mode or with explicit override, demo seeding is enabled."""
    dev_settings = Settings(app_env="development")
    assert dev_settings.is_demo_seed_enabled is True

    test_settings = Settings(app_env="test")
    assert test_settings.is_demo_seed_enabled is True

    override_settings = Settings(
        app_env="production",
        enable_demo_seed=True,
        jwt_secret="a" * 32,
        cors_origins="https://example.com",
    )
    assert override_settings.is_demo_seed_enabled is True


def test_sec_prod_03_production_missing_jwt_secret_rejected():
    """SEC-PROD-03: Production fails validation when JWT_SECRET is empty."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            app_env="production",
            jwt_secret="",
            cors_origins="https://example.com",
        )
    assert "JWT_SECRET" in str(exc_info.value)


def test_sec_prod_04_production_placeholder_jwt_secret_rejected():
    """SEC-PROD-04: Production rejects known placeholder or short JWT secrets."""
    insecure_keys = [
        "change-me-in-production",
        "helpdesk-super-secret-jwt-key-change-in-production-2024",
        "secret",
        "changeme",
        "admin",
        "short-secret-key-1234",
    ]
    for key in insecure_keys:
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                app_env="production",
                jwt_secret=key,
                cors_origins="https://example.com",
            )
        assert "JWT_SECRET" in str(exc_info.value)


def test_sec_prod_05_production_valid_jwt_secret_accepted():
    """SEC-PROD-05: Production accepts 256-bit / >=32 character secure random secret."""
    secure_key = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    settings = Settings(
        app_env="production",
        jwt_secret=secure_key,
        cors_origins="https://helpdesk.corp.example.com",
    )
    assert settings.jwt_secret == secure_key


def test_sec_prod_06_production_wildcard_cors_rejected():
    """SEC-PROD-06: Production rejects wildcard '*' CORS origins."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            app_env="production",
            jwt_secret="a" * 32,
            cors_origins="*",
        )
    assert "CORS_ORIGINS" in str(exc_info.value)


@pytest.mark.asyncio
async def test_sec_prod_07_initial_admin_provisioning():
    """SEC-PROD-07: In production, initial admin is provisioned via environment credentials."""
    temp_dir = Path(tempfile.mkdtemp(prefix="p236_sec_admin_"))
    try:
        temp_db = temp_dir / "test_admin.db"
        test_db_url = f"sqlite+aiosqlite:///{temp_db.as_posix()}"
        engine = create_async_engine(test_db_url)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        from sqlalchemy.ext.asyncio import async_sessionmaker
        SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

        async with SessionLocal() as db:
            await _provision_initial_admin(
                db,
                email="admin.prod@company.example.com",
                username="superadmin",
                password="HighlySecureProdPassword2026!",
                full_name="Chief Administrator",
            )

        async with SessionLocal() as db:
            result = await db.execute(select(User).where(User.username == "superadmin"))
            admin_user = result.scalar_one_or_none()
            assert admin_user is not None
            assert admin_user.email == "admin.prod@company.example.com"
            assert admin_user.role == UserRole.ADMIN
            assert admin_user.full_name == "Chief Administrator"

            from src.services.auth_service import verify_password
            assert verify_password("HighlySecureProdPassword2026!", admin_user.hashed_password)

            # Check idempotency: second call should not recreate or duplicate
            await _provision_initial_admin(
                db,
                email="admin.prod@company.example.com",
                username="superadmin",
                password="DifferentPassword!",
            )
            # Password remains the original
            assert verify_password("HighlySecureProdPassword2026!", admin_user.hashed_password)

        await engine.dispose()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
