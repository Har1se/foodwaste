from typing import Optional, List

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_session
from app.core.dependencies import get_current_user, require_role
from app.core.pagination import encode_cursor, decode_cursor, CursorPage, PaginationMeta
from app.models.user import User, UserRole
from app.models.vendor import Vendor
from app.models.listing import Listing, ListingAllergen, ListingStatus
from app.models.order import OrderItem
from app.schemas.listing import (
    ListingCreate, ListingResponse, ListingUpdate,
    AllergenFilterRequest, AllergenFilterResponse,
)
from app.services import listing_service

router = APIRouter(prefix="/listings", tags=["Listings"])


def _listing_to_response(listing: Listing, allergens: List[str]) -> ListingResponse:
    return ListingResponse(
        id=listing.id,
        vendor_id=listing.vendor_id,
        title=listing.title,
        description=listing.description,
        original_price=listing.original_price,
        current_price=listing.current_price,
        discount_percentage=listing.discount_percentage,
        quantity_total=listing.quantity_total,
        quantity_available=listing.quantity_available,
        status=listing.status,
        pickup_window_start=listing.pickup_window_start,
        pickup_window_end=listing.pickup_window_end,
        allergens=allergens,
        latitude=listing.latitude,
        longitude=listing.longitude,
        photo_url=listing.photo_url,
        category=listing.category,
        days_active=listing.days_active,
        created_at=listing.created_at,
    )


async def _fetch_allergens(listing_id: int, session: AsyncSession) -> List[str]:
    result = await session.execute(
        select(ListingAllergen).where(ListingAllergen.listing_id == listing_id)
    )
    return [la.allergen_code for la in result.scalars().all()]


async def _fetch_allergens_batch(
    listing_ids: List[int], session: AsyncSession
) -> dict[int, List[str]]:
    """Single query for all allergens of a batch of listings (avoids N+1)."""
    if not listing_ids:
        return {}
    result = await session.execute(
        select(ListingAllergen).where(ListingAllergen.listing_id.in_(listing_ids))
    )
    mapping: dict[int, List[str]] = {lid: [] for lid in listing_ids}
    for la in result.scalars().all():
        mapping[la.listing_id].append(la.allergen_code)
    return mapping


# ── Collection endpoints (no path param) ─────────────────────────────────────

@router.get("", response_model=CursorPage[ListingResponse])
async def list_listings(
    cursor: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    lat: Optional[float] = Query(None),
    lng: Optional[float] = Query(None),
    category: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session),
):
    """Browse active listings. Supports cursor-based pagination, geo-filter, and category filter."""
    cursor_id = None
    if cursor:
        decoded = decode_cursor(cursor)
        cursor_id = decoded.get("id") if decoded else None

    listings, next_id = await listing_service.get_listings(
        session, lat=lat, lng=lng, cursor_id=cursor_id, limit=limit, category=category
    )

    # Batch load all allergens in a single query instead of N queries
    allergens_map = await _fetch_allergens_batch([lst.id for lst in listings], session)
    responses = [
        _listing_to_response(lst, allergens_map.get(lst.id, []))
        for lst in listings
    ]

    return CursorPage(
        data=responses,
        pagination=PaginationMeta(
            limit=limit,
            next_cursor=encode_cursor({"id": next_id}) if next_id else None,
        ),
    )


@router.post("", response_model=ListingResponse, status_code=201)
async def create_listing(
    data: ListingCreate,
    current_user: User = Depends(require_role(UserRole.VENDOR, UserRole.ADMIN)),
    session: AsyncSession = Depends(get_session),
):
    """Create a new food listing (vendor only)."""
    result = await session.execute(select(Vendor).where(Vendor.user_id == current_user.id))
    vendor = result.scalars().first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor profile not found.")
    if not vendor.is_approved:
        raise HTTPException(status_code=403, detail="Vendor account is pending approval.")

    listing = await listing_service.create_listing(data, vendor, session)
    allergens = await _fetch_allergens(listing.id, session)

    # Notify all verified customers (shelters) about the new listing
    from app.models.user import UserRole as _UserRole
    from app.tasks.email_tasks import send_new_listing_email
    customers_r = await session.execute(
        select(User).where(
            User.role == _UserRole.CUSTOMER,
            User.email_verified.is_(True),
            User.is_active.is_(True),
        ).limit(200)
    )
    for customer in customers_r.scalars().all():
        send_new_listing_email.delay(
            customer.email,
            listing.title,
            listing.current_price,
            vendor.business_name,
            listing.category,
        )

    return _listing_to_response(listing, allergens)


# ── Static sub-routes BEFORE /{listing_id} ────────────────────────────────────

@router.post("/allergen-check", response_model=AllergenFilterResponse)
async def check_allergens(
    data: AllergenFilterRequest,
    _: User = Depends(get_current_user),
):
    """Allergen parser: submit ingredient list + allergen profile → safe/unsafe result."""
    return await listing_service.parse_allergens(data)


@router.get("/vendor/my-listings", response_model=CursorPage[ListingResponse])
async def get_my_listings(
    cursor: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[ListingStatus] = Query(None),
    current_user: User = Depends(require_role(UserRole.VENDOR, UserRole.ADMIN)),
    session: AsyncSession = Depends(get_session),
):
    """Get all listings for the authenticated vendor (vendor dashboard)."""
    vendor_result = await session.execute(select(Vendor).where(Vendor.user_id == current_user.id))
    vendor = vendor_result.scalars().first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor profile not found")

    cursor_id = None
    if cursor:
        decoded = decode_cursor(cursor)
        cursor_id = decoded.get("id") if decoded else None

    query = select(Listing).where(Listing.vendor_id == vendor.id)
    if status is not None:
        query = query.where(Listing.status == status)
    if cursor_id:
        query = query.where(Listing.id > cursor_id)
    query = query.order_by(Listing.id).limit(limit + 1)

    result = await session.execute(query)
    listings = list(result.scalars().all())

    next_id = None
    if len(listings) > limit:
        listings = listings[:limit]
        next_id = listings[-1].id

    allergens_map = await _fetch_allergens_batch([lst.id for lst in listings], session)
    responses = [
        _listing_to_response(lst, allergens_map.get(lst.id, []))
        for lst in listings
    ]

    return CursorPage(
        data=responses,
        pagination=PaginationMeta(
            limit=limit,
            next_cursor=encode_cursor({"id": next_id}) if next_id else None,
        ),
    )


# ── Dynamic /{listing_id} routes ──────────────────────────────────────────────

@router.get("/{listing_id}", response_model=ListingResponse)
async def get_listing(listing_id: int, session: AsyncSession = Depends(get_session)):
    """Get a single listing by ID."""
    result = await session.execute(select(Listing).where(Listing.id == listing_id))
    listing = result.scalars().first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    allergens = await _fetch_allergens(listing.id, session)
    return _listing_to_response(listing, allergens)


@router.patch("/{listing_id}", response_model=ListingResponse)
async def update_listing(
    listing_id: int,
    data: ListingUpdate,
    current_user: User = Depends(require_role(UserRole.VENDOR, UserRole.ADMIN)),
    session: AsyncSession = Depends(get_session),
):
    """Update own listing. Vendors can only update listings they own."""
    result = await session.execute(select(Listing).where(Listing.id == listing_id))
    listing = result.scalars().first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    if current_user.role == UserRole.VENDOR:
        vendor_result = await session.execute(select(Vendor).where(Vendor.user_id == current_user.id))
        vendor = vendor_result.scalars().first()
        if not vendor or listing.vendor_id != vendor.id:
            raise HTTPException(status_code=403, detail="You can only update your own listings")

    if data.title is not None:
        listing.title = data.title
    if data.description is not None:
        listing.description = data.description
    if data.quantity_total is not None:
        listing.quantity_total = data.quantity_total
        listing.quantity_available = min(listing.quantity_available, data.quantity_total)
    if data.pickup_window_start is not None:
        listing.pickup_window_start = data.pickup_window_start
    if data.pickup_window_end is not None:
        listing.pickup_window_end = data.pickup_window_end
    if data.status is not None:
        listing.status = data.status
    if data.category is not None:
        listing.category = data.category
    if data.allergens is not None:
        existing = await session.execute(
            select(ListingAllergen).where(ListingAllergen.listing_id == listing_id)
        )
        for la in existing.scalars().all():
            await session.delete(la)
        for allergen_code in data.allergens:
            session.add(ListingAllergen(listing_id=listing_id, allergen_code=allergen_code.value))

    session.add(listing)
    await session.commit()
    await session.refresh(listing)
    allergens = await _fetch_allergens(listing.id, session)
    return _listing_to_response(listing, allergens)


@router.delete("/{listing_id}", status_code=204)
async def delete_listing(
    listing_id: int,
    current_user: User = Depends(require_role(UserRole.VENDOR, UserRole.ADMIN)),
    session: AsyncSession = Depends(get_session),
):
    """Delete own listing. Blocked if listing has existing order items."""
    result = await session.execute(select(Listing).where(Listing.id == listing_id))
    listing = result.scalars().first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    if current_user.role == UserRole.VENDOR:
        vendor_result = await session.execute(select(Vendor).where(Vendor.user_id == current_user.id))
        vendor = vendor_result.scalars().first()
        if not vendor or listing.vendor_id != vendor.id:
            raise HTTPException(status_code=403, detail="You can only delete your own listings")

    item_count = await session.execute(
        select(func.count(OrderItem.id)).where(OrderItem.listing_id == listing_id)
    )
    if (item_count.scalar() or 0) > 0:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete listing with existing orders. Set status to 'paused' or 'compost' instead.",
        )

    allergens_result = await session.execute(
        select(ListingAllergen).where(ListingAllergen.listing_id == listing_id)
    )
    for la in allergens_result.scalars().all():
        await session.delete(la)
    await session.delete(listing)
    await session.commit()
