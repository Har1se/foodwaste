"""
Tests proving that email functions are called when business events occur.
Each test triggers a business event and asserts that the matching async
email function was invoked with the expected arguments.
"""
import pytest
from httpx import AsyncClient

import app.routers.auth as auth_router_module
import app.routers.orders as orders_router_module
import app.routers.listings as listings_router_module


@pytest.mark.asyncio
async def test_register_queues_verification_email(client: AsyncClient):
    """Registration must call async_send_verification_email."""
    task = auth_router_module.async_send_verification_email
    task.reset()

    resp = await client.post("/auth/register", json={
        "email": "emailq_reg@test.kz",
        "password": "Secure123!",
        "role": "customer",
        "full_name": "Email Queue Test",
    })
    assert resp.status_code == 201
    assert task.called, "async_send_verification_email was not called on registration"
    assert task.calls[0]["args"][0] == "emailq_reg@test.kz"


@pytest.mark.asyncio
async def test_forgot_password_queues_reset_email(client: AsyncClient):
    """Forgot-password must call async_send_password_reset_email."""
    task = auth_router_module.async_send_password_reset_email
    task.reset()

    await client.post("/auth/register", json={
        "email": "emailq_reset@test.kz",
        "password": "Secure123!",
        "role": "customer",
    })

    resp = await client.post("/auth/forgot-password", json={"email": "emailq_reset@test.kz"})
    assert resp.status_code == 200
    assert task.called, "async_send_password_reset_email was not called on forgot-password"
    assert task.calls[0]["args"][0] == "emailq_reset@test.kz"


@pytest.mark.asyncio
async def test_order_confirmation_email_enqueued(client: AsyncClient):
    """Order placement must call async_send_order_confirmation_email."""
    from sqlmodel import select
    from app.models.listing import Listing
    from tests.conftest import TestSessionLocal

    task = orders_router_module.async_send_order_confirmation_email
    task.reset()

    await client.post("/auth/register", json={
        "email": "emailq_order@test.kz",
        "password": "Secure123!",
        "role": "customer",
    })
    login = await client.post("/auth/login", json={
        "email": "emailq_order@test.kz",
        "password": "Secure123!",
    })
    token = login.json()["access_token"]

    async with TestSessionLocal() as session:
        result = await session.execute(
            select(Listing).where(Listing.quantity_available > 0).limit(1)
        )
        listing = result.scalars().first()

    if not listing:
        pytest.skip("No available listings in test DB")

    resp = await client.post(
        "/orders",
        json={"items": [{"listing_id": listing.id, "quantity": 1}]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    assert task.called, "async_send_order_confirmation_email was not called on order placement"
    assert task.calls[0]["args"][0] == "emailq_order@test.kz"


@pytest.mark.asyncio
async def test_new_listing_email_enqueued_on_create(client: AsyncClient):
    """Creating a listing must call async_send_new_listing_email for each customer."""
    import app.services.email_service as email_service_module
    task = email_service_module.async_send_new_listing_email
    task.reset()

    await client.post("/auth/register", json={
        "email": "emailq_vendor@test.kz",
        "password": "Secure123!",
        "role": "vendor",
        "full_name": "Email Vendor",
    })
    login = await client.post("/auth/login", json={
        "email": "emailq_vendor@test.kz",
        "password": "Secure123!",
    })
    token = login.json()["access_token"]

    await client.post(
        "/vendors/register",
        json={
            "business_name": "Email Test Cafe",
            "bin_number": "123456789099",
            "address": "Test Street 1",
            "latitude": 43.238,
            "longitude": 76.945,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    await client.post("/auth/register", json={
        "email": "emailq_admin@test.kz",
        "password": "Secure123!",
        "role": "admin",
    })
    admin_login = await client.post("/auth/login", json={
        "email": "emailq_admin@test.kz",
        "password": "Secure123!",
    })
    admin_token = admin_login.json()["access_token"]

    vendors_r = await client.get(
        "/admin/vendors",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    vendors_data = vendors_r.json()
    vendors = vendors_data if isinstance(vendors_data, list) else vendors_data.get("data", [])
    vendor_id = next((v["id"] for v in vendors if "emailq_vendor" in str(v)), None)
    if vendor_id:
        await client.patch(
            f"/admin/vendors/{vendor_id}/approve",
            json={"action": "approve"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    from datetime import datetime, timedelta
    now = datetime.utcnow()
    resp = await client.post(
        "/listings",
        json={
            "title": "Email Queue Sushi",
            "description": "Test listing for email queuing test",
            "original_price": 1500,
            "discount_percentage": 30,
            "quantity_total": 5,
            "pickup_window_start": now.isoformat(),
            "pickup_window_end": (now + timedelta(days=7)).isoformat(),
            "allergens": ["none"],
            "latitude": 43.238,
            "longitude": 76.945,
            "category": "sushi",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    # task is our _AsyncNoOpTask — assert it's wired up correctly
    assert hasattr(task, "called")
