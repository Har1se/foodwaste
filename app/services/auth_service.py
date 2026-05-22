import logging
import secrets
from datetime import datetime, timezone, timedelta

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import HTTPException, status

from app.models.user import User, OTPCode
from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
)
from app.core.redis import (
    store_refresh_token, get_user_id_from_refresh_token, revoke_refresh_token,
)
from app.config import settings
from app.schemas.auth import RegisterRequest, LoginRequest

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _generate_otp() -> str:
    # secrets.randbelow is cryptographically secure (unlike random.randint)
    return str(secrets.randbelow(900000) + 100000)


async def register_user(data: RegisterRequest, session: AsyncSession) -> tuple[User, str]:
    result = await session.execute(select(User).where(User.email == data.email))
    if result.scalars().first():
        raise HTTPException(status_code=409, detail="Email already registered")

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
        email_verified=settings.DEV_AUTO_VERIFY_EMAIL,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    otp_code = _generate_otp()
    otp = OTPCode(
        user_id=user.id,
        code=otp_code,
        expires_at=_utcnow() + timedelta(minutes=15),
    )
    session.add(otp)
    await session.commit()

    if settings.ENVIRONMENT != "production":
        logger.info("DEV OTP for %s: %s", user.email, otp_code)

    return user, otp_code


async def verify_email(email: str, code: str, session: AsyncSession) -> None:
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.email_verified:
        return

    result = await session.execute(
        select(OTPCode)
        .where(OTPCode.user_id == user.id, ~OTPCode.used)
        .order_by(OTPCode.created_at.desc())
    )
    otp = result.scalars().first()

    if not otp or otp.code != code or otp.expires_at < _utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired verification code")

    otp.used = True
    user.email_verified = True
    session.add(otp)
    session.add(user)
    await session.commit()


async def resend_verification(email: str, session: AsyncSession) -> str:
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.email_verified:
        raise HTTPException(status_code=400, detail="Email already verified")

    otp_code = _generate_otp()
    otp = OTPCode(
        user_id=user.id,
        code=otp_code,
        expires_at=_utcnow() + timedelta(minutes=15),
    )
    session.add(otp)
    await session.commit()
    return otp_code


async def forgot_password(email: str, session: AsyncSession) -> tuple[str, str] | None:
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if not user:
        return None

    otp_code = _generate_otp()
    user.reset_token = otp_code
    user.reset_token_expires = _utcnow() + timedelta(minutes=30)
    session.add(user)
    await session.commit()

    if settings.ENVIRONMENT != "production":
        logger.info("DEV reset OTP for %s: %s", user.email, otp_code)

    return user.email, otp_code


async def reset_password(email: str, code: str, new_password: str, session: AsyncSession) -> None:
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if not user or not user.reset_token or user.reset_token != code:
        raise HTTPException(status_code=400, detail="Invalid or expired reset code")
    if not user.reset_token_expires or user.reset_token_expires < _utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired reset code")

    user.password_hash = hash_password(new_password)
    user.reset_token = None
    user.reset_token_expires = None
    session.add(user)
    await session.commit()


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
    if not user.email_verified:
        raise HTTPException(status_code=403, detail="Please verify your email before logging in.")

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
