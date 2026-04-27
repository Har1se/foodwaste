from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from pydantic import BaseModel
from typing import Optional

from app.database import get_session
from app.core.dependencies import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.vendor import Vendor

router = APIRouter(prefix="/vendors", tags=["Vendors"])


class VendorRegisterRequest(BaseModel):
    business_name: str
    bin_number: str
    address: str
    latitude: float
    longitude: float


class VendorResponse(BaseModel):
    id: int
    user_id: int
    business_name: str
    bin_number: str
    address: str
    latitude: float
    longitude: float
    is_approved: bool

    class Config:
        from_attributes = True


@router.post("/register", response_model=VendorResponse, status_code=201)
async def register_vendor(
    data: VendorRegisterRequest,
    current_user: User = Depends(require_role(UserRole.VENDOR, UserRole.ADMIN)),
    session: AsyncSession = Depends(get_session),
):
    """Submit vendor profile for admin approval."""
    existing = await session.execute(select(Vendor).where(Vendor.user_id == current_user.id))
    if existing.first():
        raise HTTPException(status_code=409, detail="Vendor profile already exists")

    bin_check = await session.execute(select(Vendor).where(Vendor.bin_number == data.bin_number))
    if bin_check.first():
        raise HTTPException(status_code=409, detail="BIN number already registered")

    vendor = Vendor(
        user_id=current_user.id,
        business_name=data.business_name,
        bin_number=data.bin_number,
        address=data.address,
        latitude=data.latitude,
        longitude=data.longitude,
    )
    session.add(vendor)
    await session.commit()
    await session.refresh(vendor)
    return VendorResponse.model_validate(vendor)


@router.get("/me", response_model=VendorResponse)
async def get_my_vendor(
    current_user: User = Depends(require_role(UserRole.VENDOR, UserRole.ADMIN)),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Vendor).where(Vendor.user_id == current_user.id))
    vendor = result.scalars().first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor profile not found")
    return VendorResponse.model_validate(vendor)


@router.get("/{vendor_id}", response_model=VendorResponse)
async def get_vendor(vendor_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Vendor).where(Vendor.id == vendor_id))
    vendor = result.scalars().first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return VendorResponse.model_validate(vendor)
