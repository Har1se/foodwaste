import enum
from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, Column, Relationship
import sqlalchemy as sa


class UserRole(str, enum.Enum):
    CUSTOMER = "customer"
    VENDOR = "vendor"
    DRIVER = "driver"
    ADMIN = "admin"


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True, max_length=255)
    phone: Optional[str] = Field(default=None, unique=True, index=True, max_length=20)
    full_name: Optional[str] = Field(default=None, max_length=255)
    password_hash: str = Field(max_length=255)
    role: UserRole = Field(
        default=UserRole.CUSTOMER,
        sa_column=Column(sa.Enum(UserRole), nullable=False, server_default="customer"),
    )
    is_active: bool = Field(default=True)
    allergen_profile: Optional[str] = Field(default=None, max_length=500)  # JSON list of allergens
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(sa.DateTime, onupdate=datetime.utcnow, nullable=False, server_default=sa.func.now()),
    )

    # Relationships
    vendor: Optional["Vendor"] = Relationship(back_populates="user")
    orders: List["Order"] = Relationship(back_populates="customer")


class OTPCode(SQLModel, table=True):
    __tablename__ = "otp_codes"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    code: str = Field(max_length=6)
    expires_at: datetime = Field()
    used: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
