from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import HTTPException, status

from app.models.user import User, UserRole
from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
)
from app.core.redis import (
    store_refresh_token, get_user_id_from_refresh_token, revoke_refresh_token,
)
from app.config import settings
from app.schemas.auth import RegisterRequest, LoginRequest


async def register_user(data: RegisterRequest, session: AsyncSession) -> User:
    # Check email uniqueness
    result = await session.execute(select(User).where(User.email == data.email))
    if result.scalars().first():
        raise HTTPException(status_code=409, detail="Email already registered")

    # Check phone uniqueness if provided
    if data.phone:
        result = await session.execute(select(User).where(User.phone == data.phone))
        if result.scalars().first():
            raise HTTPException(status_code=409, detail="Phone number already registered")

    user = User(
        email=data.email,
        phone=data.phone,
        full_name=data.full_name,
        password_hash=hash_password(data.password),
        role=data.role,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def login_user(data: LoginRequest, session: AsyncSession) -> dict:
    result = await session.execute(select(User).where(User.email == data.email))
    user = result.scalars().first()

    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is suspended")

    access_token = create_access_token({"user_id": user.id, "role": user.role.value})
    refresh_token = create_refresh_token()

    await store_refresh_token(user.id, refresh_token, settings.REFRESH_TOKEN_EXPIRE_DAYS)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


async def refresh_tokens(refresh_token: str, session: AsyncSession) -> dict:
    user_id = await get_user_id_from_refresh_token(refresh_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    # Rotate refresh token
    await revoke_refresh_token(refresh_token)
    new_refresh = create_refresh_token()
    access_token = create_access_token({"user_id": user.id, "role": user.role.value})

    await store_refresh_token(user.id, new_refresh, settings.REFRESH_TOKEN_EXPIRE_DAYS)

    return {
        "access_token": access_token,
        "refresh_token": new_refresh,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


async def logout_user(refresh_token: str):
    await revoke_refresh_token(refresh_token)
