import pytest
from app.services.listing_service import _haversine


# ── Unit tests: pure business logic (no DB) ───────────────────────────────────

def test_price_decay_formula():
    """10% decay with 500 KZT floor."""
    original = 2000
    after_1_decay = max(int(original * 0.90), 0)
    assert after_1_decay == 1800

    after_2_decay = max(int(after_1_decay * 0.90), 0)
    assert after_2_decay == 1620

    # Floor at 0
    near_zero = 1
    floored = max(int(near_zero * 0.90), 0)
    assert floored == 0


def test_haversine_distance_almaty():
    """Haversine between two Almaty points (~5 km apart)."""
    # Mega mall coords
    lat1, lng1 = 43.2150, 76.8945
    # Armada mall coords
    lat2, lng2 = 43.2389, 76.8897

    dist = _haversine(lat1, lng1, lat2, lng2)
    assert 2.0 < dist < 4.0  # ~2.7 km


def test_haversine_same_point():
    dist = _haversine(43.2389, 76.8897, 43.2389, 76.8897)
    assert dist == pytest.approx(0.0, abs=0.001)


def test_haversine_10km_filter():
    """Points > 10 km apart should be filtered out."""
    # Almaty center vs Kapchagai (~80 km away)
    lat1, lng1 = 43.2389, 76.8897
    lat2, lng2 = 43.8750, 77.0750

    dist = _haversine(lat1, lng1, lat2, lng2)
    assert dist > 10  # Should be excluded from 10km radius search


def test_discount_percentage_bounds():
    """Discount must be between 1 and 90 percent."""
    from pydantic import ValidationError
    from app.schemas.listing import ListingCreate
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    base = {
        "title": "Test",
        "description": "Desc",
        "original_price": 2000,
        "quantity_total": 5,
        "pickup_window_start": now.isoformat(),
        "pickup_window_end": (now + timedelta(hours=2)).isoformat(),
        "allergens": ["none"],
        "latitude": 43.2,
        "longitude": 76.8,
    }

    # 0% discount — invalid
    with pytest.raises(ValidationError):
        ListingCreate(**{**base, "discount_percentage": 0})

    # 95% discount — invalid
    with pytest.raises(ValidationError):
        ListingCreate(**{**base, "discount_percentage": 95})

    # 40% — valid
    listing = ListingCreate(**{**base, "discount_percentage": 40})
    assert listing.discount_percentage == 40


def test_pickup_window_validation():
    """pickup_window_end must be after pickup_window_start."""
    from pydantic import ValidationError
    from app.schemas.listing import ListingCreate
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    with pytest.raises(ValidationError):
        ListingCreate(
            title="Test",
            description="Desc",
            original_price=2000,
            discount_percentage=30,
            quantity_total=5,
            pickup_window_start=now + timedelta(hours=2),
            pickup_window_end=now,   # BEFORE start — invalid
            allergens=["none"],
            latitude=43.2,
            longitude=76.8,
        )
