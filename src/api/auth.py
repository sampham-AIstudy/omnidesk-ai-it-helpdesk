"""Auth API — Login, current user."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models.schemas import LoginRequest, TokenResponse, UserCreate, UserResponse, UserSelfUpdate
from src.models.user import User, UserRole
from src.services import auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = credentials.credentials
    payload = auth_service.decode_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = await auth_service.get_user_by_id(db, int(user_id))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    return current_user


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await auth_service.authenticate_user(db, payload.username, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tên đăng nhập hoặc mật khẩu không đúng",
        )

    token = auth_service.create_access_token({"sub": str(user.id)})
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_active_user)):
    return UserResponse.model_validate(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_my_profile(
    payload: UserSelfUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update only the authenticated user's non-privileged profile fields."""
    changes = payload.model_dump(exclude_unset=True)
    if "email" in changes:
        email = str(changes["email"]).lower()
        existing = await auth_service.get_user_by_email(db, email)
        if existing and existing.id != current_user.id:
            raise HTTPException(status_code=409, detail="Email này đã được sử dụng bởi một tài khoản khác")
        current_user.email = email
    if "full_name" in changes:
        current_user.full_name = changes["full_name"].strip()
    if "phone" in changes:
        current_user.phone = changes["phone"].strip() or None

    await db.flush()
    await db.refresh(current_user)
    return UserResponse.model_validate(current_user)


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Demo only — trong production chỉ admin mới tạo được user."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only administrators can create accounts")

    existing = await auth_service.get_user_by_username(db, payload.username)
    if existing:
        raise HTTPException(status_code=409, detail="Username đã tồn tại")

    email_in_use = await auth_service.get_user_by_email(db, payload.email.lower())
    if email_in_use:
        raise HTTPException(status_code=409, detail="Email is already in use")

    user_data = payload.model_dump()
    user_data["email"] = payload.email.lower()
    user = await auth_service.create_user(db, **user_data)
    return UserResponse.model_validate(user)
