import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_order_requires_auth(client: AsyncClient):
    resp = await client.post("/orders", json={"items": [{"listing_id": 1, "quantity": 1}]})
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_order_vendor_cannot_order(client: AsyncClient):
    """Vendors cannot place orders — only customers can."""
    await client.post("/auth/register", json={
        "email": "ordervendor@test.kz",
        "password": "Secure123!",
        "role": "vendor",
    })
    login = await client.post("/auth/login", json={
        "email": "ordervendor@test.kz",
        "password": "Secure123!",
    })
    token = login.json()["access_token"]

    resp = await client.post(
        "/orders",
        json={"items": [{"listing_id": 999, "quantity": 1}]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_order_nonexistent_listing(client: AsyncClient):
    """Ordering a non-existent listing returns 404."""
    await client.post("/auth/register", json={
        "email": "ordercust@test.kz",
        "password": "Secure123!",
        "role": "customer",
    })
    login = await client.post("/auth/login", json={
        "email": "ordercust@test.kz",
        "password": "Secure123!",
    })
    token = login.json()["access_token"]

    resp = await client.post(
        "/orders",
        json={"items": [{"listing_id": 99999, "quantity": 1}]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_my_orders_pagination(client: AsyncClient):
    """GET /orders returns cursor-based paginated response."""
    await client.post("/auth/register", json={
        "email": "orderpager@test.kz",
        "password": "Secure123!",
        "role": "customer",
    })
    login = await client.post("/auth/login", json={
        "email": "orderpager@test.kz",
        "password": "Secure123!",
    })
    token = login.json()["access_token"]

    resp = await client.get(
        "/orders",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data
    assert "pagination" in data
    assert "next_cursor" in data["pagination"]
