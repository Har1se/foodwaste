from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from app.database import get_session
from app.core.dependencies import require_role
from app.models.user import User, UserRole
from app.models.vendor import Vendor
from app.models.listing import Listing, ListingStatus
from app.models.order import Order, OrderStatus, AuditLog
from app.services.listing_service import apply_price_decay

router = APIRouter(prefix="/admin", tags=["Admin"])


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


@router.patch("/vendors/{vendor_id}/approve")
async def approve_vendor(
    vendor_id: int,
    data: VendorApprovalRequest,
    admin: User = Depends(require_role(UserRole.ADMIN)),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Vendor).where(Vendor.id == vendor_id))
    vendor = result.scalars().first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    if data.action == "approve":
        vendor.is_approved = True
        vendor.approved_at = datetime.utcnow()
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
    return {"detail": f"Vendor {data.action}d successfully"}


@router.patch("/users/{user_id}/suspend")
async def suspend_user(
    user_id: int,
    is_active: bool,
    admin: User = Depends(require_role(UserRole.ADMIN)),
    session: AsyncSession = Depends(get_session),
):
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


@router.post("/trigger-price-decay")
async def trigger_price_decay(
    _: User = Depends(require_role(UserRole.ADMIN)),
    session: AsyncSession = Depends(get_session),
):
    updated = await apply_price_decay(session)
    return {"detail": f"Price decay applied to {updated} listings"}
