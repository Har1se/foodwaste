from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from app.models.order import OrderStatus


class OrderItemCreate(BaseModel):
    listing_id: int
    quantity: int


class OrderCreateRequest(BaseModel):
    items: List[OrderItemCreate]


class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    listing_id: int
    quantity: int
    unit_price: int


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    vendor_id: int
    status: OrderStatus
    total_amount: int
    pickup_token: str
    items: List[OrderItemResponse] = []
    created_at: datetime


class OrderStatusUpdate(BaseModel):
    status: OrderStatus
    reason: Optional[str] = None
