from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional, List
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.listing import Listing
    from app.models.order import Order


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Vendor(SQLModel, table=True):
    __tablename__ = "vendors"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", unique=True, index=True)
    business_name: str = Field(max_length=255)
    bin_number: str = Field(max_length=12, unique=True)
    address: str = Field(max_length=500)
    latitude: float = Field()
    longitude: float = Field()
    is_approved: bool = Field(default=False)
    approved_at: Optional[datetime] = Field(default=None)
    platform_fee_pct: float = Field(default=15.0)
    created_at: datetime = Field(default_factory=_utcnow)

    # Relationships
    user: Optional["User"] = Relationship(back_populates="vendor")
    listings: List["Listing"] = Relationship(back_populates="vendor")
    orders: List["Order"] = Relationship(back_populates="vendor")
