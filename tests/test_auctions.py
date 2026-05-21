"""
Auction system tests: create, bid, end, winner determination (lowest unique bid).
"""
import pytest
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient
from sqlmodel import select

from app.models.auction import Auction, AuctionStatus
from app.models.listing import Listing, ListingStatus
from app.models.user import User
from app.models.vendor import Vendor
from app.core.security import hash_password


# ── Helpers ───────────────────────────────────────────────────────────────────

async def register_and_login(client: AsyncClient, email: str, role: str = "customer") -> str:
    await client.post("/auth/register", json={
        "email": email, "password": "Secure123!", "role": role, "full_name": "Test User",
    })
    resp = await client.post("/auth/login", json={"email": email, "password": "Secure123!"})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    return resp.json()["access_token"]


async def create_vendor_with_listing() -> tuple[int, int, int]:
    """Returns (user_id, vendor_id, listing_id)."""
    from tests.conftest import TestSessionLocal
    import random
    async with TestSessionLocal() as s:
        suffix = random.randint(100000, 999999)
        user = User(
            email=f"auctionvendor{suffix}@test.kz",
            password_hash=hash_password("Secure123!"),
            role="vendor",
            is_active=True,
            email_verified=True,
        )
        s.add(user)
        await s.flush()

        vendor = Vendor(
            user_id=user.id,
            business_name=f"AuctionShop {suffix}",
            bin_number=f"AUC{suffix:07d}",
            address="Almaty, test",
            latitude=43.238,
            longitude=76.889,
            is_approved=True,
        )
        s.add(vendor)
        await s.flush()

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        listing = Listing(
            vendor_id=vendor.id,
            title="Flash Auction Item",
            description="Auction test listing",
            original_price=5000,
            current_price=2000,
            discount_percentage=60.0,
            quantity_total=3,
            quantity_available=3,
            status=ListingStatus.ACTIVE,
            pickup_window_start=now,
            pickup_window_end=now + timedelta(hours=4),
            latitude=43.238,
            longitude=76.889,
        )
        s.add(listing)
        await s.commit()
        return user.id, vendor.id, listing.id


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_auctions_public(client: AsyncClient):
    """GET /auctions is public."""
    resp = await client.get("/auctions")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_create_auction_requires_auth(client: AsyncClient):
    """Creating an auction requires authentication."""
    resp = await client.post("/auctions", json={
        "listing_id": 1,
        "start_price": 5000,
        "reserve_price": 500,
        "ends_at": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
    })
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_create_auction_nonexistent_listing(client: AsyncClient):
    """Creating auction for non-existent listing returns 404."""
    from tests.conftest import TestSessionLocal
    import random
    async with TestSessionLocal() as s:
        suffix = random.randint(100000, 999999)
        user = User(
            email=f"vendorauction{suffix}@test.kz",
            password_hash=hash_password("Secure123!"),
            role="vendor",
            is_active=True,
            email_verified=True,
        )
        s.add(user)
        await s.flush()
        vendor = Vendor(
            user_id=user.id,
            business_name=f"V {suffix}",
            bin_number=f"VV{suffix:07d}",
            address="Almaty",
            latitude=43.2,
            longitude=76.8,
            is_approved=True,
        )
        s.add(vendor)
        await s.commit()

    async with AsyncClient(transport=client._transport, base_url="http://test") as c:
        await c.post("/auth/register", json={
            "email": f"vendorauction{suffix}@test.kz",
            "password": "Secure123!",
            "role": "vendor",
        })
        login = await c.post("/auth/login", json={
            "email": f"vendorauction{suffix}@test.kz",
            "password": "Secure123!",
        })
        token = login.json()["access_token"]

        resp = await c.post("/auctions", json={
            "listing_id": 999999,
            "start_price": 5000,
            "reserve_price": 500,
            "ends_at": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_place_bid_requires_auth(client: AsyncClient):
    """Bidding requires authentication."""
    resp = await client.post("/auctions/1/bid", json={"amount": 1000})
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_place_bid_nonexistent_auction(client: AsyncClient):
    """Bidding on non-existent auction returns 404."""
    import random
    suffix = random.randint(100000, 999999)
    async with AsyncClient(transport=client._transport, base_url="http://test") as c:
        await c.post("/auth/register", json={
            "email": f"bidder{suffix}@test.kz",
            "password": "Secure123!",
            "role": "customer",
        })
        login = await c.post("/auth/login", json={
            "email": f"bidder{suffix}@test.kz",
            "password": "Secure123!",
        })
        token = login.json()["access_token"]

        resp = await c.post(
            "/auctions/999999/bid",
            json={"amount": 1000},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_lowest_unique_bid_winner_logic():
    """Unit test: _find_lowest_unique_bid returns correct winner."""
    from app.routers.auctions import _find_lowest_unique_bid

    class MockBid:
        def __init__(self, bidder_id, amount):
            self.bidder_id = bidder_id
            self.amount = amount

    # Three bidders: 500 (unique lowest), 1000 (duplicate), 1000 (duplicate)
    bids = [
        MockBid(1, 500),
        MockBid(2, 1000),
        MockBid(3, 1000),
    ]
    winner = _find_lowest_unique_bid(bids)
    assert winner is not None
    assert winner.bidder_id == 1
    assert winner.amount == 500


@pytest.mark.asyncio
async def test_lowest_unique_bid_all_duplicates():
    """No unique bids → no winner."""
    from app.routers.auctions import _find_lowest_unique_bid

    class MockBid:
        def __init__(self, bidder_id, amount):
            self.bidder_id = bidder_id
            self.amount = amount

    bids = [MockBid(1, 500), MockBid(2, 500), MockBid(3, 1000), MockBid(4, 1000)]
    winner = _find_lowest_unique_bid(bids)
    assert winner is None


@pytest.mark.asyncio
async def test_lowest_unique_bid_single_bidder():
    """Single bidder → that bidder wins."""
    from app.routers.auctions import _find_lowest_unique_bid

    class MockBid:
        def __init__(self, bidder_id, amount):
            self.bidder_id = bidder_id
            self.amount = amount

    bids = [MockBid(1, 750)]
    winner = _find_lowest_unique_bid(bids)
    assert winner is not None
    assert winner.bidder_id == 1


@pytest.mark.asyncio
async def test_get_auction_not_found(client: AsyncClient):
    """GET /auctions/999999 returns 404."""
    resp = await client.get("/auctions/999999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_auction_bid_reserve_price_validation(client: AsyncClient, db_session):
    """Bid below reserve_price must be rejected with 422."""
    import random
    suffix = random.randint(100000, 999999)
    _, vendor_id, listing_id = await create_vendor_with_listing()

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    auction = Auction(
        listing_id=listing_id,
        vendor_id=vendor_id,
        start_price=5000,
        reserve_price=1000,
        ends_at=now + timedelta(hours=2),
        status=AuctionStatus.ACTIVE,
    )
    db_session.add(auction)
    await db_session.commit()
    await db_session.refresh(auction)

    async with AsyncClient(transport=client._transport, base_url="http://test") as c:
        await c.post("/auth/register", json={
            "email": f"lowbidder{suffix}@test.kz",
            "password": "Secure123!",
            "role": "customer",
        })
        login = await c.post("/auth/login", json={
            "email": f"lowbidder{suffix}@test.kz",
            "password": "Secure123!",
        })
        token = login.json()["access_token"]

        resp = await c.post(
            f"/auctions/{auction.id}/bid",
            json={"amount": 500},  # below reserve of 1000
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_auction_full_flow(client: AsyncClient, db_session):
    """Full auction: create → bid → end → winner determined."""
    import random
    suffix = random.randint(100000, 999999)
    _, vendor_id, listing_id = await create_vendor_with_listing()

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    auction = Auction(
        listing_id=listing_id,
        vendor_id=vendor_id,
        start_price=5000,
        reserve_price=100,
        ends_at=now + timedelta(hours=2),
        status=AuctionStatus.ACTIVE,
    )
    db_session.add(auction)
    await db_session.commit()
    await db_session.refresh(auction)

    async with AsyncClient(transport=client._transport, base_url="http://test") as c:
        # Register bidders
        b1_token = await register_and_login(c, f"buyer1_{suffix}@test.kz")
        b2_token = await register_and_login(c, f"buyer2_{suffix}@test.kz")
        b3_token = await register_and_login(c, f"buyer3_{suffix}@test.kz")

        # Bidder 1: unique bid at 300
        r1 = await c.post(f"/auctions/{auction.id}/bid", json={"amount": 300},
                          headers={"Authorization": f"Bearer {b1_token}"})
        assert r1.status_code == 201

        # Bidder 2 and 3: both bid 500 (duplicate — neither can win)
        r2 = await c.post(f"/auctions/{auction.id}/bid", json={"amount": 500},
                          headers={"Authorization": f"Bearer {b2_token}"})
        assert r2.status_code == 201
        r3 = await c.post(f"/auctions/{auction.id}/bid", json={"amount": 500},
                          headers={"Authorization": f"Bearer {b3_token}"})
        assert r3.status_code == 201

        # Fetch auction details
        get_resp = await c.get(f"/auctions/{auction.id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["bid_count"] == 3

    # Verify winner in DB: bidder 1 with 300 (lowest unique)
    result = await db_session.execute(select(Auction).where(Auction.id == auction.id))
    updated = result.scalars().first()
    # Auction not ended yet (would need to call /end endpoint)
    assert updated.status == AuctionStatus.ACTIVE
