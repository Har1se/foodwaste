import enum
from datetime import datetime, timezone
from typing import Optional, List
from sqlmodel import SQLModel, Field, Column, Relationship
import sqlalchemy as sa


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AuctionStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    ENDED = "ended"
    CANCELLED = "cancelled"


class Auction(SQLModel, table=True):
    __tablename__ = "auctions"
    __table_args__ = (
        sa.CheckConstraint("reserve_price <= start_price", name="ck_auction_reserve"),
        sa.Index("ix_auction_listing", "listing_id"),
        sa.Index("ix_auction_status_ends", "status", "ends_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    listing_id: int = Field(foreign_key="listings.id", index=True)
    vendor_id: int = Field(foreign_key="vendors.id", index=True)
    start_price: int = Field(ge=1)        # maximum acceptable price (KZT)
    reserve_price: int = Field(ge=0)      # minimum — won't sell below this
    ends_at: datetime = Field()
    status: AuctionStatus = Field(
        default=AuctionStatus.PENDING,
        sa_column=Column(
            sa.Enum(AuctionStatus, name="auctionstatus", values_callable=lambda obj: [e.value for e in obj]),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
    )
    winner_user_id: Optional[int] = Field(default=None, foreign_key="users.id")
    winning_bid_amount: Optional[int] = Field(default=None)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    bids: List["AuctionBid"] = Relationship(back_populates="auction")


class AuctionBid(SQLModel, table=True):
    __tablename__ = "auction_bids"
    __table_args__ = (
        sa.CheckConstraint("amount >= 0", name="ck_bid_amount_nonneg"),
        sa.Index("ix_bid_auction_amount", "auction_id", "amount"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    auction_id: int = Field(foreign_key="auctions.id", index=True)
    bidder_id: int = Field(foreign_key="users.id", index=True)
    amount: int = Field(ge=0)             # KZT — lowest unique bid wins
    created_at: datetime = Field(default_factory=_utcnow)

    auction: Optional[Auction] = Relationship(back_populates="bids")
