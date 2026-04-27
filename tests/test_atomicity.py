"""
Integration tests proving transaction atomicity.

test_overselling_impossible: skipped on SQLite (no SELECT FOR UPDATE support).
Passes on PostgreSQL in production — run with docker compose.
"""
import asyncio
import os
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.listing import Listing, ListingStatus
from app.models.order import Order
from app.models.vendor import Vendor
from app.models.user import User
from app.core.security import hash_password

IS_SQLITE = "sqlite" in os.environ.get("DATABASE_URL", "sqlite")


# ── Helpers ───────────────────────────────────────────────────────────────────

async def register_and_login(client: AsyncClient, email: str, role: str = "customer") -> str:
    await client.post("/auth/register", json={
        "email": email, "password": "Secure123!", "role": role, "full_name": "Test"
    })
    resp = await client.post("/auth/login", json={"email": email, "password": "Secure123!"})
    return resp.json()["access_token"]


async def create_approved_vendor_and_listing(qty: int) -> tuple[int, int]:
    """Create vendor + listing directly in DB. Returns (vendor_id, listing_id)."""
    from tests.conftest import TestSessionLocal
    from datetime import datetime, timedelta
    import random

    async with TestSessionLocal() as s:
        suffix = random.randint(10000, 99999)
        user = User(
            email=f"vendor{suffix}@test.kz",
            password_hash=hash_password("Secure123!"),
            role="vendor",
            is_active=True,
        )
        s.add(user)
        await s.flush()

        vendor = Vendor(
            user_id=user.id,
            business_name=f"Bakery {suffix}",
            bin_number=f"BIN{suffix:07d}",
            address="Almaty, test",
            latitude=43.238,
            longitude=76.889,
            is_approved=True,
        )
        s.add(vendor)
        await s.flush()

        listing = Listing(
            vendor_id=vendor.id,
            title="Last Croissant",
            description="Only one left!",
            original_price=2000,
            current_price=1400,
            discount_percentage=30.0,
            quantity_total=qty,
            quantity_available=qty,
            status=ListingStatus.ACTIVE,
            pickup_window_start=datetime.utcnow(),
            pickup_window_end=datetime.utcnow() + timedelta(hours=3),
            latitude=43.238,
            longitude=76.889,
        )
        s.add(listing)
        await s.commit()
        return vendor.id, listing.id


def get_app():
    from app.main import app
    return app


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.skipif(IS_SQLITE, reason="SELECT FOR UPDATE requires PostgreSQL. Run with docker compose up to verify.")
async def test_overselling_impossible(db_session: AsyncSession):
    """
    ATOMICITY TEST (PostgreSQL only): Two concurrent requests for the last 1 unit.
    Expected: exactly 1 success (201) and 1 conflict (409).
    Proves SELECT FOR UPDATE prevents overselling under concurrency.
    """
    vendor_id, listing_id = await create_approved_vendor_and_listing(qty=1)
    app = get_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c1, \
               AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c2:
        import random
        s = random.randint(10000, 99999)
        token1 = await register_and_login(c1, f"buyer1x{s}@test.kz")
        token2 = await register_and_login(c2, f"buyer2x{s}@test.kz")

        payload = {"items": [{"listing_id": listing_id, "quantity": 1}]}
        resp1, resp2 = await asyncio.gather(
            c1.post("/orders", json=payload, headers={"Authorization": f"Bearer {token1}"}),
            c2.post("/orders", json=payload, headers={"Authorization": f"Bearer {token2}"}),
        )

    statuses = sorted([resp1.status_code, resp2.status_code])
    assert statuses == [201, 409], (
        f"Overselling detected! Both returned: {resp1.status_code}, {resp2.status_code}"
    )

    from tests.conftest import TestSessionLocal
    async with TestSessionLocal() as s:
        r = await s.execute(select(Listing).where(Listing.id == listing_id))
        listing = r.scalars().first()
        assert listing.quantity_available == 0
        assert listing.status == ListingStatus.SOLD_OUT


@pytest.mark.asyncio
async def test_double_entry_order_total(db_session: AsyncSession):
    """
    ATOMICITY TEST: Order total = sum(unit_price × quantity) for all items.
    Verifies price snapshot stored correctly at order creation time.
    current_price=1400, qty=3 → total must be 4200 KZT.
    """
    vendor_id, listing_id = await create_approved_vendor_and_listing(qty=10)
    app = get_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        import random
        token = await register_and_login(client, f"pricebuyer{random.randint(1,99999)}@test.kz")
        resp = await client.post(
            "/orders",
            json={"items": [{"listing_id": listing_id, "quantity": 3}]},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 201, resp.text
    data = resp.json()

    # Verify: total == sum of (unit_price × quantity) per item
    items = data["items"]
    computed_total = sum(i["unit_price"] * i["quantity"] for i in items)
    assert data["total_amount"] == computed_total, (
        f"total_amount {data['total_amount']} != computed {computed_total}"
    )
    # unit_price must be current_price snapshot (1400), not original_price (2000)
    assert items[0]["unit_price"] == 1400
    assert data["total_amount"] == 1400 * 3  # 4200 KZT


@pytest.mark.asyncio
async def test_cancel_restores_stock(db_session: AsyncSession):
    """
    ATOMICITY TEST: Cancelling an order restores quantity_available exactly.
    Place order for 2 units from stock of 5 → cancel → stock back to 5.
    """
    vendor_id, listing_id = await create_approved_vendor_and_listing(qty=5)
    app = get_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        import random
        token = await register_and_login(client, f"cancelbuyer{random.randint(1,99999)}@test.kz")

        order_resp = await client.post(
            "/orders",
            json={"items": [{"listing_id": listing_id, "quantity": 2}]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert order_resp.status_code == 201
        order_id = order_resp.json()["id"]

        cancel_resp = await client.patch(
            f"/orders/{order_id}/status",
            json={"status": "cancelled"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert cancel_resp.status_code == 200
        assert cancel_resp.json()["status"] == "cancelled"

    from tests.conftest import TestSessionLocal
    async with TestSessionLocal() as s:
        r = await s.execute(select(Listing).where(Listing.id == listing_id))
        listing = r.scalars().first()
        assert listing.quantity_available == 5, (
            f"Stock should be 5 after cancel, got {listing.quantity_available}"
        )


@pytest.mark.asyncio
async def test_insufficient_stock_returns_409(db_session: AsyncSession):
    """
    ATOMICITY TEST: Ordering more than available stock returns 409 Conflict.
    Stock=1, request for qty=5 must fail immediately.
    """
    vendor_id, listing_id = await create_approved_vendor_and_listing(qty=1)
    app = get_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        import random
        token = await register_and_login(client, f"overbuyer{random.randint(1,99999)}@test.kz")
        resp = await client.post(
            "/orders",
            json={"items": [{"listing_id": listing_id, "quantity": 5}]},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 409, f"Expected 409, got {resp.status_code}: {resp.text}"
    assert "stock" in resp.json()["detail"].lower() or "insufficient" in resp.json()["detail"].lower()
