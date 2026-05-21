import math
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_session
from app.models.driver import Driver, Delivery, DriverStatus, DeliveryStatus
from app.models.order import Order, OrderStatus
from app.models.user import User
from app.schemas.driver import (
    DriverRegister, DriverLocationUpdate, DriverResponse,
    DeliveryStatusUpdate, DeliveryResponse, RouteOptimizeResponse, RouteStop,
)

router = APIRouter(tags=["Drivers"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


@router.post("/drivers/register", response_model=DriverResponse, status_code=201, tags=["Drivers"])
async def register_driver(
    data: DriverRegister,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    existing_r = await session.execute(select(Driver).where(Driver.user_id == current_user.id))
    if existing_r.scalars().first():
        raise HTTPException(status_code=409, detail="Already registered as a driver")
    driver = Driver(user_id=current_user.id, vehicle_type=data.vehicle_type)
    session.add(driver)
    await session.commit()
    await session.refresh(driver)
    return driver


@router.get("/drivers/me", response_model=DriverResponse, tags=["Drivers"])
async def get_my_driver_profile(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Driver).where(Driver.user_id == current_user.id))
    driver = result.scalars().first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver profile not found")
    return driver


@router.patch("/drivers/me/location", response_model=DriverResponse, tags=["Drivers"])
async def update_driver_location(
    data: DriverLocationUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Driver).where(Driver.user_id == current_user.id))
    driver = result.scalars().first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver profile not found")
    driver.current_lat = data.lat
    driver.current_lng = data.lng
    if data.status is not None:
        driver.status = data.status
    driver.updated_at = _utcnow()
    await session.commit()
    await session.refresh(driver)
    return driver


@router.get("/drivers/nearby", response_model=List[DriverResponse], tags=["Drivers"])
async def get_nearby_drivers(
    lat: float,
    lng: float,
    radius_km: float = 5.0,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    result = await session.execute(
        select(Driver).where(
            Driver.status == DriverStatus.AVAILABLE,
            Driver.is_verified.is_(True),
            Driver.current_lat.isnot(None),
            Driver.current_lng.isnot(None),
        )
    )
    drivers = result.scalars().all()
    nearby = [
        d for d in drivers
        if _haversine_km(lat, lng, d.current_lat, d.current_lng) <= radius_km
    ]
    nearby.sort(key=lambda d: _haversine_km(lat, lng, d.current_lat, d.current_lng))
    return nearby


@router.post("/drivers/assign/{order_id}", response_model=DeliveryResponse, status_code=201, tags=["Drivers"])
async def assign_driver_to_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Admin or vendor assigns the nearest available driver to an order."""
    if current_user.role not in ("admin", "vendor"):
        raise HTTPException(status_code=403, detail="Vendor or admin only")

    order_r = await session.execute(select(Order).where(Order.id == order_id))
    order = order_r.scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != OrderStatus.CONFIRMED:
        raise HTTPException(status_code=409, detail="Order must be confirmed to assign driver")

    # FIX: vendors may only assign drivers to their own orders.
    # Old code checked role but not ownership — any vendor could assign any order.
    if current_user.role == "vendor":
        from app.models.vendor import Vendor as VendorModel
        vendor_check_r = await session.execute(
            select(VendorModel).where(VendorModel.user_id == current_user.id)
        )
        requesting_vendor = vendor_check_r.scalars().first()
        if not requesting_vendor or order.vendor_id != requesting_vendor.id:
            raise HTTPException(status_code=403, detail="You can only assign drivers to your own orders")

    existing_r = await session.execute(select(Delivery).where(Delivery.order_id == order_id))
    if existing_r.scalars().first():
        raise HTTPException(status_code=409, detail="Driver already assigned to this order")

    from app.models.listing import Listing
    from app.models.order import OrderItem
    item_r = await session.execute(select(OrderItem).where(OrderItem.order_id == order_id))
    item = item_r.scalars().first()
    if not item:
        raise HTTPException(status_code=422, detail="Order has no items")
    listing_r = await session.execute(select(Listing).where(Listing.id == item.listing_id))
    listing = listing_r.scalars().first()

    pickup_lat = listing.latitude if listing else 43.238
    pickup_lng = listing.longitude if listing else 76.945

    drivers_r = await session.execute(
        select(Driver).where(
            Driver.status == DriverStatus.AVAILABLE,
            Driver.is_verified.is_(True),
            Driver.current_lat.isnot(None),
            Driver.current_lng.isnot(None),
        )
    )
    available = drivers_r.scalars().all()
    if not available:
        raise HTTPException(status_code=404, detail="No available drivers nearby")

    best_driver = min(
        available,
        key=lambda d: _haversine_km(pickup_lat, pickup_lng, d.current_lat, d.current_lng),
    )

    dist = _haversine_km(pickup_lat, pickup_lng, best_driver.current_lat, best_driver.current_lng)

    from app.models.vendor import Vendor
    vendor_r = await session.execute(select(Vendor).where(Vendor.id == order.vendor_id))
    vendor = vendor_r.scalars().first()

    delivery = Delivery(
        order_id=order_id,
        driver_id=best_driver.id,
        pickup_lat=pickup_lat,
        pickup_lng=pickup_lng,
        delivery_lat=vendor.latitude if vendor and hasattr(vendor, "latitude") else pickup_lat,
        delivery_lng=vendor.longitude if vendor and hasattr(vendor, "longitude") else pickup_lng,
        distance_km=round(dist, 2),
    )
    best_driver.status = DriverStatus.BUSY
    best_driver.updated_at = _utcnow()
    session.add(delivery)
    await session.commit()
    await session.refresh(delivery)

    # Notify driver by email about their new delivery assignment
    driver_user_r = await session.execute(select(User).where(User.id == best_driver.user_id))
    driver_user = driver_user_r.scalars().first()
    if driver_user and driver_user.email:
        from app.tasks.email_tasks import send_driver_assignment_email
        vendor_address = vendor.address if vendor else "Алматы"
        vendor_biz_name = vendor.business_name if vendor else "Заведение"
        send_driver_assignment_email.delay(
            driver_user.email, order_id, vendor_biz_name, vendor_address, round(dist, 2),
        )

    return delivery


@router.get("/deliveries/my", response_model=List[DeliveryResponse], tags=["Drivers"])
async def get_my_deliveries(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    driver_r = await session.execute(select(Driver).where(Driver.user_id == current_user.id))
    driver = driver_r.scalars().first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver profile not found")
    result = await session.execute(
        select(Delivery).where(Delivery.driver_id == driver.id).order_by(Delivery.assigned_at.desc())
    )
    return result.scalars().all()


@router.patch("/deliveries/{delivery_id}/status", response_model=DeliveryResponse, tags=["Drivers"])
async def update_delivery_status(
    delivery_id: int,
    data: DeliveryStatusUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    delivery_r = await session.execute(select(Delivery).where(Delivery.id == delivery_id))
    delivery = delivery_r.scalars().first()
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")

    # Admins can update any delivery; drivers can only update their own.
    if current_user.role != "admin":
        driver_r = await session.execute(select(Driver).where(Driver.user_id == current_user.id))
        driver = driver_r.scalars().first()
        if not driver or delivery.driver_id != driver.id:
            raise HTTPException(status_code=403, detail="Not your delivery")
    else:
        driver_r = await session.execute(select(Driver).where(Driver.id == delivery.driver_id))
        driver = driver_r.scalars().first()

    now = _utcnow()
    delivery.status = data.status
    if data.notes:
        delivery.notes = data.notes
    if data.status == DeliveryStatus.AT_PICKUP:
        delivery.picked_up_at = now
    elif data.status == DeliveryStatus.DELIVERED:
        delivery.delivered_at = now
        driver.status = DriverStatus.AVAILABLE
        driver.total_deliveries += 1
        driver.updated_at = now
    elif data.status == DeliveryStatus.FAILED:
        driver.status = DriverStatus.AVAILABLE
        driver.updated_at = now

    await session.commit()
    await session.refresh(delivery)
    return delivery


@router.get("/drivers/route-optimize", response_model=RouteOptimizeResponse, tags=["Drivers"])
async def optimize_route(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Nearest-neighbor route optimization for driver's active deliveries."""
    driver_r = await session.execute(select(Driver).where(Driver.user_id == current_user.id))
    driver = driver_r.scalars().first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver profile not found")
    if driver.current_lat is None:
        raise HTTPException(status_code=422, detail="Driver location not set")

    active_statuses = (
        DeliveryStatus.ASSIGNED,
        DeliveryStatus.EN_ROUTE_PICKUP,
        DeliveryStatus.AT_PICKUP,
        DeliveryStatus.EN_ROUTE_DELIVERY,
    )
    result = await session.execute(
        select(Delivery).where(
            Delivery.driver_id == driver.id,
            Delivery.status.in_(active_statuses),
        )
    )
    deliveries = result.scalars().all()
    if not deliveries:
        return RouteOptimizeResponse(driver_id=driver.id, total_distance_km=0.0, stops=[])

    unvisited = list(deliveries)
    stops: List[RouteStop] = []
    current_lat, current_lng = driver.current_lat, driver.current_lng
    total_dist = 0.0
    seq = 1

    while unvisited:
        nearest = min(
            unvisited,
            key=lambda d: _haversine_km(current_lat, current_lng, d.pickup_lat, d.pickup_lng),
        )
        dist = _haversine_km(current_lat, current_lng, nearest.pickup_lat, nearest.pickup_lng)
        total_dist += dist
        stops.append(RouteStop(
            order_id=nearest.order_id,
            delivery_id=nearest.id,
            lat=nearest.pickup_lat,
            lng=nearest.pickup_lng,
            sequence=seq,
            distance_from_prev_km=round(dist, 2),
        ))
        current_lat, current_lng = nearest.pickup_lat, nearest.pickup_lng
        unvisited.remove(nearest)
        seq += 1

    return RouteOptimizeResponse(
        driver_id=driver.id,
        total_distance_km=round(total_dist, 2),
        stops=stops,
    )
