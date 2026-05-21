"""
Direct service-layer tests.

These tests call service functions with a db_session fixture directly —
no HTTP overhead, no conftest patching indirection. This guarantees
coverage tracking on all Python versions / platforms.
"""
import pytest
from datetime import datetime, timezone, timedelta
from sqlmodel import select

from app.core.security import hash_password
from app.models.user import User, OTPCode, UserRole
from app.models.vendor import Vendor
from app.models.listing import Listing, ListingStatus
from app.schemas.auth import RegisterRequest, LoginRequest
from app.schemas.listing import ListingCreate
from app.schemas.order import OrderCreateRequest, OrderItemCreate, OrderStatusUpdate
from app.models.order import OrderStatus


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ── Auth service ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_svc_register_user(db_session):
    from app.services.auth_service import register_user
    data = RegisterRequest(email="svc_reg@test.kz", password="Secure123!", role=UserRole.CUSTOMER, full_name="Direct")
    user, otp_code = await register_user(data, db_session)
    assert user.id is not None
    assert len(otp_code) == 6


@pytest.mark.asyncio
async def test_svc_register_duplicate_email(db_session):
    from app.services.auth_service import register_user
    from fastapi import HTTPException
    data = RegisterRequest(email="svc_dup@test.kz", password="Secure123!", role=UserRole.CUSTOMER)
    await register_user(data, db_session)
    with pytest.raises(HTTPException) as exc:
        await register_user(data, db_session)
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_svc_register_duplicate_phone(db_session):
    from app.services.auth_service import register_user
    from fastapi import HTTPException
    await register_user(
        RegisterRequest(email="phone1@test.kz", password="Secure123!", role=UserRole.CUSTOMER, phone="+77770000001"),
        db_session,
    )
    with pytest.raises(HTTPException) as exc:
        await register_user(
            RegisterRequest(email="phone2@test.kz", password="Secure123!", role=UserRole.CUSTOMER, phone="+77770000001"),
            db_session,
        )
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_svc_verify_email_not_found(db_session):
    from app.services.auth_service import verify_email
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await verify_email("nobody_ve@test.kz", "000000", db_session)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_svc_verify_email_already_verified(db_session):
    from app.services.auth_service import verify_email
    user = User(email="alrver@test.kz", password_hash=hash_password("pw"), role=UserRole.CUSTOMER, email_verified=True)
    db_session.add(user)
    await db_session.commit()
    # Should return without raising (idempotent)
    await verify_email("alrver@test.kz", "any_code", db_session)


@pytest.mark.asyncio
async def test_svc_verify_email_wrong_code(db_session):
    from app.services.auth_service import verify_email
    from fastapi import HTTPException
    user = User(email="wrongotp@test.kz", password_hash=hash_password("pw"), role=UserRole.CUSTOMER, email_verified=False)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    otp = OTPCode(user_id=user.id, code="111111", expires_at=_now() + timedelta(minutes=15))
    db_session.add(otp)
    await db_session.commit()
    with pytest.raises(HTTPException) as exc:
        await verify_email("wrongotp@test.kz", "000000", db_session)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_svc_verify_email_correct_code(db_session):
    from app.services.auth_service import verify_email
    user = User(email="corrcode@test.kz", password_hash=hash_password("pw"), role=UserRole.CUSTOMER, email_verified=False)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    otp = OTPCode(user_id=user.id, code="888888", expires_at=_now() + timedelta(minutes=15))
    db_session.add(otp)
    await db_session.commit()
    await verify_email("corrcode@test.kz", "888888", db_session)
    result = await db_session.execute(select(User).where(User.email == "corrcode@test.kz"))
    assert result.scalars().first().email_verified is True


@pytest.mark.asyncio
async def test_svc_resend_verification_not_found(db_session):
    from app.services.auth_service import resend_verification
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await resend_verification("nobody_rv2@test.kz", db_session)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_svc_resend_verification_already_verified(db_session):
    from app.services.auth_service import resend_verification
    from fastapi import HTTPException
    user = User(email="alrver2@test.kz", password_hash=hash_password("pw"), role=UserRole.CUSTOMER, email_verified=True)
    db_session.add(user)
    await db_session.commit()
    with pytest.raises(HTTPException) as exc:
        await resend_verification("alrver2@test.kz", db_session)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_svc_resend_verification_success(db_session):
    from app.services.auth_service import resend_verification
    user = User(email="resendok@test.kz", password_hash=hash_password("pw"), role=UserRole.CUSTOMER, email_verified=False)
    db_session.add(user)
    await db_session.commit()
    code = await resend_verification("resendok@test.kz", db_session)
    assert len(code) == 6


@pytest.mark.asyncio
async def test_svc_forgot_password_nonexistent(db_session):
    from app.services.auth_service import forgot_password
    result = await forgot_password("ghost@test.kz", db_session)
    assert result is None


@pytest.mark.asyncio
async def test_svc_forgot_password_existing(db_session):
    from app.services.auth_service import forgot_password
    user = User(email="forgotok@test.kz", password_hash=hash_password("pw"), role=UserRole.CUSTOMER, email_verified=True)
    db_session.add(user)
    await db_session.commit()
    result = await forgot_password("forgotok@test.kz", db_session)
    assert result is not None
    email, token = result
    assert email == "forgotok@test.kz"
    assert len(token) > 10


@pytest.mark.asyncio
async def test_svc_reset_password_invalid_token(db_session):
    from app.services.auth_service import reset_password
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await reset_password("badtoken", "NewSecure123!", db_session)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_svc_reset_password_success(db_session):
    from app.services.auth_service import forgot_password, reset_password, login_user
    user = User(email="resetok@test.kz", password_hash=hash_password("OldPass1!"), role=UserRole.CUSTOMER, email_verified=True)
    db_session.add(user)
    await db_session.commit()

    result = await forgot_password("resetok@test.kz", db_session)
    _, token = result
    await reset_password(token, "NewPass2!", db_session)

    # New password works
    tokens = await login_user(LoginRequest(email="resetok@test.kz", password="NewPass2!"), db_session)
    assert "access_token" in tokens


@pytest.mark.asyncio
async def test_svc_login_wrong_password(db_session):
    from app.services.auth_service import login_user
    from fastapi import HTTPException
    user = User(email="loginwrong@test.kz", password_hash=hash_password("Correct1!"), role=UserRole.CUSTOMER, email_verified=True)
    db_session.add(user)
    await db_session.commit()
    with pytest.raises(HTTPException) as exc:
        await login_user(LoginRequest(email="loginwrong@test.kz", password="WrongPass1!"), db_session)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_svc_login_inactive_user(db_session):
    from app.services.auth_service import login_user
    from fastapi import HTTPException
    user = User(email="inactive@test.kz", password_hash=hash_password("Secure1!"), role=UserRole.CUSTOMER,
                email_verified=True, is_active=False)
    db_session.add(user)
    await db_session.commit()
    with pytest.raises(HTTPException) as exc:
        await login_user(LoginRequest(email="inactive@test.kz", password="Secure1!"), db_session)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_svc_login_unverified(db_session):
    from app.services.auth_service import login_user
    from fastapi import HTTPException
    user = User(email="unverlog@test.kz", password_hash=hash_password("Secure1!"), role=UserRole.CUSTOMER,
                email_verified=False)
    db_session.add(user)
    await db_session.commit()
    with pytest.raises(HTTPException) as exc:
        await login_user(LoginRequest(email="unverlog@test.kz", password="Secure1!"), db_session)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_svc_login_success(db_session):
    from app.services.auth_service import login_user
    user = User(email="loginsvc@test.kz", password_hash=hash_password("Secure1!"), role=UserRole.CUSTOMER, email_verified=True)
    db_session.add(user)
    await db_session.commit()
    tokens = await login_user(LoginRequest(email="loginsvc@test.kz", password="Secure1!"), db_session)
    assert "access_token" in tokens
    assert "refresh_token" in tokens


@pytest.mark.asyncio
async def test_svc_refresh_tokens_invalid(db_session):
    from app.services.auth_service import refresh_tokens
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await refresh_tokens("fake_refresh_token_xyz", db_session)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_svc_refresh_tokens_success(db_session):
    from app.services.auth_service import login_user, refresh_tokens
    user = User(email="refresh2@test.kz", password_hash=hash_password("Secure1!"), role=UserRole.CUSTOMER, email_verified=True)
    db_session.add(user)
    await db_session.commit()
    tokens = await login_user(LoginRequest(email="refresh2@test.kz", password="Secure1!"), db_session)
    new_tokens = await refresh_tokens(tokens["refresh_token"], db_session)
    assert "access_token" in new_tokens


# ── Listing service ───────────────────────────────────────────────────────────

async def _make_vendor_and_listing(db_session, email_suffix: str, bin_num: str):
    """Helper: create user + vendor + approved listing in test DB."""
    user = User(email=f"vendor_{email_suffix}@svc.kz", password_hash=hash_password("pw"),
                role=UserRole.VENDOR, email_verified=True)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    vendor = Vendor(user_id=user.id, business_name="SVC Shop", bin_number=bin_num,
                    address="Addr", latitude=43.2, longitude=76.8, is_approved=True)
    db_session.add(vendor)
    await db_session.commit()
    await db_session.refresh(vendor)
    return vendor


@pytest.mark.asyncio
async def test_svc_create_listing(db_session):
    from app.services.listing_service import create_listing
    vendor = await _make_vendor_and_listing(db_session, "crl", "SVC001")
    data = ListingCreate(
        title="SVC Bread", description="Fresh", original_price=1000, discount_percentage=30,
        quantity_total=5, pickup_window_start=_now() + timedelta(hours=1),
        pickup_window_end=_now() + timedelta(hours=3), allergens=["none"],
        latitude=43.2, longitude=76.8,
    )
    listing = await create_listing(data, vendor, db_session)
    assert listing.id is not None
    assert listing.current_price == 700


@pytest.mark.asyncio
async def test_svc_get_listings_with_category_free(db_session):
    from app.services.listing_service import get_listings
    listings, _ = await get_listings(db_session, category="free", limit=10)
    assert isinstance(listings, list)


@pytest.mark.asyncio
async def test_svc_get_listings_with_category(db_session):
    from app.services.listing_service import get_listings
    listings, _ = await get_listings(db_session, category="bakery", limit=10)
    assert isinstance(listings, list)


@pytest.mark.asyncio
async def test_svc_get_listings_with_geo(db_session):
    from app.services.listing_service import get_listings
    listings, _ = await get_listings(db_session, lat=43.2, lng=76.8, limit=10)
    assert isinstance(listings, list)


@pytest.mark.asyncio
async def test_svc_get_listings_with_cursor(db_session):
    from app.services.listing_service import get_listings
    listings, next_id = await get_listings(db_session, cursor_id=0, limit=5)
    assert isinstance(listings, list)


@pytest.mark.asyncio
async def test_svc_apply_price_decay_old_listing(db_session):
    """apply_price_decay updates listings older than DECAY_START_DAYS."""
    from app.services.listing_service import apply_price_decay
    vendor = await _make_vendor_and_listing(db_session, "decay1", "SVC_DC1")
    listing = Listing(
        vendor_id=vendor.id, title="Old Bread", description="Old",
        original_price=1000, current_price=1000, discount_percentage=30,
        quantity_total=5, quantity_available=5, status=ListingStatus.ACTIVE,
        pickup_window_start=_now() + timedelta(hours=1),
        pickup_window_end=_now() + timedelta(hours=3),
        latitude=43.2, longitude=76.8,
        created_at=_now() - timedelta(days=2),  # old enough to decay
    )
    db_session.add(listing)
    await db_session.commit()
    updated = await apply_price_decay(db_session)
    assert updated >= 1


@pytest.mark.asyncio
async def test_svc_apply_price_decay_expired_listing(db_session):
    """apply_price_decay moves expired listings to COMPOST."""
    from app.services.listing_service import apply_price_decay
    vendor = await _make_vendor_and_listing(db_session, "decay2", "SVC_DC2")
    listing = Listing(
        vendor_id=vendor.id, title="Expired Food", description="Old",
        original_price=500, current_price=500, discount_percentage=10,
        quantity_total=3, quantity_available=3, status=ListingStatus.ACTIVE,
        pickup_window_start=_now() - timedelta(hours=4),
        pickup_window_end=_now() - timedelta(hours=1),  # already expired
        latitude=43.2, longitude=76.8,
    )
    db_session.add(listing)
    await db_session.commit()
    updated = await apply_price_decay(db_session)
    assert updated >= 1


# ── Order service ─────────────────────────────────────────────────────────────

async def _setup_order_scenario(db_session, suffix: str):
    """Return (customer, vendor_user, listing) for order tests."""
    customer = User(email=f"cust_{suffix}@svc.kz", password_hash=hash_password("pw"),
                    role=UserRole.CUSTOMER, email_verified=True)
    db_session.add(customer)
    await db_session.commit()
    await db_session.refresh(customer)

    vendor_user = User(email=f"vend_{suffix}@svc.kz", password_hash=hash_password("pw"),
                       role=UserRole.VENDOR, email_verified=True)
    db_session.add(vendor_user)
    await db_session.commit()
    await db_session.refresh(vendor_user)

    vendor = Vendor(user_id=vendor_user.id, business_name=f"Shop {suffix}", bin_number=f"ORD{suffix}",
                    address="A", latitude=43.2, longitude=76.8, is_approved=True)
    db_session.add(vendor)
    await db_session.commit()
    await db_session.refresh(vendor)

    listing = Listing(
        vendor_id=vendor.id, title=f"Item {suffix}", description="D",
        original_price=2000, current_price=1200, discount_percentage=40,
        quantity_total=10, quantity_available=10, status=ListingStatus.ACTIVE,
        pickup_window_start=_now() + timedelta(hours=1),
        pickup_window_end=_now() + timedelta(hours=5),
        latitude=43.2, longitude=76.8,
    )
    db_session.add(listing)
    await db_session.commit()
    await db_session.refresh(listing)
    return customer, vendor_user, listing


@pytest.mark.asyncio
async def test_svc_create_order_success(db_session):
    from app.services.order_service import create_order
    customer, _, listing = await _setup_order_scenario(db_session, "ord1")
    data = OrderCreateRequest(items=[OrderItemCreate(listing_id=listing.id, quantity=2)])
    order = await create_order(data, customer, db_session)
    assert order.id is not None
    assert order.total_amount == listing.current_price * 2
    assert order.status == OrderStatus.PENDING


@pytest.mark.asyncio
async def test_svc_create_order_not_found(db_session):
    from app.services.order_service import create_order
    from fastapi import HTTPException
    customer = User(email="nolisting@svc.kz", password_hash=hash_password("pw"), role=UserRole.CUSTOMER, email_verified=True)
    db_session.add(customer)
    await db_session.commit()
    data = OrderCreateRequest(items=[OrderItemCreate(listing_id=99999, quantity=1)])
    with pytest.raises(HTTPException) as exc:
        await create_order(data, customer, db_session)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_svc_create_order_insufficient_stock(db_session):
    from app.services.order_service import create_order
    from fastapi import HTTPException
    customer, _, listing = await _setup_order_scenario(db_session, "ord2")
    data = OrderCreateRequest(items=[OrderItemCreate(listing_id=listing.id, quantity=999)])
    with pytest.raises(HTTPException) as exc:
        await create_order(data, customer, db_session)
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_svc_create_order_empty_items(db_session):
    from app.services.order_service import create_order
    from fastapi import HTTPException
    customer = User(email="emptyord@svc.kz", password_hash=hash_password("pw"), role=UserRole.CUSTOMER, email_verified=True)
    db_session.add(customer)
    await db_session.commit()
    data = OrderCreateRequest(items=[])
    with pytest.raises(HTTPException) as exc:
        await create_order(data, customer, db_session)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_svc_update_order_status_not_found(db_session):
    from app.services.order_service import update_order_status
    from fastapi import HTTPException
    admin = User(email="admord@svc.kz", password_hash=hash_password("pw"), role=UserRole.ADMIN, email_verified=True)
    db_session.add(admin)
    await db_session.commit()
    with pytest.raises(HTTPException) as exc:
        await update_order_status(99999, OrderStatusUpdate(status=OrderStatus.CONFIRMED), admin, db_session)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_svc_update_order_status_success(db_session):
    from app.services.order_service import create_order, update_order_status
    customer, _, listing = await _setup_order_scenario(db_session, "ord3")
    data = OrderCreateRequest(items=[OrderItemCreate(listing_id=listing.id, quantity=1)])
    order = await create_order(data, customer, db_session)

    admin = User(email="admin_ord@svc.kz", password_hash=hash_password("pw"), role=UserRole.ADMIN, email_verified=True)
    db_session.add(admin)
    await db_session.commit()

    updated = await update_order_status(order.id, OrderStatusUpdate(status=OrderStatus.CONFIRMED), admin, db_session)
    assert updated.status == OrderStatus.CONFIRMED
