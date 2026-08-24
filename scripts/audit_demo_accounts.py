"""Pre-deployment script to audit database for known demo accounts."""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# Add repo root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from src.database import AsyncSessionLocal, init_db
from src.models.user import User

DEMO_USERNAMES = {
    "employee1",
    "employee_vip",
    "tech1",
    "manager1",
    "admin",
    "employee_healthcare",
    "employee_auto",
}

DEMO_EMAIL_DOMAINS = {
    "corp.example.com",
    "hospital.example.com",
    "xe.example.com",
}


async def audit_database() -> int:
    await init_db()
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()

        demo_users_found: list[User] = []
        for user in users:
            is_demo = (
                user.username in DEMO_USERNAMES
                or any(user.email.endswith(f"@{domain}") for domain in DEMO_EMAIL_DOMAINS)
            )
            if is_demo:
                demo_users_found.append(user)

        print("=" * 60)
        print("P-236 DATABASE DEMO ACCOUNT AUDIT")
        print("=" * 60)
        print(f"Total users in database: {len(users)}")
        print(f"Demo accounts detected: {len(demo_users_found)}")
        print("-" * 60)

        if demo_users_found:
            for u in demo_users_found:
                status = "ACTIVE" if u.is_active else "INACTIVE"
                print(f" - [{status}] User: '{u.username}' | Role: {u.role.value} | Email: {u.email}")
            print("-" * 60)
            print("RECOMMENDATION FOR PRODUCTION:")
            print("1. Do NOT destructively delete user records (preserves audit integrity).")
            print("2. Set is_active=False or update passwords to high-entropy values before production.")
            print("3. Ensure APP_ENV=production is set so demo seeds are permanently disabled.")
            return 1
        else:
            print("PASS: No default demo accounts detected in database.")
            return 0


if __name__ == "__main__":
    exit_code = asyncio.run(audit_database())
    sys.exit(exit_code)
