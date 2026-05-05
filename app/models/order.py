import enum
from datetime import datetime, timezone
from typing import Optional, List
from sqlmodel import SQLModel, Field, Column, Relationship
import sqlalchemy as sa


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    READY_FOR_PICKUP = "ready_for_pickup"
    PICKED_UP = "picked_up"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class Order(SQLModel, table=True):
    __tablename__ = "orders"
    __table_args__ = (
        sa.Index("ix_order_customer", "customer_id", "status"),
        sa.Index("ix_order_vendor", "vendor_id", "status"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    customer_id: int = Field(foreign_key="users.id", index=True)
    vendor_id: int = Field(foreign_key="vendors.id", index=True)
    status: OrderStatus = Field(
        default=OrderStatus.PENDING,
        sa_column=Column(
            sa.Enum(OrderStatus, name="orderstatus", values_callable=lambda obj: [e.value for e in obj]),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
    )
    total_amount: int = Field(ge=0)   # KZT
    pickup_token: str = Field(max_length=64, unique=True)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    # Relationships
    customer: Optional["User"] = Relationship(back_populates="orders")
    vendor: Optional["Vendor"] = Relationship(back_populates="orders")
    items: List["OrderItem"] = Relationship(back_populates="order")
    payment: Optional["Payment"] = Relationship(back_populates="order")


class OrderItem(SQLModel, table=True):
    __tablename__ = "order_items"

    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="orders.id", index=True)
    listing_id: int = Field(foreign_key="listings.id")
    quantity: int = Field(ge=1)
    unit_price: int = Field(ge=0)   # snapshot at order time

    # Relationships
    order: Optional[Order] = Relationship(back_populates="items")
    listing: Optional["Listing"] = Relationship(back_populates="order_items")


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class Payment(SQLModel, table=True):
    __tablename__ = "payments"

    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="orders.id", unique=True)
    amount_kzt: int = Field(ge=0)
    status: PaymentStatus = Field(
        default=PaymentStatus.PENDING,
        sa_column=Column(
            sa.Enum(PaymentStatus, name="paymentstatus", values_callable=lambda obj: [e.value for e in obj]),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
    )
    kaspi_ref_id: Optional[str] = Field(default=None, unique=True, max_length=100)
    paid_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=_utcnow)

    # Relationship
    order: Optional[Order] = Relationship(back_populates="payment")


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_logs"
    __table_args__ = (sa.Index("ix_audit_actor_time", "actor_id", "created_at"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    table_name: str = Field(max_length=100)
    record_id: int = Field()
    action: str = Field(max_length=20)   # INSERT, UPDATE, DELETE
    actor_id: Optional[int] = Field(default=None)
    old_data: Optional[str] = Field(default=None)   # JSON string
    new_data: Optional[str] = Field(default=None)   # JSON string
    created_at: datetime = Field(default_factory=_utcnow)
