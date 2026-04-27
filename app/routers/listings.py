from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_session
from app.core.dependencies import get_current_user, require_role
from app.core.pagination import encode_cursor, decode_cursor, CursorPage, PaginationMeta
from app.models.user import User, UserRole
from app.models.vendor import Vendor
from app.models.listing import Listing, ListingAllergen, AllergenCode
from app.schemas.listing import (
    ListingCreate, ListingUpdate, ListingResponse,
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
        days_active=listing.days_active,
        created_at=listing.created_at,
    )


async def _fetch_allergens(listing_id: int, session: AsyncSession) -> List[str]:
    result = await session.execute(
        select(ListingAllergen).where(ListingAllergen.listing_id == listing_id)
    )
    return [la.allergen_code for la in result.scalars().all()]


@router.get("", response_model=CursorPage[ListingResponse])
async def list_listings(
    cursor: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    lat: Optional[float] = Query(None),
    lng: Optional[float] = Query(None),
    session: AsyncSession = Depends(get_session),
):
    """Browse active listings. Supports cursor-based pagination and geo-filter."""
    cursor_id = None
    if cursor:
        decoded = decode_cursor(cursor)
        cursor_id = decoded.get("id") if decoded else None

    listings, next_id = await listing_service.get_listings(
        session, lat=lat, lng=lng, cursor_id=cursor_id, limit=limit
    )

    responses = []
    for listing in listings:
        allergens = await _fetch_allergens(listing.id, session)
        responses.append(_listing_to_response(listing, allergens))

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
    return _listing_to_response(listing, allergens)


@router.get("/{listing_id}", response_model=ListingResponse)
async def get_listing(listing_id: int, session: AsyncSession = Depends(get_session)):
    """Get a single listing by ID."""
    result = await session.execute(select(Listing).where(Listing.id == listing_id))
    listing = result.scalars().first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    allergens = await _fetch_allergens(listing.id, session)
    return _listing_to_response(listing, allergens)


@router.post("/allergen-check", response_model=AllergenFilterResponse)
async def check_allergens(
    data: AllergenFilterRequest,
    _: User = Depends(get_current_user),
):
    """
    RESCUEBITE CORE: Allergen parser.
    Submit ingredient list + allergen profile → get safe/unsafe result.
    """
    return await listing_service.parse_allergens(data)
