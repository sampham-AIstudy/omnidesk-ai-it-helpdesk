"""Authenticated, read-only view of currently applicable company policies."""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth import get_current_active_user
from src.database import get_db
from src.models.policy import Policy, PolicyScope, PolicyVersion, PolicyVersionStatus
from src.models.schemas import (
    ApplicablePolicyDetailResponse,
    ApplicablePolicyListResponse,
)
from src.models.user import User
from src.services.policy_resolver import ResolverContext, applicable_policy_versions

router = APIRouter(prefix="/policies", tags=["Policies"])


def _context(user: User) -> ResolverContext:
    return ResolverContext(
        tenant_id=user.company_unit.value,
        company_unit=user.company_unit.value,
        department=user.department,
        role=user.role.value,
        user_id=user.id,
        timestamp=datetime.now(UTC),
    )


async def _applicable_records(db: AsyncSession, user: User) -> list[tuple[Policy, PolicyVersion]]:
    """Load candidates then apply the canonical resolver visibility helper."""
    context = _context(user)
    now = context.timestamp
    policies = list((await db.execute(
        select(Policy).where(
            Policy.status == "active",
            or_(Policy.tenant_id.is_(None), Policy.tenant_id == context.tenant_id),
        )
    )).scalars())
    if not policies:
        return []
    versions = list((await db.execute(
        select(PolicyVersion).where(
            PolicyVersion.policy_id.in_([policy.id for policy in policies]),
            PolicyVersion.status == PolicyVersionStatus.ACTIVE.value,
            PolicyVersion.effective_from <= now,
            or_(PolicyVersion.effective_until.is_(None), PolicyVersion.effective_until > now),
        )
    )).scalars())
    if not versions:
        return []
    scopes = list((await db.execute(
        select(PolicyScope).where(
            PolicyScope.policy_version_id.in_([version.id for version in versions])
        )
    )).scalars())
    return applicable_policy_versions(context, policies, versions, scopes)


def _summary(policy: Policy, version: PolicyVersion) -> dict:
    return {
        "policy_id": policy.id,
        "policy_key": policy.policy_key,
        "name": policy.name,
        "category": policy.category,
        "description": policy.description,
        "current_version_number": version.version_number,
        "effective_from": version.effective_from,
        "effective_until": version.effective_until,
    }


@router.get("", response_model=ApplicablePolicyListResponse)
async def list_applicable_policies(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    query: str | None = Query(None, max_length=80),
    category: str | None = Query(None, max_length=64),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    records = await _applicable_records(db, current_user)
    if query:
        needle = query.strip().casefold()
        records = [item for item in records if needle in item[0].policy_key.casefold() or needle in item[0].name.casefold()]
    if category:
        records = [item for item in records if item[0].category == category]
    records.sort(key=lambda item: (item[0].category, item[0].name, item[0].policy_key, item[0].id))
    total = len(records)
    start = (page - 1) * page_size
    return {
        "items": [_summary(policy, version) for policy, version in records[start:start + page_size]],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{policy_id}", response_model=ApplicablePolicyDetailResponse)
async def applicable_policy_detail(
    policy_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    for policy, version in await _applicable_records(db, current_user):
        if policy.id == policy_id:
            return {**_summary(policy, version), "content": version.content}
    raise HTTPException(status_code=404, detail="Policy not found")
