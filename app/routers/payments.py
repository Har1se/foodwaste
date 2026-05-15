import secrets
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.core.dependencies import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.order import Order, OrderStatus, Payment, PaymentStatus, AuditLog

router = APIRouter(prefix="/payments", tags=["Payments"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class PaymentInitResponse(BaseModel):
    order_id: int
    amount_kzt: int
    kaspi_payment_url: str
    payment_id: int
    status: str


class PaymentStatusResponse(BaseModel):
    payment_id: int
    order_id: int
    amount_kzt: int
    status: str
    kaspi_ref_id: Optional[str]
    paid_at: Optional[datetime]


class KaspiWebhookPayload(BaseModel):
    order_id: int
    amount: int
    reference_id: str
    status: str    # "SUCCESS" | "FAILED"
    signature: str


@router.post("/{order_id}/initiate", response_model=PaymentInitResponse)
async def initiate_payment(
    order_id: int,
    current_user: User = Depends(require_role(UserRole.CUSTOMER, UserRole.ADMIN)),
    session: AsyncSession = Depends(get_session),
):
    """Initiate a Kaspi Pay payment for an order. Returns payment URL for redirect."""
    result = await session.execute(select(Order).where(Order.id == order_id))
    order = result.scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if current_user.role == UserRole.CUSTOMER and order.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if order.status not in (OrderStatus.PENDING, OrderStatus.CONFIRMED):
        raise HTTPException(status_code=409, detail="Order is not in a payable state")

    existing = await session.execute(select(Payment).where(Payment.order_id == order_id))
    payment = existing.scalars().first()
    if payment and payment.status == PaymentStatus.COMPLETED:
        raise HTTPException(status_code=409, detail="Order already paid")

    if not payment:
        payment = Payment(order_id=order.id, amount_kzt=order.total_amount)
        session.add(payment)
        await session.commit()
        await session.refresh(payment)

    kaspi_url = f"https://pay.kaspi.kz/pay?order_id={order.id}&amount={order.total_amount}&merchant=rescuebite"
    return PaymentInitResponse(
        order_id=order.id,
        amount_kzt=order.total_amount,
        kaspi_payment_url=kaspi_url,
        payment_id=payment.id,
        status=payment.status.value,
    )


@router.post("/{order_id}/simulate-success", response_model=PaymentStatusResponse)
async def simulate_payment_success(
    order_id: int,
    current_user: User = Depends(require_role(UserRole.CUSTOMER, UserRole.ADMIN)),
    session: AsyncSession = Depends(get_session),
):
    """
    DEV/DEMO: Simulate a successful Kaspi payment without hitting the real gateway.
    In production this is triggered by Kaspi webhook.
    """
    result = await session.execute(select(Order).where(Order.id == order_id))
    order = result.scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if current_user.role == UserRole.CUSTOMER and order.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    existing = await session.execute(select(Payment).where(Payment.order_id == order_id))
    payment = existing.scalars().first()
    if not payment:
        payment = Payment(order_id=order.id, amount_kzt=order.total_amount)
        session.add(payment)

    if payment.status == PaymentStatus.COMPLETED:
        raise HTTPException(status_code=409, detail="Already paid")

    payment.status = PaymentStatus.COMPLETED
    payment.kaspi_ref_id = f"KASPI-SIM-{secrets.token_hex(8).upper()}"
    payment.paid_at = _utcnow()

    order.status = OrderStatus.CONFIRMED
    order.updated_at = _utcnow()

    audit = AuditLog(
        table_name="payments", record_id=payment.id, action="UPDATE",
        actor_id=current_user.id,
        new_data=str({"status": "completed", "ref": payment.kaspi_ref_id}),
    )
    session.add(order)
    session.add(audit)
    await session.commit()
    await session.refresh(payment)

    return PaymentStatusResponse(
        payment_id=payment.id,
        order_id=order.id,
        amount_kzt=payment.amount_kzt,
        status=payment.status.value,
        kaspi_ref_id=payment.kaspi_ref_id,
        paid_at=payment.paid_at,
    )


@router.get("/{order_id}/status", response_model=PaymentStatusResponse)
async def get_payment_status(
    order_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get current payment status for an order."""
    result = await session.execute(select(Order).where(Order.id == order_id))
    order = result.scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if current_user.role == UserRole.CUSTOMER and order.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    existing = await session.execute(select(Payment).where(Payment.order_id == order_id))
    payment = existing.scalars().first()
    if not payment:
        raise HTTPException(status_code=404, detail="No payment record found for this order")

    return PaymentStatusResponse(
        payment_id=payment.id,
        order_id=order.id,
        amount_kzt=payment.amount_kzt,
        status=payment.status.value,
        kaspi_ref_id=payment.kaspi_ref_id,
        paid_at=payment.paid_at,
    )
