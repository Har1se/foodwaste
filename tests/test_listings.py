import pytest
from httpx import AsyncClient
from app.models.listing import AllergenCode
from app.services.listing_service import parse_allergens
from app.schemas.listing import AllergenFilterRequest


# ── Unit tests: allergen parser (pure business logic) ─────────────────────────

@pytest.mark.asyncio
async def test_allergen_parser_detects_gluten():
    result = await parse_allergens(AllergenFilterRequest(
        ingredients=["wheat flour", "sugar", "butter"],
        user_allergens=[AllergenCode.GLUTEN],
    ))
    assert result.safe is False
    assert AllergenCode.GLUTEN in result.detected_allergens
    assert "wheat flour" in result.flagged_ingredients


@pytest.mark.asyncio
async def test_allergen_parser_safe_for_user():
    result = await parse_allergens(AllergenFilterRequest(
        ingredients=["rice", "tomato", "olive oil"],
        user_allergens=[AllergenCode.GLUTEN, AllergenCode.DAIRY],
    ))
    assert result.safe is True
    assert result.flagged_ingredients == []


@pytest.mark.asyncio
async def test_allergen_parser_multiple_conflicts():
    result = await parse_allergens(AllergenFilterRequest(
        ingredients=["wheat flour", "milk", "eggs", "sugar"],
        user_allergens=[AllergenCode.GLUTEN, AllergenCode.DAIRY, AllergenCode.EGGS],
    ))
    assert result.safe is False
    assert len(result.flagged_ingredients) >= 2


@pytest.mark.asyncio
async def test_allergen_parser_detects_but_user_not_allergic():
    """Allergen present in food but user is not allergic to it — should be safe."""
    result = await parse_allergens(AllergenFilterRequest(
        ingredients=["wheat flour", "sugar"],
        user_allergens=[AllergenCode.DAIRY],  # user is only allergic to dairy
    ))
    assert result.safe is True
    assert AllergenCode.GLUTEN in result.detected_allergens
    assert result.flagged_ingredients == []


# ── Integration tests: listing endpoints ─────────────────────────────────────

@pytest.mark.asyncio
async def test_allergen_check_endpoint_requires_auth(client: AsyncClient):
    resp = await client.post("/listings/allergen-check", json={
        "ingredients": ["wheat flour"],
        "user_allergens": ["gluten"],
    })
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_allergen_check_endpoint_authenticated(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "allergyuser@test.kz",
        "password": "Secure123!",
        "role": "customer",
    })
    login = await client.post("/auth/login", json={
        "email": "allergyuser@test.kz",
        "password": "Secure123!",
    })
    token = login.json()["access_token"]

    resp = await client.post(
        "/listings/allergen-check",
        json={
            "ingredients": ["wheat flour", "sugar"],
            "user_allergens": ["gluten"],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["safe"] is False
    assert "gluten" in data["detected_allergens"]


@pytest.mark.asyncio
async def test_get_listings_public(client: AsyncClient):
    """GET /listings is public (no auth required)."""
    resp = await client.get("/listings")
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data
    assert "pagination" in data


@pytest.mark.asyncio
async def test_create_listing_requires_vendor_role(client: AsyncClient):
    """Customer cannot create listings — must get 403."""
    await client.post("/auth/register", json={
        "email": "notavendor@test.kz",
        "password": "Secure123!",
        "role": "customer",
    })
    login = await client.post("/auth/login", json={
        "email": "notavendor@test.kz",
        "password": "Secure123!",
    })
    token = login.json()["access_token"]

    resp = await client.post(
        "/listings",
        json={
            "title": "Test Listing",
            "description": "Test",
            "original_price": 2000,
            "discount_percentage": 30,
            "quantity_total": 5,
            "pickup_window_start": "2099-01-01T18:00:00",
            "pickup_window_end": "2099-01-01T20:00:00",
            "allergens": ["none"],
            "latitude": 43.2,
            "longitude": 76.8,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_listing_allergens_required(client: AsyncClient):
    """Listing with empty allergens list must fail validation."""
    await client.post("/auth/register", json={
        "email": "vendortest2@test.kz",
        "password": "Secure123!",
        "role": "vendor",
    })
    login = await client.post("/auth/login", json={
        "email": "vendortest2@test.kz",
        "password": "Secure123!",
    })
    token = login.json()["access_token"]

    resp = await client.post(
        "/listings",
        json={
            "title": "No allergen listing",
            "description": "Test",
            "original_price": 2000,
            "discount_percentage": 30,
            "quantity_total": 5,
            "pickup_window_start": "2099-01-01T18:00:00",
            "pickup_window_end": "2099-01-01T20:00:00",
            "allergens": [],   # EMPTY — must fail
            "latitude": 43.2,
            "longitude": 76.8,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422
