from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import select
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, ConfigDict

from app.database import get_session
from app.core.dependencies import require_role
from app.core.pagination import encode_cursor, decode_cursor, CursorPage, PaginationMeta
from app.models.user import User, UserRole
from app.models.vendor import Vendor
from app.models.listing import Listing, ListingStatus, ListingAllergen
from app.models.order import Order, OrderStatus, OrderItem, AuditLog
from app.models.log import SystemLog
from app.schemas.auth import UserProfileResponse, AdminUserUpdateRequest
from app.schemas.listing import ListingResponse, ListingUpdate
from app.schemas.order import OrderResponse, OrderItemResponse
from app.routers.vendors import VendorResponse
from app.services.listing_service import apply_price_decay
from app.tasks.email_tasks import send_vendor_approved_email


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


router = APIRouter(prefix="/admin", tags=["Admin"])


# ── Internal helpers ──────────────────────────────────────────────────────────

async def _get_allergens(listing_id: int, session: AsyncSession) -> List[str]:
    result = await session.execute(
        select(ListingAllergen).where(ListingAllergen.listing_id == listing_id)
    )
    return [la.allergen_code for la in result.scalars().all()]


async def _listing_response(listing: Listing, session: AsyncSession) -> ListingResponse:
    allergens = await _get_allergens(listing.id, session)
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


async def _order_response(order: Order, session: AsyncSession) -> OrderResponse:
    items_result = await session.execute(
        select(OrderItem).where(OrderItem.order_id == order.id)
    )
    items = [
        OrderItemResponse(id=i.id, listing_id=i.listing_id, quantity=i.quantity, unit_price=i.unit_price)
        for i in items_result.scalars().all()
    ]
    return OrderResponse(
        id=order.id,
        customer_id=order.customer_id,
        vendor_id=order.vendor_id,
        status=order.status,
        total_amount=order.total_amount,
        pickup_token=order.pickup_token,
        items=items,
        created_at=order.created_at,
    )


# ── Schemas ───────────────────────────────────────────────────────────────────

class VendorApprovalRequest(BaseModel):
    action: str
    reason: Optional[str] = None


class AdminStatsResponse(BaseModel):
    total_users: int
    total_vendors: int
    total_listings: int
    active_listings: int
    total_orders: int
    pending_orders: int


class SystemLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: Optional[int]
    role: Optional[str]
    endpoint: str
    method: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    request_body: Optional[str]
    response_status: int
    error_message: Optional[str]
    error_traceback: Optional[str]
    duration_ms: int
    level: str
    created_at: datetime


# ── Platform stats ────────────────────────────────────────────────────────────

@router.get("/stats", response_model=AdminStatsResponse)
async def platform_stats(
    _: User = Depends(require_role(UserRole.ADMIN)),
    session: AsyncSession = Depends(get_session),
):
    async def count(stmt):
        r = await session.execute(stmt)
        return r.scalar() or 0

    return AdminStatsResponse(
        total_users=await count(select(func.count(User.id))),
        total_vendors=await count(select(func.count(Vendor.id))),
        total_listings=await count(select(func.count(Listing.id))),
        active_listings=await count(select(func.count(Listing.id)).where(Listing.status == ListingStatus.ACTIVE)),
        total_orders=await count(select(func.count(Order.id))),
        pending_orders=await count(select(func.count(Order.id)).where(Order.status == OrderStatus.PENDING)),
    )


# ── User management ───────────────────────────────────────────────────────────

@router.get("/users", response_model=CursorPage[UserProfileResponse])
async def list_users(
    cursor: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    role: Optional[UserRole] = Query(None),
    is_active: Optional[bool] = Query(None),
    _: User = Depends(require_role(UserRole.ADMIN)),
    session: AsyncSession = Depends(get_session),
):
    """List all users with optional role/status filter and cursor pagination."""
    cursor_id = None
    if cursor:
        decoded = decode_cursor(cursor)
        cursor_id = decoded.get("id") if decoded else None

    query = select(User)
    if role is not None:
        query = query.where(User.role == role)
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    if cursor_id:
        query = query.where(User.id > cursor_id)

    query = query.order_by(User.id).limit(limit + 1)
    result = await session.execute(query)
    users = list(result.scalars().all())

    next_id = None
    if len(users) > limit:
        users = users[:limit]
        next_id = users[-1].id

    return CursorPage(
        data=[UserProfileResponse.model_validate(u) for u in users],
        pagination=PaginationMeta(
            limit=limit,
            next_cursor=encode_cursor({"id": next_id}) if next_id else None,
        ),
    )


@router.get("/users/{user_id}", response_model=UserProfileResponse)
async def get_user(
    user_id: int,
    _: User = Depends(require_role(UserRole.ADMIN)),
    session: AsyncSession = Depends(get_session),
):
    """Get a single user by ID."""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserProfileResponse.model_validate(user)


@router.patch("/users/{user_id}", response_model=UserProfileResponse)
async def update_user(
    user_id: int,
    data: AdminUserUpdateRequest,
    admin: User = Depends(require_role(UserRole.ADMIN)),
    session: AsyncSession = Depends(get_session),
):
    """Update user fields: full_name, phone, role, is_active."""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    changed: dict = {}
    if data.full_name is not None:
        user.full_name = data.full_name
        changed["full_name"] = data.full_name
    if data.phone is not None:
        existing = await session.execute(
            select(User).where(User.phone == data.phone, User.id != user_id)
        )
        if existing.scalars().first():
            raise HTTPException(status_code=409, detail="Phone number already in use")
        user.phone = data.phone
        changed["phone"] = data.phone
    if data.role is not None:
        user.role = data.role
        changed["role"] = data.role.value
    if data.is_active is not None:
        user.is_active = data.is_active
        changed["is_active"] = data.is_active

    audit = AuditLog(
        table_name="users", record_id=user.id, action="UPDATE",
        actor_id=admin.id, new_data=str(changed),
    )
    session.add(user)
    session.add(audit)
    await session.commit()
    await session.refresh(user)
    return UserProfileResponse.model_validate(user)


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: int,
    admin: User = Depends(require_role(UserRole.ADMIN)),
    session: AsyncSession = Depends(get_session),
):
    """Hard-delete a user. Blocked if user has orders (use is_active=false to deactivate instead)."""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own admin account")

    vendor_profile = await session.execute(select(Vendor).where(Vendor.user_id == user_id))
    if vendor_profile.scalars().first():
        raise HTTPException(
            status_code=409,
            detail="Cannot delete user with a vendor profile. Delete the vendor first via DELETE /admin/vendors/{id}.",
        )

    order_count = await session.execute(
        select(func.count(Order.id)).where(Order.customer_id == user_id)
    )
    if (order_count.scalar() or 0) > 0:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete user with existing orders. Use PATCH /admin/users/{id} with is_active=false to deactivate.",
        )

    audit = AuditLog(
        table_name="users", record_id=user.id, action="DELETE",
        actor_id=admin.id, new_data=str({"email": user.email}),
    )
    session.add(audit)
    await session.delete(user)
    await session.commit()


# ── Vendor management ─────────────────────────────────────────────────────────

@router.get("/vendors", response_model=List[VendorResponse])
async def list_vendors(
    is_approved: Optional[bool] = Query(None),
    _: User = Depends(require_role(UserRole.ADMIN)),
    session: AsyncSession = Depends(get_session),
):
    """List all vendors. Filter by approval status with ?is_approved=true/false."""
    query = select(Vendor)
    if is_approved is not None:
        query = query.where(Vendor.is_approved == is_approved)
    result = await session.execute(query.order_by(Vendor.id))
    return [VendorResponse.model_validate(v) for v in result.scalars().all()]


@router.patch("/vendors/{vendor_id}/approve")
async def approve_vendor(
    vendor_id: int,
    data: VendorApprovalRequest,
    admin: User = Depends(require_role(UserRole.ADMIN)),
    session: AsyncSession = Depends(get_session),
):
    """Approve or reject a vendor application."""
    result = await session.execute(select(Vendor).where(Vendor.id == vendor_id))
    vendor = result.scalars().first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    if data.action == "approve":
        vendor.is_approved = True
        vendor.approved_at = _utcnow()
    elif data.action == "reject":
        vendor.is_approved = False
    else:
        raise HTTPException(status_code=400, detail="action must be 'approve' or 'reject'")

    audit = AuditLog(
        table_name="vendors", record_id=vendor.id, action="UPDATE",
        actor_id=admin.id, new_data=str({"action": data.action, "reason": data.reason}),
    )
    session.add(vendor)
    session.add(audit)
    await session.commit()

    if data.action == "approve":
        user_result = await session.execute(select(User).where(User.id == vendor.user_id))
        vendor_user = user_result.scalars().first()
        if vendor_user:
            send_vendor_approved_email.delay(vendor_user.email, vendor.business_name)

    return {"detail": f"Vendor {data.action}d successfully"}


@router.delete("/vendors/{vendor_id}", status_code=204)
async def delete_vendor(
    vendor_id: int,
    admin: User = Depends(require_role(UserRole.ADMIN)),
    session: AsyncSession = Depends(get_session),
):
    """Hard-delete a vendor and all their listings. Blocked if active orders exist."""
    result = await session.execute(select(Vendor).where(Vendor.id == vendor_id))
    vendor = result.scalars().first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    active_orders = await session.execute(
        select(func.count(Order.id)).where(
            Order.vendor_id == vendor_id,
            Order.status.in_([OrderStatus.PENDING, OrderStatus.CONFIRMED]),
        )
    )
    if (active_orders.scalar() or 0) > 0:
        raise HTTPException(status_code=409, detail="Cannot delete vendor with active orders")

    listings_result = await session.execute(select(Listing).where(Listing.vendor_id == vendor_id))
    for listing in listings_result.scalars().all():
        allergens = await session.execute(
            select(ListingAllergen).where(ListingAllergen.listing_id == listing.id)
        )
        for la in allergens.scalars().all():
            await session.delete(la)
        await session.delete(listing)

    audit = AuditLog(
        table_name="vendors", record_id=vendor.id, action="DELETE",
        actor_id=admin.id, new_data=str({"business_name": vendor.business_name}),
    )
    session.add(audit)
    await session.delete(vendor)
    await session.commit()


# ── Listing management ────────────────────────────────────────────────────────

@router.get("/listings", response_model=CursorPage[ListingResponse])
async def list_all_listings(
    cursor: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[ListingStatus] = Query(None),
    vendor_id: Optional[int] = Query(None),
    _: User = Depends(require_role(UserRole.ADMIN)),
    session: AsyncSession = Depends(get_session),
):
    """List all listings regardless of status. Filter by status or vendor."""
    cursor_id = None
    if cursor:
        decoded = decode_cursor(cursor)
        cursor_id = decoded.get("id") if decoded else None

    query = select(Listing)
    if status is not None:
        query = query.where(Listing.status == status)
    if vendor_id is not None:
        query = query.where(Listing.vendor_id == vendor_id)
    if cursor_id:
        query = query.where(Listing.id > cursor_id)

    query = query.order_by(Listing.id).limit(limit + 1)
    result = await session.execute(query)
    listings = list(result.scalars().all())

    next_id = None
    if len(listings) > limit:
        listings = listings[:limit]
        next_id = listings[-1].id

    responses = [await _listing_response(lst, session) for lst in listings]
    return CursorPage(
        data=responses,
        pagination=PaginationMeta(
            limit=limit,
            next_cursor=encode_cursor({"id": next_id}) if next_id else None,
        ),
    )


@router.patch("/listings/{listing_id}", response_model=ListingResponse)
async def update_listing(
    listing_id: int,
    data: ListingUpdate,
    admin: User = Depends(require_role(UserRole.ADMIN)),
    session: AsyncSession = Depends(get_session),
):
    """Update any listing field (title, status, quantity, pickup window, allergens)."""
    result = await session.execute(select(Listing).where(Listing.id == listing_id))
    listing = result.scalars().first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    changed: dict = {}
    if data.title is not None:
        listing.title = data.title
        changed["title"] = data.title
    if data.description is not None:
        listing.description = data.description
    if data.status is not None:
        listing.status = data.status
        changed["status"] = data.status.value
    if data.quantity_total is not None:
        listing.quantity_total = data.quantity_total
        listing.quantity_available = data.quantity_total  # full restock when admin sets new total
        changed["quantity_total"] = data.quantity_total
    if data.pickup_window_start is not None:
        listing.pickup_window_start = data.pickup_window_start
    if data.pickup_window_end is not None:
        listing.pickup_window_end = data.pickup_window_end
    if data.allergens is not None:
        existing_allergens = await session.execute(
            select(ListingAllergen).where(ListingAllergen.listing_id == listing_id)
        )
        for la in existing_allergens.scalars().all():
            await session.delete(la)
        for allergen_code in data.allergens:
            session.add(ListingAllergen(listing_id=listing_id, allergen_code=allergen_code.value))
        changed["allergens"] = [a.value for a in data.allergens]

    audit = AuditLog(
        table_name="listings", record_id=listing.id, action="UPDATE",
        actor_id=admin.id, new_data=str(changed),
    )
    session.add(listing)
    session.add(audit)
    await session.commit()
    await session.refresh(listing)
    return await _listing_response(listing, session)


@router.delete("/listings/{listing_id}", status_code=204)
async def delete_listing(
    listing_id: int,
    admin: User = Depends(require_role(UserRole.ADMIN)),
    session: AsyncSession = Depends(get_session),
):
    """Hard-delete a listing. Blocked if it has order items (use status=compost instead)."""
    result = await session.execute(select(Listing).where(Listing.id == listing_id))
    listing = result.scalars().first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    item_count = await session.execute(
        select(func.count(OrderItem.id)).where(OrderItem.listing_id == listing_id)
    )
    if (item_count.scalar() or 0) > 0:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete listing with existing orders. Use PATCH /admin/listings/{id} with status=compost instead.",
        )

    allergens = await session.execute(
        select(ListingAllergen).where(ListingAllergen.listing_id == listing_id)
    )
    for la in allergens.scalars().all():
        await session.delete(la)

    audit = AuditLog(
        table_name="listings", record_id=listing.id, action="DELETE",
        actor_id=admin.id, new_data=str({"title": listing.title}),
    )
    session.add(audit)
    await session.delete(listing)
    await session.commit()


# ── Order management ──────────────────────────────────────────────────────────

@router.get("/orders", response_model=CursorPage[OrderResponse])
async def list_all_orders(
    cursor: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[OrderStatus] = Query(None),
    vendor_id: Optional[int] = Query(None),
    customer_id: Optional[int] = Query(None),
    _: User = Depends(require_role(UserRole.ADMIN)),
    session: AsyncSession = Depends(get_session),
):
    """List all orders across all vendors. Filter by status, vendor or customer."""
    cursor_id = None
    if cursor:
        decoded = decode_cursor(cursor)
        cursor_id = decoded.get("id") if decoded else None

    query = select(Order)
    if status is not None:
        query = query.where(Order.status == status)
    if vendor_id is not None:
        query = query.where(Order.vendor_id == vendor_id)
    if customer_id is not None:
        query = query.where(Order.customer_id == customer_id)
    if cursor_id:
        query = query.where(Order.id > cursor_id)

    query = query.order_by(Order.id).limit(limit + 1)
    result = await session.execute(query)
    orders = list(result.scalars().all())

    next_id = None
    if len(orders) > limit:
        orders = orders[:limit]
        next_id = orders[-1].id

    responses = [await _order_response(o, session) for o in orders]
    return CursorPage(
        data=responses,
        pagination=PaginationMeta(
            limit=limit,
            next_cursor=encode_cursor({"id": next_id}) if next_id else None,
        ),
    )


@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    _: User = Depends(require_role(UserRole.ADMIN)),
    session: AsyncSession = Depends(get_session),
):
    """Get a single order by ID with full item details."""
    result = await session.execute(select(Order).where(Order.id == order_id))
    order = result.scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return await _order_response(order, session)


# ── User suspend (legacy, kept for compatibility) ─────────────────────────────

@router.patch("/users/{user_id}/suspend")
async def suspend_user(
    user_id: int,
    is_active: bool,
    admin: User = Depends(require_role(UserRole.ADMIN)),
    session: AsyncSession = Depends(get_session),
):
    """Quick suspend/activate toggle. Use PATCH /admin/users/{id} for full updates."""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = is_active
    audit = AuditLog(
        table_name="users", record_id=user.id, action="UPDATE",
        actor_id=admin.id, new_data=str({"is_active": is_active}),
    )
    session.add(user)
    session.add(audit)
    await session.commit()
    return {"detail": f"User {'activated' if is_active else 'suspended'} successfully"}


# ── Price decay trigger ───────────────────────────────────────────────────────

@router.post("/trigger-price-decay")
async def trigger_price_decay(
    _: User = Depends(require_role(UserRole.ADMIN)),
    session: AsyncSession = Depends(get_session),
):
    """Manually trigger the price decay state machine (normally runs via Celery)."""
    updated = await apply_price_decay(session)
    return {"detail": f"Price decay applied to {updated} listings"}


# ── System logs ───────────────────────────────────────────────────────────────

@router.get("/logs", response_model=CursorPage[SystemLogResponse])
async def get_system_logs(
    cursor: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    endpoint: Optional[str] = Query(None, description="Filter by endpoint (partial match)"),
    level: Optional[str] = Query(None, description="Filter by level: info | warning | error"),
    date_from: Optional[datetime] = Query(None, description="ISO datetime lower bound"),
    date_to: Optional[datetime] = Query(None, description="ISO datetime upper bound"),
    _: User = Depends(require_role(UserRole.ADMIN)),
    session: AsyncSession = Depends(get_session),
):
    """
    List system request logs with filtering. Results are newest-first (cursor paginates backwards).
    Use for debugging, audit, and monitoring.
    """
    cursor_id: Optional[int] = None
    if cursor:
        decoded = decode_cursor(cursor)
        cursor_id = decoded.get("id") if decoded else None

    query = select(SystemLog)
    if user_id is not None:
        query = query.where(SystemLog.user_id == user_id)
    if endpoint:
        query = query.where(SystemLog.endpoint.contains(endpoint))
    if level in ("info", "warning", "error"):
        query = query.where(SystemLog.level == level)
    if date_from is not None:
        query = query.where(SystemLog.created_at >= date_from)
    if date_to is not None:
        query = query.where(SystemLog.created_at <= date_to)
    if cursor_id is not None:
        query = query.where(SystemLog.id < cursor_id)

    query = query.order_by(SystemLog.id.desc()).limit(limit + 1)
    result = await session.execute(query)
    logs = list(result.scalars().all())

    next_id: Optional[int] = None
    if len(logs) > limit:
        logs = logs[:limit]
        next_id = logs[-1].id

    return CursorPage(
        data=[SystemLogResponse.model_validate(lg) for lg in logs],
        pagination=PaginationMeta(
            limit=limit,
            next_cursor=encode_cursor({"id": next_id}) if next_id else None,
        ),
    )


# ── Demo seed reset ───────────────────────────────────────────────────────────

@router.post("/seed-reset")
async def seed_reset(
    admin: User = Depends(require_role(UserRole.ADMIN)),
    session: AsyncSession = Depends(get_session),
):
    """
    Delete all listings owned by the demo vendor and re-seed fresh demo data.
    Safe to call multiple times — always results in a clean dataset.
    """
    from app.demo_seed import auto_seed
    from app.models.vendor import Vendor as VendorModel

    result = await session.execute(select(User).where(User.email == "vendor@test.kz"))
    vendor_user = result.scalars().first()

    if vendor_user:
        vr = await session.execute(select(VendorModel).where(VendorModel.user_id == vendor_user.id))
        vendor = vr.scalars().first()
        if vendor:
            all_listings = await session.execute(
                select(Listing).where(Listing.vendor_id == vendor.id)
            )
            listing_ids = [lst.id for lst in all_listings.scalars().all()]
            for lid in listing_ids:
                # remove order items referencing this listing
                ois = await session.execute(select(OrderItem).where(OrderItem.listing_id == lid))
                for oi in ois.scalars().all():
                    await session.delete(oi)
                # remove allergens
                als = await session.execute(select(ListingAllergen).where(ListingAllergen.listing_id == lid))
                for al in als.scalars().all():
                    await session.delete(al)
            await session.flush()
            for lid in listing_ids:
                lst_r = await session.execute(select(Listing).where(Listing.id == lid))
                lst = lst_r.scalars().first()
                if lst:
                    await session.delete(lst)
            await session.flush()

    n = await auto_seed(session)

    audit = AuditLog(
        table_name="listings", record_id=0, action="SEED_RESET",
        actor_id=admin.id, new_data=str({"seeded": n}),
    )
    session.add(audit)
    await session.commit()
    return {"detail": f"Seed reset complete — {n} demo listings created"}
