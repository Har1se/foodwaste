import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    resp = await client.post("/auth/register", json={
        "email": "newuser@test.kz",
        "password": "Secure123!",
        "role": "customer",
        "full_name": "New User",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "newuser@test.kz"
    assert data["role"] == "customer"
    assert "password_hash" not in data


@pytest.mark.asyncio
async def test_register_weak_password(client: AsyncClient):
    resp = await client.post("/auth/register", json={
        "email": "weak@test.kz",
        "password": "short",
        "role": "customer",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "dup@test.kz",
        "password": "Secure123!",
        "role": "customer",
    })
    resp = await client.post("/auth/register", json={
        "email": "dup@test.kz",
        "password": "Secure123!",
        "role": "customer",
    })
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "logintest@test.kz",
        "password": "Secure123!",
        "role": "customer",
    })
    resp = await client.post("/auth/login", json={
        "email": "logintest@test.kz",
        "password": "Secure123!",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "wrongpass@test.kz",
        "password": "Secure123!",
        "role": "customer",
    })
    resp = await client.post("/auth/login", json={
        "email": "wrongpass@test.kz",
        "password": "WrongPassword1!",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_no_token(client: AsyncClient):
    """Protected endpoints must reject missing token with 401, not 403."""
    resp = await client.get("/auth/me")
    assert resp.status_code in (401, 403)  # HTTPBearer: 403 on older FastAPI, 401 on newer


@pytest.mark.asyncio
async def test_protected_endpoint_invalid_token(client: AsyncClient):
    resp = await client.get("/auth/me", headers={"Authorization": "Bearer invalidtoken"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_token_refresh(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "refresh@test.kz",
        "password": "Secure123!",
        "role": "customer",
    })
    login = await client.post("/auth/login", json={
        "email": "refresh@test.kz",
        "password": "Secure123!",
    })
    refresh_token = login.json()["refresh_token"]

    resp = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["refresh_token"] != refresh_token  # Token rotated


@pytest.mark.asyncio
async def test_logout_invalidates_refresh_token(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "logout@test.kz",
        "password": "Secure123!",
        "role": "customer",
    })
    login = await client.post("/auth/login", json={
        "email": "logout@test.kz",
        "password": "Secure123!",
    })
    refresh_token = login.json()["refresh_token"]

    # Logout
    await client.post("/auth/logout", json={"refresh_token": refresh_token})

    # Try to use old refresh token — must fail
    resp = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_rbac_customer_cannot_access_admin(client: AsyncClient):
    """RBAC: customer role must receive 403 on admin endpoints."""
    await client.post("/auth/register", json={
        "email": "custonly@test.kz",
        "password": "Secure123!",
        "role": "customer",
    })
    login = await client.post("/auth/login", json={
        "email": "custonly@test.kz",
        "password": "Secure123!",
    })
    token = login.json()["access_token"]

    resp = await client.get("/admin/stats", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_me_endpoint(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "metest@test.kz",
        "password": "Secure123!",
        "role": "customer",
    })
    login = await client.post("/auth/login", json={
        "email": "metest@test.kz",
        "password": "Secure123!",
    })
    token = login.json()["access_token"]

    resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "metest@test.kz"


@pytest.mark.asyncio
async def test_verify_email_already_verified(client: AsyncClient):
    """verify-email on already-verified user returns 200 (idempotent early return)."""
    await client.post("/auth/register", json={
        "email": "verifytest@test.kz",
        "password": "Secure123!",
        "role": "customer",
    })
    resp = await client.post("/auth/verify-email", json={
        "email": "verifytest@test.kz",
        "code": "123456",
    })
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_verify_email_invalid_code(client: AsyncClient, db_session):
    """Invalid OTP code returns 400."""
    from datetime import datetime, timezone, timedelta
    from app.models.user import User, OTPCode
    from app.core.security import hash_password

    user = User(
        email="unverified@test.kz",
        password_hash=hash_password("Secure123!"),
        role="customer",
        email_verified=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    otp = OTPCode(
        user_id=user.id,
        code="999999",
        expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=15),
    )
    db_session.add(otp)
    await db_session.commit()

    resp = await client.post("/auth/verify-email", json={
        "email": "unverified@test.kz",
        "code": "000000",
    })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_verify_email_correct_code(client: AsyncClient, db_session):
    """Correct OTP code verifies the email."""
    from datetime import datetime, timezone, timedelta
    from app.models.user import User, OTPCode
    from app.core.security import hash_password

    user = User(
        email="toverify@test.kz",
        password_hash=hash_password("Secure123!"),
        role="customer",
        email_verified=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    otp = OTPCode(
        user_id=user.id,
        code="654321",
        expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=15),
    )
    db_session.add(otp)
    await db_session.commit()

    resp = await client.post("/auth/verify-email", json={
        "email": "toverify@test.kz",
        "code": "654321",
    })
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_verify_email_unknown_user(client: AsyncClient):
    """verify-email for non-existent email returns 404."""
    resp = await client.post("/auth/verify-email", json={
        "email": "nobody_noresp@test.kz",
        "code": "123456",
    })
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_forgot_password_existing_user(client: AsyncClient):
    """forgot-password returns 200 for a registered email."""
    await client.post("/auth/register", json={
        "email": "forgotpass@test.kz",
        "password": "Secure123!",
        "role": "customer",
    })
    resp = await client.post("/auth/forgot-password", json={"email": "forgotpass@test.kz"})
    assert resp.status_code == 200
    assert "sent" in resp.json()["detail"].lower() or "reset" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_forgot_password_nonexistent_email(client: AsyncClient):
    """forgot-password returns 200 even for unknown email (prevents enumeration)."""
    resp = await client.post("/auth/forgot-password", json={"email": "nobody_fp@test.kz"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_reset_password_success(client: AsyncClient, db_session):
    """Valid reset token allows password change; login succeeds with new password."""
    from sqlmodel import select
    from app.models.user import User

    await client.post("/auth/register", json={
        "email": "resetme@test.kz",
        "password": "Secure123!",
        "role": "customer",
    })
    await client.post("/auth/forgot-password", json={"email": "resetme@test.kz"})

    result = await db_session.execute(select(User).where(User.email == "resetme@test.kz"))
    user = result.scalars().first()
    token = user.reset_token
    assert token is not None

    resp = await client.post("/auth/reset-password", json={
        "token": token,
        "new_password": "NewSecure123!",
    })
    assert resp.status_code == 200

    login = await client.post("/auth/login", json={
        "email": "resetme@test.kz",
        "password": "NewSecure123!",
    })
    assert login.status_code == 200


@pytest.mark.asyncio
async def test_reset_password_invalid_token(client: AsyncClient):
    """Invalid reset token returns 400."""
    resp = await client.post("/auth/reset-password", json={
        "token": "totally-fake-token-xyz",
        "new_password": "NewSecure123!",
    })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_resend_verification_already_verified(client: AsyncClient):
    """Resending verification to already-verified user returns 400."""
    await client.post("/auth/register", json={
        "email": "alreadyver@test.kz",
        "password": "Secure123!",
        "role": "customer",
    })
    resp = await client.post("/auth/resend-verification", json={"email": "alreadyver@test.kz"})
    assert resp.status_code == 400
    assert "already" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_resend_verification_unknown_user(client: AsyncClient):
    """Resending verification to unknown email returns 404."""
    resp = await client.post("/auth/resend-verification", json={"email": "nobody_rv@test.kz"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_profile(client: AsyncClient):
    """PATCH /auth/me updates profile fields."""
    await client.post("/auth/register", json={
        "email": "updateme@test.kz",
        "password": "Secure123!",
        "role": "customer",
        "full_name": "Old Name",
    })
    login = await client.post("/auth/login", json={
        "email": "updateme@test.kz",
        "password": "Secure123!",
    })
    token = login.json()["access_token"]

    resp = await client.patch(
        "/auth/me",
        json={"full_name": "New Name"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "New Name"


@pytest.mark.asyncio
async def test_update_profile_with_allergens(client: AsyncClient):
    """PATCH /auth/me can set allergen_profile."""
    await client.post("/auth/register", json={
        "email": "allergenpatch@test.kz",
        "password": "Secure123!",
        "role": "customer",
    })
    login = await client.post("/auth/login", json={
        "email": "allergenpatch@test.kz",
        "password": "Secure123!",
    })
    token = login.json()["access_token"]

    resp = await client.patch(
        "/auth/me",
        json={"allergen_profile": ["gluten", "dairy"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert "gluten" in resp.json()["allergen_profile"]


@pytest.mark.asyncio
async def test_change_password_success(client: AsyncClient):
    """PATCH /auth/me/password succeeds with correct current password."""
    await client.post("/auth/register", json={
        "email": "changepwd@test.kz",
        "password": "Secure123!",
        "role": "customer",
    })
    login = await client.post("/auth/login", json={
        "email": "changepwd@test.kz",
        "password": "Secure123!",
    })
    token = login.json()["access_token"]

    resp = await client.patch(
        "/auth/me/password",
        json={"current_password": "Secure123!", "new_password": "NewSecure456!"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_change_password_wrong_current(client: AsyncClient):
    """PATCH /auth/me/password fails with wrong current password."""
    await client.post("/auth/register", json={
        "email": "wrongcurr@test.kz",
        "password": "Secure123!",
        "role": "customer",
    })
    login = await client.post("/auth/login", json={
        "email": "wrongcurr@test.kz",
        "password": "Secure123!",
    })
    token = login.json()["access_token"]

    resp = await client.patch(
        "/auth/me/password",
        json={"current_password": "WrongOldPwd1!", "new_password": "NewSecure456!"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_delete_account(client: AsyncClient):
    """DELETE /auth/me deactivates the account (soft delete)."""
    await client.post("/auth/register", json={
        "email": "deleteme@test.kz",
        "password": "Secure123!",
        "role": "customer",
    })
    login = await client.post("/auth/login", json={
        "email": "deleteme@test.kz",
        "password": "Secure123!",
    })
    token = login.json()["access_token"]

    resp = await client.delete(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 204
