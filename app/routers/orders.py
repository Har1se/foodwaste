from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_session
from app.core.dependencies import get_current_user, require_role
from app.core.pagination import encode_cursor, decode_cursor, CursorPage, PaginationMeta
from app.models.user import User, UserRole
from app.models.order import Order, OrderItem
from app.schemas.order import OrderCreateRequest, OrderResponse, OrderStatusUpdate, OrderItemResponse
from app.services import order_service
from app.services.email_service import async_send_order_confirmation_email

router = APIRouter(prefix="/orders", tags=["Orders"])


async def _build_order_response(order: Order, session: AsyncSession) -> OrderResponse:
    items_result = await session.execute(select(OrderItem).where(OrderItem.order_id == order.id))
    items = [
        OrderItemResponse(
            id=i.id,
            listing_id=i.listing_id,
            quantity=i.quantity,
            unit_price=i.unit_price,
        )
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


@router.post("", response_model=OrderResponse, status_code=201)
async def create_order(
    data: OrderCreateRequest,
    current_user: User = Depends(require_role(UserRole.CUSTOMER, UserRole.ADMIN)),
    session: AsyncSession = Depends(get_session),
):
    """Place an order. Atomically decrements stock using SELECT FOR UPDATE + Redis reservation."""
    order = await order_service.create_order(data, current_user, session)
    await async_send_order_confirmation_email(
        current_user.email, order.id, order.pickup_token, float(order.total_amount)
    )
    return await _build_order_response(order, session)


@router.get("", response_model=CursorPage[OrderResponse])
async def list_my_orders(
    cursor: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """List authenticated user's orders (cursor-based pagination)."""
    cursor_id = None
    if cursor:
        decoded = decode_cursor(cursor)
        cursor_id = decoded.get("id") if decoded else None

    orders, next_id = await order_service.get_user_orders(current_user.id, session, cursor_id, limit)
    responses = [await _build_order_response(o, session) for o in orders]

    return CursorPage(
        data=responses,
        pagination=PaginationMeta(
            limit=limit,
            next_cursor=encode_cursor({"id": next_id}) if next_id else None,
        ),
    )


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Order).where(Order.id == order_id))
    order = result.scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if current_user.role == UserRole.CUSTOMER and order.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return await _build_order_response(order, session)


@router.patch("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: int,
    data: OrderStatusUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    order = await order_service.update_order_status(order_id, data, current_user, session)
    return await _build_order_response(order, session)
