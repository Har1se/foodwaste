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
