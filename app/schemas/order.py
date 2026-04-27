from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from app.models.order import OrderStatus


class OrderItemCreate(BaseModel):
    listing_id: int
    quantity: int


class OrderCreateRequest(BaseModel):
    items: List[OrderItemCreate]


class OrderItemResponse(BaseModel):
    id: int
    listing_id: int
    quantity: int
    unit_price: int

    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    id: int
    customer_id: int
    vendor_id: int
    status: OrderStatus
    total_amount: int
    pickup_token: str
    items: List[OrderItemResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True


class OrderStatusUpdate(BaseModel):
    status: OrderStatus
    reason: Optional[str] = None
