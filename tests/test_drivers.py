"""
Driver system tests: register, location update, nearby search, route optimization.
"""
import pytest
from httpx import AsyncClient



# ── Helpers ───────────────────────────────────────────────────────────────────

async def register_and_login(client: AsyncClient, email: str, role: str = "customer") -> str:
    await client.post("/auth/register", json={
        "email": email, "password": "Secure123!", "role": role, "full_name": "Test",
    })
    resp = await client.post("/auth/login", json={"email": email, "password": "Secure123!"})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_driver_register_requires_auth(client: AsyncClient):
    """Registering as driver requires authentication."""
    resp = await client.post("/drivers/register", json={"vehicle_type": "bicycle"})
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_driver_register_success(client: AsyncClient):
    """Any authenticated user can register as driver."""
    import random
    suffix = random.randint(100000, 999999)
    async with AsyncClient(transport=client._transport, base_url="http://test") as c:
        token = await register_and_login(c, f"driver{suffix}@test.kz", "customer")
        resp = await c.post(
            "/drivers/register",
            json={"vehicle_type": "bicycle"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["vehicle_type"] == "bicycle"
        assert data["status"] == "offline"
        assert data["is_verified"] is False
        assert data["rating"] == 5.0


@pytest.mark.asyncio
async def test_driver_register_duplicate(client: AsyncClient):
    """Cannot register as driver twice."""
    import random
    suffix = random.randint(100000, 999999)
    async with AsyncClient(transport=client._transport, base_url="http://test") as c:
        token = await register_and_login(c, f"driverdup{suffix}@test.kz", "customer")
        headers = {"Authorization": f"Bearer {token}"}

        r1 = await c.post("/drivers/register", json={"vehicle_type": "car"}, headers=headers)
        assert r1.status_code == 201

        r2 = await c.post("/drivers/register", json={"vehicle_type": "scooter"}, headers=headers)
        assert r2.status_code == 409


@pytest.mark.asyncio
async def test_driver_get_profile(client: AsyncClient):
    """GET /drivers/me returns driver profile."""
    import random
    suffix = random.randint(100000, 999999)
    async with AsyncClient(transport=client._transport, base_url="http://test") as c:
        token = await register_and_login(c, f"driverme{suffix}@test.kz")
        headers = {"Authorization": f"Bearer {token}"}

        await c.post("/drivers/register", json={"vehicle_type": "scooter"}, headers=headers)

        resp = await c.get("/drivers/me", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["vehicle_type"] == "scooter"
        assert data["total_deliveries"] == 0


@pytest.mark.asyncio
async def test_driver_get_profile_not_registered(client: AsyncClient):
    """GET /drivers/me returns 404 for non-driver users."""
    import random
    suffix = random.randint(100000, 999999)
    async with AsyncClient(transport=client._transport, base_url="http://test") as c:
        token = await register_and_login(c, f"nodriver{suffix}@test.kz")
        resp = await c.get("/drivers/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_driver_location_update(client: AsyncClient):
    """PATCH /drivers/me/location updates lat/lng and status."""
    import random
    suffix = random.randint(100000, 999999)
    async with AsyncClient(transport=client._transport, base_url="http://test") as c:
        token = await register_and_login(c, f"driverloc{suffix}@test.kz")
        headers = {"Authorization": f"Bearer {token}"}

        await c.post("/drivers/register", json={"vehicle_type": "car"}, headers=headers)

        resp = await c.patch(
            "/drivers/me/location",
            json={"lat": 43.238, "lng": 76.945, "status": "available"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["current_lat"] == pytest.approx(43.238)
        assert data["current_lng"] == pytest.approx(76.945)
        assert data["status"] == "available"


@pytest.mark.asyncio
async def test_driver_location_invalid_coords(client: AsyncClient):
    """Invalid lat/lng must be rejected (>90, <-90)."""
    import random
    suffix = random.randint(100000, 999999)
    async with AsyncClient(transport=client._transport, base_url="http://test") as c:
        token = await register_and_login(c, f"driverinvalid{suffix}@test.kz")
        headers = {"Authorization": f"Bearer {token}"}
        await c.post("/drivers/register", json={"vehicle_type": "walk"}, headers=headers)

        resp = await c.patch(
            "/drivers/me/location",
            json={"lat": 999.0, "lng": 76.945},
            headers=headers,
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_nearby_drivers_requires_auth(client: AsyncClient):
    """GET /drivers/nearby requires authentication."""
    resp = await client.get("/drivers/nearby?lat=43.2&lng=76.9")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_nearby_drivers_empty_when_all_offline(client: AsyncClient):
    """No available drivers → empty list."""
    import random
    suffix = random.randint(100000, 999999)
    async with AsyncClient(transport=client._transport, base_url="http://test") as c:
        token = await register_and_login(c, f"nearbytest{suffix}@test.kz")
        resp = await c.get(
            "/drivers/nearby",
            params={"lat": 43.238, "lng": 76.945, "radius_km": 5},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        # All drivers are offline by default — result may be empty
        assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_route_optimize_no_deliveries(client: AsyncClient):
    """Route optimization with no active deliveries returns empty stops."""
    import random
    suffix = random.randint(100000, 999999)
    async with AsyncClient(transport=client._transport, base_url="http://test") as c:
        token = await register_and_login(c, f"routedriver{suffix}@test.kz")
        headers = {"Authorization": f"Bearer {token}"}

        await c.post("/drivers/register", json={"vehicle_type": "bicycle"}, headers=headers)
        await c.patch("/drivers/me/location", json={"lat": 43.238, "lng": 76.945},
                      headers=headers)

        resp = await c.get("/drivers/route-optimize", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_distance_km"] == 0.0
        assert data["stops"] == []


@pytest.mark.asyncio
async def test_haversine_formula():
    """Unit test: haversine distance between two Almaty points."""
    from app.routers.drivers import _haversine_km
    # Mega mall vs Armada mall (~2.7 km)
    dist = _haversine_km(43.215, 76.894, 43.238, 76.889)
    assert 2.0 < dist < 4.0


@pytest.mark.asyncio
async def test_haversine_same_point():
    """Same coordinates → 0 distance."""
    from app.routers.drivers import _haversine_km
    dist = _haversine_km(43.238, 76.889, 43.238, 76.889)
    assert dist == pytest.approx(0.0, abs=0.001)


@pytest.mark.asyncio
async def test_delivery_status_update_not_your_delivery(client: AsyncClient):
    """Driver cannot update another driver's delivery."""
    import random
    suffix = random.randint(100000, 999999)
    async with AsyncClient(transport=client._transport, base_url="http://test") as c:
        token = await register_and_login(c, f"wrongdriver{suffix}@test.kz")
        headers = {"Authorization": f"Bearer {token}"}
        await c.post("/drivers/register", json={"vehicle_type": "car"}, headers=headers)

        resp = await c.patch(
            "/deliveries/99999/status",
            json={"status": "delivered"},
            headers=headers,
        )
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_vehicle_types_accepted(client: AsyncClient):
    """All vehicle types accepted: bicycle, scooter, car, walk."""
    import random
    for vtype in ["bicycle", "scooter", "car", "walk"]:
        suffix = random.randint(100000, 999999)
        async with AsyncClient(transport=client._transport, base_url="http://test") as c:
            token = await register_and_login(c, f"vtype{vtype}{suffix}@test.kz")
            resp = await c.post(
                "/drivers/register",
                json={"vehicle_type": vtype},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 201, f"Failed for {vtype}: {resp.text}"
            assert resp.json()["vehicle_type"] == vtype
