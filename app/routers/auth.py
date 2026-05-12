import json

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_session
from app.core.redis import check_rate_limit
from app.core.dependencies import get_current_user
from app.core.security import verify_password, hash_password
from app.models.user import User
from app.schemas.auth import (
    RegisterRequest, LoginRequest, AuthResponse, RefreshRequest,
    UpdateProfileRequest, ChangePasswordRequest,
    UserProfileResponse,
)
from app.services import auth_service
from app.tasks.email_tasks import (
    send_verification_email,
    send_password_reset_email,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@router.post("/register", response_model=UserProfileResponse, status_code=201)
async def register(
    data: RegisterRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Register a new user account. Sends a 6-digit OTP to the provided email."""
    ip = request.client.host
    await check_rate_limit(f"ratelimit:register:{ip}", max_requests=3, window_seconds=3600)
    user, otp_code = await auth_service.register_user(data, session)
    send_verification_email.delay(user.email, otp_code)
    return UserProfileResponse.model_validate(user)


@router.post("/verify-email", status_code=200)
async def verify_email(
    data: VerifyEmailRequest,
    session: AsyncSession = Depends(get_session),
):
    """Verify email address using the 6-digit OTP sent at registration."""
    await auth_service.verify_email(data.email, data.code, session)
    return {"detail": "Email verified successfully. You can now log in."}


@router.post("/resend-verification", status_code=200)
async def resend_verification(
    data: ResendVerificationRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Resend the email verification OTP."""
    ip = request.client.host
    await check_rate_limit(f"ratelimit:resend:{ip}", max_requests=3, window_seconds=3600)
    otp_code = await auth_service.resend_verification(data.email, session)
    send_verification_email.delay(data.email, otp_code)
    return {"detail": "Verification code sent. Check your inbox."}


@router.post("/forgot-password", status_code=200)
async def forgot_password(
    data: ForgotPasswordRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Request a password reset link via email."""
    ip = request.client.host
    await check_rate_limit(f"ratelimit:forgot:{ip}", max_requests=3, window_seconds=3600)
    result = await auth_service.forgot_password(data.email, session)
    if result:
        email, reset_token = result
        send_password_reset_email.delay(email, reset_token)
    # Always return 200 to prevent email enumeration
    return {"detail": "If an account with that email exists, a reset link has been sent."}


@router.post("/reset-password", status_code=200)
async def reset_password(
    data: ResetPasswordRequest,
    session: AsyncSession = Depends(get_session),
):
    """Set a new password using the token from the reset email."""
    await auth_service.reset_password(data.token, data.new_password, session)
    return {"detail": "Password reset successfully. You can now log in."}


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


@router.patch("/me", response_model=UserProfileResponse)
async def update_me(
    data: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Update own profile: full_name, phone, allergen_profile."""
    if data.full_name is not None:
        current_user.full_name = data.full_name

    if data.phone is not None:
        existing = await session.execute(
            select(User).where(User.phone == data.phone, User.id != current_user.id)
        )
        if existing.scalars().first():
            raise HTTPException(status_code=409, detail="Phone number already in use")
        current_user.phone = data.phone

    if data.allergen_profile is not None:
        current_user.allergen_profile = json.dumps(data.allergen_profile)

    session.add(current_user)
    await session.commit()
    await session.refresh(current_user)
    return UserProfileResponse.model_validate(current_user)


@router.patch("/me/password", status_code=204)
async def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Change own password (requires current password for verification)."""
    if not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    current_user.password_hash = hash_password(data.new_password)
    session.add(current_user)
    await session.commit()


@router.delete("/me", status_code=204)
async def delete_account(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Soft-delete: deactivates the account. Use admin hard-delete to remove permanently."""
    current_user.is_active = False
    session.add(current_user)
    await session.commit()
