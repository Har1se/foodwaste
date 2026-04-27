from fastapi import APIRouter, Depends, Request
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_session
from app.core.redis import check_rate_limit
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import RegisterRequest, LoginRequest, AuthResponse, RefreshRequest, UserProfileResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserProfileResponse, status_code=201)
async def register(
    data: RegisterRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Register a new user account (customer or vendor)."""
    ip = request.client.host
    await check_rate_limit(f"ratelimit:register:{ip}", max_requests=3, window_seconds=3600)
    user = await auth_service.register_user(data, session)
    return UserProfileResponse.model_validate(user)


@router.post("/login", response_model=AuthResponse)
async def login(
    data: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Login and receive JWT access + refresh tokens."""
    ip = request.client.host
    await check_rate_limit(f"ratelimit:login:{ip}", max_requests=5, window_seconds=60)
    return await auth_service.login_user(data, session)


@router.post("/refresh", response_model=AuthResponse)
async def refresh(
    data: RefreshRequest,
    session: AsyncSession = Depends(get_session),
):
    """Exchange a valid refresh token for a new access token (token rotation)."""
    return await auth_service.refresh_tokens(data.refresh_token, session)


@router.post("/logout", status_code=204)
async def logout(data: RefreshRequest):
    """Revoke refresh token (invalidate session)."""
    await auth_service.logout_user(data.refresh_token)


@router.get("/me", response_model=UserProfileResponse)
async def me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user profile."""
    return UserProfileResponse.model_validate(current_user)
