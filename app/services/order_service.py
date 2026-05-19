import secrets
from datetime import datetime, timezone
from typing import List, Optional

from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from fastapi import HTTPException

from app.models.order import Order, OrderItem, OrderStatus, AuditLog
from app.models.listing import Listing, ListingStatus
from app.models.user import User, UserRole
from app.models.vendor import Vendor
from app.schemas.order import OrderCreateRequest, OrderStatusUpdate
from app.core.redis import reserve_stock, release_stock_reservation


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def _lock_listing_row(listing_id: int, session: AsyncSession):
    """SELECT FOR UPDATE — only supported on PostgreSQL. SQLite silently skips."""
    try:
        await session.execute(
            text("SELECT id FROM listings WHERE id = :id FOR UPDATE").bindparams(id=listing_id)
        )
    except Exception:
        pass  # SQLite in tests doesn't support FOR UPDATE — OK, PostgreSQL in prod does


async def create_order(
    data: OrderCreateRequest,
    customer: User,
    session: AsyncSession,
) -> Order:
    """
    RESCUEBITE CORE: Atomic order creation — two-layer oversell prevention.

    Layer 1 — Redis soft lock (reserve_stock): increments a counter per listing with
    TTL=300s. Prevents parallel checkouts from over-committing stock before DB write.

    Layer 2 — PostgreSQL SELECT FOR UPDATE (hard lock): re-checks stock inside the
    DB transaction and atomically decrements quantity_available. Guarantees consistency
    even under concurrent load.
    """
    if not data.items:
        raise HTTPException(status_code=400, detail="Order must have at least one item")

    # ── Layer 1: Redis soft reservation ───────────────────────────────────────
    redis_reserved = []
    try:
        for item_req in data.items:
            await reserve_stock(item_req.listing_id, item_req.quantity, ttl_seconds=300)
            redis_reserved.append((item_req.listing_id, item_req.quantity))
    except Exception:
        for lid, qty in redis_reserved:
            await release_stock_reservation(lid, qty)
        raise HTTPException(status_code=503, detail="Stock reservation unavailable, please retry")

    # ── Layer 2: DB validation + SELECT FOR UPDATE ─────────────────────────────
    try:
        total_amount = 0
        vendor_id = None
        order_items_data = []

        for item_req in data.items:
            result = await session.execute(select(Listing).where(Listing.id == item_req.listing_id))
            listing = result.scalars().first()

            if not listing:
                raise HTTPException(status_code=404, detail=f"Listing {item_req.listing_id} not found")
            if listing.status not in [ListingStatus.ACTIVE, ListingStatus.DISCOUNTED, ListingStatus.FREE]:
                raise HTTPException(status_code=409, detail=f"Listing {item_req.listing_id} is not available")
            if listing.quantity_available < item_req.quantity:
                raise HTTPException(
                    status_code=409,
                    detail=f"Insufficient stock for listing {item_req.listing_id}. "
                           f"Available: {listing.quantity_available}, requested: {item_req.quantity}",
                )
            if vendor_id is None:
                vendor_id = listing.vendor_id
            elif vendor_id != listing.vendor_id:
                raise HTTPException(status_code=400, detail="All items must be from the same vendor")

            order_items_data.append((listing, item_req.quantity))
            total_amount += listing.current_price * item_req.quantity

        # Lock rows + atomic decrement
        for listing, quantity in order_items_data:
            await _lock_listing_row(listing.id, session)
            # Re-fetch after lock to get latest state
            result = await session.execute(select(Listing).where(Listing.id == listing.id))
            locked = result.scalars().first()
            if locked.quantity_available < quantity:
                raise HTTPException(
                    status_code=409,
                    detail=f"Stock changed for listing {listing.id} during checkout. Please retry."
                )
            locked.quantity_available -= quantity
            if locked.quantity_available == 0:
                locked.status = ListingStatus.SOLD_OUT
            session.add(locked)

        order = Order(
            customer_id=customer.id,
            vendor_id=vendor_id,
            status=OrderStatus.PENDING,
            total_amount=total_amount,
            pickup_token=secrets.token_hex(32),
        )
        session.add(order)
        await session.flush()

        for listing, quantity in order_items_data:
            item = OrderItem(
                order_id=order.id,
                listing_id=listing.id,
                quantity=quantity,
                unit_price=listing.current_price,
            )
            session.add(item)

        audit = AuditLog(
            table_name="orders",
            record_id=order.id,
            action="INSERT",
            actor_id=customer.id,
            new_data=str({"customer_id": customer.id, "total": total_amount}),
        )
        session.add(audit)
        await session.commit()
        await session.refresh(order)
        return order

    except HTTPException:
        for lid, qty in redis_reserved:
            await release_stock_reservation(lid, qty)
        raise
    except Exception:
        for lid, qty in redis_reserved:
            await release_stock_reservation(lid, qty)
        raise


# Valid status transitions: from_status → [allowed to_statuses]
_ALLOWED_TRANSITIONS: dict[OrderStatus, list[OrderStatus]] = {
    OrderStatus.PENDING:          [OrderStatus.CONFIRMED, OrderStatus.CANCELLED],
    OrderStatus.CONFIRMED:        [OrderStatus.READY_FOR_PICKUP, OrderStatus.CANCELLED],
    OrderStatus.READY_FOR_PICKUP: [OrderStatus.PICKED_UP],
    OrderStatus.PICKED_UP:        [],
    OrderStatus.CANCELLED:        [],
}


async def update_order_status(
    order_id: int,
    data: OrderStatusUpdate,
    actor: User,
    session: AsyncSession,
) -> Order:
    result = await session.execute(select(Order).where(Order.id == order_id))
    order = result.scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # ── Authorization ─────────────────────────────────────────────────────────
    if actor.role == UserRole.VENDOR:
        vresult = await session.execute(select(Vendor).where(Vendor.user_id == actor.id))
        vendor = vresult.scalars().first()
        if not vendor or order.vendor_id != vendor.id:
            raise HTTPException(status_code=403, detail="Not your order")
    elif actor.role == UserRole.CUSTOMER:
        if order.customer_id != actor.id:
            raise HTTPException(status_code=403, detail="Not your order")
        if data.status != OrderStatus.CANCELLED:
            raise HTTPException(status_code=403, detail="Customers can only cancel orders")

    # ── Validate transition ────────────────────────────────────────────────────
    allowed = _ALLOWED_TRANSITIONS.get(order.status, [])
    if data.status not in allowed:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot transition order from '{order.status.value}' to '{data.status.value}'. "
                   f"Allowed: {[s.value for s in allowed] or 'none'}",
        )

    old_status = order.status
    order.status = data.status
    order.updated_at = _utcnow()

    if data.status == OrderStatus.CANCELLED:
        now_ts = _utcnow()
        items_result = await session.execute(select(OrderItem).where(OrderItem.order_id == order.id))
        for item in items_result.scalars().all():
            lresult = await session.execute(select(Listing).where(Listing.id == item.listing_id))
            listing = lresult.scalars().first()
            if listing:
                listing.quantity_available += item.quantity
                # Only restore status if listing was sold-out AND still within pickup window
                # Never restore COMPOST/FREE/DISCOUNTED listings back to ACTIVE
                if listing.status == ListingStatus.SOLD_OUT and listing.pickup_window_end > now_ts:
                    listing.status = ListingStatus.ACTIVE
                session.add(listing)

    audit = AuditLog(
        table_name="orders",
        record_id=order.id,
        action="UPDATE",
        actor_id=actor.id,
        old_data=str({"status": old_status.value}),
        new_data=str({"status": data.status.value}),
    )
    session.add(audit)
    session.add(order)
    await session.commit()
    await session.refresh(order)
    return order


async def get_user_orders(
    customer_id: int,
    session: AsyncSession,
    cursor_id: Optional[int] = None,
    limit: int = 20,
) -> tuple[List[Order], Optional[int]]:
    query = select(Order).where(Order.customer_id == customer_id)
    if cursor_id:
        query = query.where(Order.id < cursor_id)
    query = query.order_by(Order.id.desc()).limit(limit + 1)
    result = await session.execute(query)
    orders = list(result.scalars().all())
    next_cursor = None
    if len(orders) > limit:
        orders = orders[:limit]
        next_cursor = orders[-1].id
    return orders, next_cursor
