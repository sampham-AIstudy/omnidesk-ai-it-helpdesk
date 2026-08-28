"""Auth service — JWT + role-based permissions."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.models.user import CompanyUnit, User, UserRole

settings = get_settings()


# ─── Password Utilities ───────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    pwd_bytes = plain.encode("utf-8")[:72]
    hashed_bytes = hashed.encode("utf-8")
    return bcrypt.checkpw(pwd_bytes, hashed_bytes)


# ─── JWT Utilities ────────────────────────────────────────────────────────────

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.jwt_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError:
        return {}


# ─── DB Operations ────────────────────────────────────────────────────────────

async def authenticate_user(db: AsyncSession, username: str, password: str) -> User | None:
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user or not user.is_active or not verify_password(password, user.hashed_password):
        return None
    return user


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, **kwargs) -> User:
    password = kwargs.pop("password")
    user = User(**kwargs, hashed_password=hash_password(password))
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


# ─── Permission Checks ────────────────────────────────────────────────────────

def require_role(*roles: UserRole):
    """Return checker function for role-based access."""
    def check(user: User) -> bool:
        return user.role in roles
    return check


ROLE_HIERARCHY = {
    UserRole.ADMIN: 4,
    UserRole.MANAGER: 3,
    UserRole.TECHNICIAN: 2,
    UserRole.EMPLOYEE: 1,
}


def has_min_role(user: User, min_role: UserRole) -> bool:
    return ROLE_HIERARCHY.get(user.role, 0) >= ROLE_HIERARCHY.get(min_role, 0)


def can_approve_hitl(user: User) -> bool:
    """KTV hoặc Admin có thể xác nhận quyết định ticket (Manager đã bị xóa)."""
    return user.role in (UserRole.TECHNICIAN, UserRole.ADMIN)


def can_access_company_unit(user: User, company_unit: CompanyUnit | str | None) -> bool:
    """Central tenant boundary: only Admin or corporate IT may cross units."""
    if user.role == UserRole.ADMIN or user.company_unit == CompanyUnit.CORPORATE:
        return True
    if company_unit is None:
        candidate = ""
    elif hasattr(company_unit, "value"):
        candidate = str(getattr(company_unit, "value"))
    else:
        candidate = str(company_unit)
    return candidate == user.company_unit.value


def scoped_company_unit(user: User) -> CompanyUnit | None:
    """Return a required tenant filter, or ``None`` for centrally authorized roles."""
    return None if user.role == UserRole.ADMIN or user.company_unit == CompanyUnit.CORPORATE else user.company_unit


def can_view_ticket(user: User, ticket) -> bool:
    """Employee chỉ xem ticket của mình; tech/manager xem tất cả trong company."""
    if user.role == UserRole.ADMIN:
        return True
    if user.role in (UserRole.MANAGER, UserRole.TECHNICIAN):
        return can_access_company_unit(user, ticket.submitter.company_unit)
    # Employee chỉ xem ticket của mình
    return ticket.submitter_id == user.id
