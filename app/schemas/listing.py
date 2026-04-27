from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from app.models.listing import ListingStatus, AllergenCode


class ListingCreate(BaseModel):
    title: str
    description: str
    original_price: int      # KZT
    discount_percentage: float = Field(ge=1, le=90)
    quantity_total: int
    pickup_window_start: datetime
    pickup_window_end: datetime
    allergens: List[AllergenCode]
    latitude: float
    longitude: float
    photo_url: Optional[str] = None

    @field_validator("allergens")
    @classmethod
    def allergens_required(cls, v):
        if not v:
            raise ValueError("At least one allergen tag is required (use 'none' if no allergens)")
        return v

    @field_validator("pickup_window_end")
    @classmethod
    def window_valid(cls, v, info):
        start = info.data.get("pickup_window_start")
        if start and v <= start:
            raise ValueError("pickup_window_end must be after pickup_window_start")
        return v


class ListingUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    quantity_total: Optional[int] = None
    pickup_window_start: Optional[datetime] = None
    pickup_window_end: Optional[datetime] = None
    allergens: Optional[List[AllergenCode]] = None
    status: Optional[ListingStatus] = None


class AllergenFilterRequest(BaseModel):
    """Allergy parser: validate ingredient list against user allergen profile."""
    ingredients: List[str]
    user_allergens: List[AllergenCode]


class AllergenFilterResponse(BaseModel):
    safe: bool
    detected_allergens: List[AllergenCode]
    flagged_ingredients: List[str]
    message: str


class ListingResponse(BaseModel):
    id: int
    vendor_id: int
    title: str
    description: str
    original_price: int
    current_price: int
    discount_percentage: float = Field(ge=1, le=90)
    quantity_total: int
    quantity_available: int
    status: ListingStatus
    pickup_window_start: datetime
    pickup_window_end: datetime
    allergens: List[AllergenCode] = []
    latitude: float
    longitude: float
    photo_url: Optional[str]
    days_active: int
    created_at: datetime

    class Config:
        from_attributes = True
