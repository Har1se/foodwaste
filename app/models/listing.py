import enum
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional, List
from sqlmodel import SQLModel, Field, Column, Relationship
import sqlalchemy as sa

if TYPE_CHECKING:
    from app.models.vendor import Vendor
    from app.models.order import OrderItem


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ListingStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    DISCOUNTED = "discounted"    # Price decay applied
    FREE = "free"                # Near expiry, free to take
    COMPOST = "compost"          # Expired, waste
    PAUSED = "paused"
    SOLD_OUT = "sold_out"


class AllergenCode(str, enum.Enum):
    NONE = "none"
    GLUTEN = "gluten"
    DAIRY = "dairy"
    EGGS = "eggs"
    NUTS = "nuts"
    SOY = "soy"
    FISH = "fish"
    SHELLFISH = "shellfish"
    SESAME = "sesame"


class Listing(SQLModel, table=True):
    __tablename__ = "listings"
    __table_args__ = (
        sa.CheckConstraint("current_price <= original_price", name="ck_price_order"),
        sa.CheckConstraint("current_price >= 0", name="ck_floor_price"),
        sa.CheckConstraint("quantity_available >= 0", name="ck_qty_nonneg"),
        sa.CheckConstraint("discount_percentage BETWEEN 1 AND 90", name="ck_discount"),
        sa.Index("ix_listing_vendor_status", "vendor_id", "status"),
        sa.Index("ix_listing_geo", "latitude", "longitude"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    vendor_id: int = Field(foreign_key="vendors.id", index=True)
    title: str = Field(max_length=200)
    description: str = Field(max_length=1000)
    original_price: int = Field(ge=500)      # KZT integer
    current_price: int = Field(ge=0)
    discount_percentage: float = Field(ge=1, le=90)
    quantity_total: int = Field(ge=1)
    quantity_available: int = Field(ge=0)
    status: ListingStatus = Field(
        default=ListingStatus.DRAFT,
        sa_column=Column(
            sa.Enum(ListingStatus, name="listingstatus", values_callable=lambda obj: [e.value for e in obj]),
            nullable=False,
            server_default=sa.text("'draft'"),
        ),
    )
    pickup_window_start: datetime = Field()
    pickup_window_end: datetime = Field()
    days_active: int = Field(default=0)
    latitude: float = Field()
    longitude: float = Field()
    photo_url: Optional[str] = Field(default=None, max_length=500)
    category: Optional[str] = Field(default=None, max_length=50, index=True)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    # Relationships
    vendor: Optional["Vendor"] = Relationship(back_populates="listings")
    allergens: List["ListingAllergen"] = Relationship(back_populates="listing")
    order_items: List["OrderItem"] = Relationship(back_populates="listing")


class ListingAllergen(SQLModel, table=True):
    __tablename__ = "listing_allergens"
    __table_args__ = (
        sa.PrimaryKeyConstraint("listing_id", "allergen_code"),
    )

    listing_id: int = Field(foreign_key="listings.id")
    allergen_code: str = Field(max_length=20)

    # Relationship
    listing: Optional[Listing] = Relationship(back_populates="allergens")
