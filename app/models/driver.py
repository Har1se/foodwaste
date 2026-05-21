import enum
from datetime import datetime, timezone
from typing import Optional, List
from sqlmodel import SQLModel, Field, Column, Relationship
import sqlalchemy as sa


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class VehicleType(str, enum.Enum):
    BICYCLE = "bicycle"
    SCOOTER = "scooter"
    CAR = "car"
    WALK = "walk"


class DriverStatus(str, enum.Enum):
    AVAILABLE = "available"
    BUSY = "busy"
    OFFLINE = "offline"


class DeliveryStatus(str, enum.Enum):
    ASSIGNED = "assigned"
    EN_ROUTE_PICKUP = "en_route_pickup"
    AT_PICKUP = "at_pickup"
    EN_ROUTE_DELIVERY = "en_route_delivery"
    DELIVERED = "delivered"
    FAILED = "failed"


class Driver(SQLModel, table=True):
    __tablename__ = "drivers"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", unique=True, index=True)
    vehicle_type: VehicleType = Field(
        default=VehicleType.BICYCLE,
        sa_column=Column(
            sa.Enum(VehicleType, name="vehicletype", values_callable=lambda obj: [e.value for e in obj]),
            nullable=False,
            server_default=sa.text("'bicycle'"),
        ),
    )
    current_lat: Optional[float] = Field(default=None)
    current_lng: Optional[float] = Field(default=None)
    status: DriverStatus = Field(
        default=DriverStatus.OFFLINE,
        sa_column=Column(
            sa.Enum(DriverStatus, name="driverstatus", values_callable=lambda obj: [e.value for e in obj]),
            nullable=False,
            server_default=sa.text("'offline'"),
        ),
    )
    is_verified: bool = Field(default=False)
    rating: float = Field(default=5.0, ge=1.0, le=5.0)
    total_deliveries: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    deliveries: List["Delivery"] = Relationship(back_populates="driver")


class Delivery(SQLModel, table=True):
    __tablename__ = "deliveries"
    __table_args__ = (
        sa.Index("ix_delivery_driver_status", "driver_id", "status"),
        sa.Index("ix_delivery_order", "order_id"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="orders.id", unique=True, index=True)
    driver_id: int = Field(foreign_key="drivers.id", index=True)
    pickup_lat: float = Field()
    pickup_lng: float = Field()
    delivery_lat: float = Field()
    delivery_lng: float = Field()
    status: DeliveryStatus = Field(
        default=DeliveryStatus.ASSIGNED,
        sa_column=Column(
            sa.Enum(DeliveryStatus, name="deliverystatus", values_callable=lambda obj: [e.value for e in obj]),
            nullable=False,
            server_default=sa.text("'assigned'"),
        ),
    )
    distance_km: Optional[float] = Field(default=None, ge=0)
    assigned_at: datetime = Field(default_factory=_utcnow)
    picked_up_at: Optional[datetime] = Field(default=None)
    delivered_at: Optional[datetime] = Field(default=None)
    notes: Optional[str] = Field(default=None, max_length=500)

    driver: Optional[Driver] = Relationship(back_populates="deliveries")
