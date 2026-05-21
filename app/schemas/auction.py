from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class AuctionCreate(BaseModel):
    listing_id: int
    start_price: int = Field(ge=1, description="Max acceptable price (KZT)")
    reserve_price: int = Field(ge=0, description="Min acceptable price (KZT)")
    ends_at: datetime


class BidCreate(BaseModel):
    amount: int = Field(ge=0, description="Bid amount in KZT — lowest unique bid wins")


class BidResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    auction_id: int
    bidder_id: int
    amount: int
    created_at: datetime


class AuctionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    listing_id: int
    vendor_id: int
    start_price: int
    reserve_price: int
    ends_at: datetime
    status: str
    winner_user_id: Optional[int]
    winning_bid_amount: Optional[int]
    bid_count: int = 0
    created_at: datetime
    updated_at: datetime
