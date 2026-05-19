import math
from datetime import datetime, timezone
from typing import List, Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import text
from fastapi import HTTPException

from app.models.listing import Listing, ListingAllergen, ListingStatus, AllergenCode
from app.models.vendor import Vendor
from app.schemas.listing import ListingCreate, AllergenFilterRequest, AllergenFilterResponse


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# Ingredient → allergen keyword mapping
ALLERGEN_KEYWORDS: dict[AllergenCode, list[str]] = {
    AllergenCode.GLUTEN: ["wheat", "flour", "bread", "gluten", "barley", "rye", "oats", "пшеница", "мука"],
    AllergenCode.DAIRY: ["milk", "cheese", "butter", "cream", "yogurt", "lactose", "молоко", "сыр", "сливки"],
    AllergenCode.EGGS: ["egg", "яйцо", "яйца"],
    AllergenCode.NUTS: ["almond", "walnut", "cashew", "peanut", "nut", "орех", "миндаль"],
    AllergenCode.SOY: ["soy", "tofu", "edamame", "соя"],
    AllergenCode.FISH: ["fish", "salmon", "tuna", "cod", "рыба", "лосось"],
    AllergenCode.SHELLFISH: ["shrimp", "crab", "lobster", "prawn", "креветка", "краб"],
    AllergenCode.SESAME: ["sesame", "tahini", "кунжут"],
}


async def parse_allergens(data: AllergenFilterRequest) -> AllergenFilterResponse:
    """
    RESCUEBITE CORE: Accept ingredient JSON, validate against user allergen profile.
    Returns safe=False if any ingredient matches a user's allergen.
    """
    detected: set[AllergenCode] = set()
    flagged_ingredients: list[str] = []

    for ingredient in data.ingredients:
        ingredient_lower = ingredient.lower()
        for allergen_code, keywords in ALLERGEN_KEYWORDS.items():
            if any(kw in ingredient_lower for kw in keywords):
                detected.add(allergen_code)
                if allergen_code in data.user_allergens:
                    flagged_ingredients.append(ingredient)

    # Cross-check with user profile
    user_allergen_set = set(data.user_allergens)
    conflicts = detected & user_allergen_set

    safe = len(conflicts) == 0
    message = (
        "No allergen conflicts detected."
        if safe
        else f"WARNING: Contains allergens matching your profile: {[a.value for a in conflicts]}"
    )

    return AllergenFilterResponse(
        safe=safe,
        detected_allergens=list(detected),
        flagged_ingredients=flagged_ingredients,
        message=message,
    )


async def create_listing(data: ListingCreate, vendor: Vendor, session: AsyncSession) -> Listing:
    # Calculate current price from discount
    current_price = int(data.original_price * (1 - data.discount_percentage / 100))
    current_price = max(current_price, 500)  # floor 500 KZT

    listing = Listing(
        vendor_id=vendor.id,
        title=data.title,
        description=data.description,
        original_price=data.original_price,
        current_price=current_price,
        discount_percentage=data.discount_percentage,
        quantity_total=data.quantity_total,
        quantity_available=data.quantity_total,
        status=ListingStatus.ACTIVE,
        pickup_window_start=data.pickup_window_start,
        pickup_window_end=data.pickup_window_end,
        latitude=data.latitude,
        longitude=data.longitude,
        photo_url=data.photo_url,
    )
    session.add(listing)
    await session.flush()  # get listing.id

    # Add allergens (M:N)
    for allergen_code in data.allergens:
        la = ListingAllergen(listing_id=listing.id, allergen_code=allergen_code.value)
        session.add(la)

    await session.commit()
    await session.refresh(listing)
    return listing


async def get_listings(
    session: AsyncSession,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    cursor_id: Optional[int] = None,
    limit: int = 20,
) -> tuple[List[Listing], Optional[int]]:
    """Cursor-based listing search with optional geo-filter.

    When a geo-filter is active the query fetches a larger batch so that
    enough in-range results survive the client-side distance check.  This
    avoids the pagination bug where filtering after a limit+1 fetch could
    return fewer than `limit` rows even though more in-range rows exist.
    """
    geo_active = lat is not None and lng is not None
    # Fetch extra rows when geo-filtering to compensate for items outside range
    fetch_limit = (limit + 1) * 8 if geo_active else (limit + 1)

    query = select(Listing).where(
        Listing.status.in_([ListingStatus.ACTIVE, ListingStatus.DISCOUNTED, ListingStatus.FREE]),
        Listing.quantity_available > 0,
        Listing.pickup_window_end > _utcnow(),
    )

    if cursor_id:
        query = query.where(Listing.id > cursor_id)

    query = query.order_by(Listing.id).limit(fetch_limit)
    result = await session.execute(query)
    listings = list(result.scalars().all())

    if geo_active:
        listings = [
            lst for lst in listings
            if _haversine(lat, lng, lst.latitude, lst.longitude) <= 10
        ]

    next_cursor = None
    if len(listings) > limit:
        listings = listings[:limit]
        next_cursor = listings[-1].id

    return listings, next_cursor


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance in km between two lat/lng points."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


# ── Price Decay State Machine ──────────────────────────────────────────────────
# Fresh → Discounted (days_active >= 30, 10% decay every 72h)
# Discounted → Free (price hits floor 0)
# Free → Compost (pickup_window_end passed)

async def apply_price_decay(session: AsyncSession) -> int:
    """
    RESCUEBITE CORE: Food item state machine with time-based transitions.
    Called by Celery Beat every 72 hours.
    Returns number of listings updated.
    """
    now = _utcnow()
    result = await session.execute(
        select(Listing).where(
            Listing.status.in_([ListingStatus.ACTIVE, ListingStatus.DISCOUNTED]),
            Listing.days_active >= 30,
            Listing.pickup_window_end > now,
        )
    )
    listings = list(result.scalars().all())
    updated = 0

    for listing in listings:
        new_price = max(int(listing.current_price * 0.90), 0)
        listing.current_price = new_price
        listing.days_active += 3

        # State transitions — order matters: FREE check first, no elif
        if new_price == 0:
            listing.status = ListingStatus.FREE
        elif listing.status == ListingStatus.ACTIVE:
            listing.status = ListingStatus.DISCOUNTED
        # DISCOUNTED stays DISCOUNTED until price hits 0

        session.add(listing)
        updated += 1

    # Expire listings past pickup window
    expired_result = await session.execute(
        select(Listing).where(
            Listing.status.in_([ListingStatus.ACTIVE, ListingStatus.DISCOUNTED, ListingStatus.FREE]),
            Listing.pickup_window_end <= now,
        )
    )
    for listing in expired_result.scalars().all():
        listing.status = ListingStatus.COMPOST
        session.add(listing)
        updated += 1

    await session.commit()
    return updated
