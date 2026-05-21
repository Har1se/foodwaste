import pytest
from httpx import AsyncClient


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _register_and_login(client: AsyncClient, email: str, role: str) -> str:
    await client.post("/auth/register", json={
        "email": email,
        "password": "Secure123!",
        "role": role,
    })
    login = await client.post("/auth/login", json={
        "email": email,
        "password": "Secure123!",
    })
    return login.json()["access_token"]


async def _create_vendor_profile(client: AsyncClient, token: str, bin_number: str = "123456789001") -> dict:
    resp = await client.post(
        "/vendors/register",
        json={
            "business_name": "Test Bakery",
            "bin_number": bin_number,
            "address": "123 Almaty St",
            "latitude": 43.2,
            "longitude": 76.8,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp


async def _create_listing(client: AsyncClient, token: str) -> dict:
    resp = await client.post(
        "/listings",
        json={
            "title": "Fresh Sourdough",
            "description": "Baked today",
            "original_price": 2000,
            "discount_percentage": 40,
            "quantity_total": 10,
            "pickup_window_start": "2099-06-01T18:00:00",
            "pickup_window_end": "2099-06-01T20:00:00",
            "allergens": ["gluten"],
            "latitude": 43.2,
            "longitude": 76.8,
            "category": "bakery",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp


# ── Vendor profile tests ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_vendor_register_profile(client: AsyncClient):
    """Vendor can create a vendor profile and it is auto-approved."""
    token = await _register_and_login(client, "vendorflow1@test.kz", "vendor")
    resp = await _create_vendor_profile(client, token, "110000000001")
    assert resp.status_code == 201
    data = resp.json()
    assert data["business_name"] == "Test Bakery"
    assert data["is_approved"] is True


@pytest.mark.asyncio
async def test_vendor_duplicate_registration(client: AsyncClient):
    """Registering a vendor profile twice returns 409."""
    token = await _register_and_login(client, "vendorflow2@test.kz", "vendor")
    await _create_vendor_profile(client, token, "110000000002")
    resp2 = await _create_vendor_profile(client, token, "110000000002")
    assert resp2.status_code == 409


@pytest.mark.asyncio
async def test_vendor_duplicate_bin(client: AsyncClient):
    """Two vendors with same BIN number returns 409."""
    token1 = await _register_and_login(client, "vendorbin1@test.kz", "vendor")
    token2 = await _register_and_login(client, "vendorbin2@test.kz", "vendor")

    resp1 = await client.post(
        "/vendors/register",
        json={"business_name": "Shop A", "bin_number": "DUPBIN001", "address": "A", "latitude": 43.2, "longitude": 76.8},
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert resp1.status_code == 201

    resp2 = await client.post(
        "/vendors/register",
        json={"business_name": "Shop B", "bin_number": "DUPBIN001", "address": "B", "latitude": 43.2, "longitude": 76.8},
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert resp2.status_code == 409


@pytest.mark.asyncio
async def test_get_my_vendor_profile(client: AsyncClient):
    """GET /vendors/me returns the vendor's own profile."""
    token = await _register_and_login(client, "vendorme@test.kz", "vendor")
    await _create_vendor_profile(client, token, "110000000003")

    resp = await client.get("/vendors/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["business_name"] == "Test Bakery"


@pytest.mark.asyncio
async def test_get_vendor_public(client: AsyncClient):
    """GET /vendors/{id} is public and returns vendor info."""
    token = await _register_and_login(client, "vendorpub@test.kz", "vendor")
    profile = await _create_vendor_profile(client, token, "110000000004")
    vendor_id = profile.json()["id"]

    resp = await client.get(f"/vendors/{vendor_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == vendor_id


@pytest.mark.asyncio
async def test_get_vendor_not_found(client: AsyncClient):
    """GET /vendors/99999 returns 404."""
    resp = await client.get("/vendors/99999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_my_vendor_not_found(client: AsyncClient):
    """GET /vendors/me without a profile returns 404."""
    token = await _register_and_login(client, "vendornoprofile@test.kz", "vendor")
    resp = await client.get("/vendors/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404


# ── Listing creation tests ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_vendor_create_listing(client: AsyncClient):
    """Approved vendor can create a listing."""
    token = await _register_and_login(client, "vendorlisting@test.kz", "vendor")
    await _create_vendor_profile(client, token, "110000000005")

    resp = await _create_listing(client, token)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Fresh Sourdough"
    assert data["discount_percentage"] == 40
    assert data["quantity_available"] == 10


@pytest.mark.asyncio
async def test_vendor_create_listing_no_profile(client: AsyncClient):
    """Vendor without a profile cannot create a listing (404)."""
    token = await _register_and_login(client, "vendornoprof2@test.kz", "vendor")
    resp = await _create_listing(client, token)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_vendor_get_my_listings(client: AsyncClient):
    """GET /listings/vendor/my-listings returns the vendor's own listings."""
    token = await _register_and_login(client, "vendormylist@test.kz", "vendor")
    await _create_vendor_profile(client, token, "110000000006")
    await _create_listing(client, token)

    resp = await client.get(
        "/listings/vendor/my-listings",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data
    assert "pagination" in data
    assert len(data["data"]) >= 1


@pytest.mark.asyncio
async def test_vendor_get_my_listings_no_profile(client: AsyncClient):
    """GET /listings/vendor/my-listings without a vendor profile returns 404."""
    token = await _register_and_login(client, "vendornoprof3@test.kz", "vendor")
    resp = await client.get(
        "/listings/vendor/my-listings",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# ── Full vendor → listing → order flow ───────────────────────────────────────

@pytest.mark.asyncio
async def test_customer_place_order(client: AsyncClient):
    """Customer can place an order on an active listing — full happy path."""
    vendor_token = await _register_and_login(client, "vendorfull@test.kz", "vendor")
    await _create_vendor_profile(client, vendor_token, "110000000007")
    listing_resp = await _create_listing(client, vendor_token)
    listing_id = listing_resp.json()["id"]

    customer_token = await _register_and_login(client, "customerfull@test.kz", "customer")

    resp = await client.post(
        "/orders",
        json={"items": [{"listing_id": listing_id, "quantity": 2}]},
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "pending"
    assert data["total_amount"] > 0
    assert data["pickup_token"] is not None
    assert len(data["items"]) == 1
    assert data["items"][0]["quantity"] == 2


@pytest.mark.asyncio
async def test_customer_list_own_orders(client: AsyncClient):
    """GET /orders returns cursor-paged list of customer's own orders."""
    vendor_token = await _register_and_login(client, "vendorordlist@test.kz", "vendor")
    await _create_vendor_profile(client, vendor_token, "110000000008")
    listing_resp = await _create_listing(client, vendor_token)
    listing_id = listing_resp.json()["id"]

    customer_token = await _register_and_login(client, "customerordlist@test.kz", "customer")
    await client.post(
        "/orders",
        json={"items": [{"listing_id": listing_id, "quantity": 1}]},
        headers={"Authorization": f"Bearer {customer_token}"},
    )

    resp = await client.get("/orders", headers={"Authorization": f"Bearer {customer_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data
    assert len(data["data"]) >= 1
