from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field
from app.models.driver import VehicleType, DriverStatus, DeliveryStatus


class DriverRegister(BaseModel):
    vehicle_type: VehicleType = VehicleType.BICYCLE


class DriverLocationUpdate(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    status: Optional[DriverStatus] = None


class DriverResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    vehicle_type: VehicleType
    current_lat: Optional[float]
    current_lng: Optional[float]
    status: DriverStatus
    is_verified: bool
    rating: float
    total_deliveries: int
    created_at: datetime


class DeliveryStatusUpdate(BaseModel):
    status: DeliveryStatus
    notes: Optional[str] = None


class DeliveryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    driver_id: int
    pickup_lat: float
    pickup_lng: float
    delivery_lat: float
    delivery_lng: float
    status: DeliveryStatus
    distance_km: Optional[float]
    assigned_at: datetime
    picked_up_at: Optional[datetime]
    delivered_at: Optional[datetime]
    notes: Optional[str]


class RouteStop(BaseModel):
    order_id: int
    delivery_id: int
    lat: float
    lng: float
    sequence: int
    distance_from_prev_km: float


class RouteOptimizeResponse(BaseModel):
    driver_id: int
    total_distance_km: float
    stops: List[RouteStop]
