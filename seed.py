"""
Create demo data for local development.

Run:
    docker compose exec api python seed.py
"""

import asyncio
from datetime import datetime, timedelta, timezone

from sqlmodel import select

from app.core.security import hash_password
from app.database import AsyncSessionLocal
from app.models.listing import Listing, ListingAllergen, ListingStatus
from app.models.user import User, UserRole
from app.models.vendor import Vendor


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def get_or_create_user(session, email: str, password: str, role: UserRole, full_name: str) -> User:
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if user:
        user.password_hash = hash_password(password)
        user.role = role
        user.full_name = full_name
        user.email_verified = True
        user.is_active = True
        session.add(user)
        await session.flush()
        return user

    user = User(
        email=email,
        password_hash=hash_password(password),
        role=role,
        full_name=full_name,
        email_verified=True,
        is_active=True,
    )
    session.add(user)
    await session.flush()
    return user


async def seed():
    async with AsyncSessionLocal() as session:
        admin = await get_or_create_user(session, "admin@test.kz", "Secure123!", UserRole.ADMIN, "Demo Admin")
        vendor_user = await get_or_create_user(session, "vendor@test.kz", "Secure123!", UserRole.VENDOR, "Demo Vendor")
        customer = await get_or_create_user(session, "customer@test.kz", "Secure123!", UserRole.CUSTOMER, "Demo Customer")

        result = await session.execute(select(Vendor).where(Vendor.user_id == vendor_user.id))
        vendor = result.scalars().first()
        if not vendor:
            vendor = Vendor(
                user_id=vendor_user.id,
                business_name="Green Cafe",
                bin_number="123456789012",
                address="Almaty, Abaya 1",
                latitude=43.238,
                longitude=76.945,
                is_approved=True,
            )
            session.add(vendor)
            await session.flush()
        else:
            vendor.business_name = "Green Cafe"
            vendor.is_approved = True
            session.add(vendor)
            await session.flush()

        existing = await session.execute(select(Listing).where(Listing.vendor_id == vendor.id))
        for listing in existing.scalars().all():
            allergens = await session.execute(select(ListingAllergen).where(ListingAllergen.listing_id == listing.id))
            for item in allergens.scalars().all():
                await session.delete(item)
            await session.delete(listing)
        await session.flush()

        now = utcnow()
        products = [
            {
                "title": "Sushi Box",
                "description": "Fresh salmon rolls, rice and soy sauce. Made today.",
                "original_price": 5000,
                "current_price": 3000,
                "discount_percentage": 40,
                "quantity_total": 10,
                "quantity_available": 10,
                "status": ListingStatus.ACTIVE,
                "allergens": ["fish", "gluten"],
                "photo_url": "https://images.unsplash.com/photo-1579871494447-9811cf80d66c?auto=format&fit=crop&w=900&q=80",
            },
            {
                "title": "Bakery Mix",
                "description": "Croissants, buns and pastries from today's morning batch.",
                "original_price": 2400,
                "current_price": 1200,
                "discount_percentage": 50,
                "quantity_total": 12,
                "quantity_available": 12,
                "status": ListingStatus.ACTIVE,
                "allergens": ["gluten", "dairy", "eggs"],
                "photo_url": "https://images.unsplash.com/photo-1509440159596-0249088772ff?auto=format&fit=crop&w=900&q=80",
            },
            {
                "title": "Healthy Salad Bowl",
                "description": "Greens, chickpeas, tomatoes and house dressing.",
                "original_price": 2800,
                "current_price": 1680,
                "discount_percentage": 40,
                "quantity_total": 8,
                "quantity_available": 8,
                "status": ListingStatus.ACTIVE,
                "allergens": ["sesame"],
                "photo_url": "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?auto=format&fit=crop&w=900&q=80",
            },
            {
                "title": "Lunch Box Chicken",
                "description": "Rice, grilled chicken and vegetables. Ready to pick up.",
                "original_price": 3500,
                "current_price": 2100,
                "discount_percentage": 40,
                "quantity_total": 7,
                "quantity_available": 7,
                "status": ListingStatus.ACTIVE,
                "allergens": ["none"],
                "photo_url": "https://images.unsplash.com/photo-1543353071-10c8ba85a904?auto=format&fit=crop&w=900&q=80",
            },
            {
                "title": "Pizza Slices",
                "description": "Assorted slices from the evening service.",
                "original_price": 3200,
                "current_price": 1600,
                "discount_percentage": 50,
                "quantity_total": 9,
                "quantity_available": 9,
                "status": ListingStatus.ACTIVE,
                "allergens": ["gluten", "dairy"],
                "photo_url": "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?auto=format&fit=crop&w=900&q=80",
            },
            {
                "title": "Fruit Smoothies",
                "description": "Mango, banana and berry smoothies. Chilled and bottled.",
                "original_price": 1800,
                "current_price": 900,
                "discount_percentage": 50,
                "quantity_total": 15,
                "quantity_available": 15,
                "status": ListingStatus.ACTIVE,
                "allergens": ["none"],
                "photo_url": "https://images.unsplash.com/photo-1505252585461-04db1eb84625?auto=format&fit=crop&w=900&q=80",
            },
        ]

        for index, data in enumerate(products):
            allergens = data.pop("allergens")
            listing = Listing(
                vendor_id=vendor.id,
                pickup_window_start=now + timedelta(hours=1),
                pickup_window_end=now + timedelta(hours=6 + index),
                days_active=0,
                latitude=43.238 + index * 0.002,
                longitude=76.945 + index * 0.002,
                **data,
            )
            session.add(listing)
            await session.flush()
            for code in allergens:
                session.add(ListingAllergen(listing_id=listing.id, allergen_code=code))

        await session.commit()

    print("Demo data ready")
    print("Customer: customer@test.kz / Secure123!")
    print("Vendor:   vendor@test.kz / Secure123!")
    print("Admin:    admin@test.kz / Secure123!")
    print(f"Seeded by admin user id: {admin.id}, sample customer id: {customer.id}")


if __name__ == "__main__":
    asyncio.run(seed())
