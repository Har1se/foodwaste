import os
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# ── Override DATABASE_URL BEFORE any app imports ──────────────────────────────
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"

# ── Redis mock MUST happen before app import ──────────────────────────────────
_mock_store: dict = {}

async def mock_check_rate_limit(key, max_requests, window_seconds):
    pass  # no-op for tests

async def mock_store_refresh_token(user_id, token, expires_days):
    _mock_store[f"refresh:{token}"] = str(user_id)

async def mock_get_user_id_from_refresh_token(token):
    val = _mock_store.get(f"refresh:{token}")
    return int(val) if val else None

async def mock_revoke_refresh_token(token):
    _mock_store.pop(f"refresh:{token}", None)

import app.core.redis as redis_module
redis_module.check_rate_limit = mock_check_rate_limit
redis_module.store_refresh_token = mock_store_refresh_token
redis_module.get_user_id_from_refresh_token = mock_get_user_id_from_refresh_token
redis_module.revoke_refresh_token = mock_revoke_refresh_token

import app.services.auth_service as auth_svc
auth_svc.store_refresh_token = mock_store_refresh_token
auth_svc.get_user_id_from_refresh_token = mock_get_user_id_from_refresh_token
auth_svc.revoke_refresh_token = mock_revoke_refresh_token

# ── Mock Celery email tasks (no broker in tests) ──────────────────────────────

class _NoOpTask:
    def delay(self, *args, **kwargs):
        pass

import app.tasks.email_tasks as email_tasks_module
email_tasks_module.send_verification_email = _NoOpTask()
email_tasks_module.send_password_reset_email = _NoOpTask()
email_tasks_module.send_order_confirmation_email = _NoOpTask()
email_tasks_module.send_vendor_approved_email = _NoOpTask()
email_tasks_module.send_auction_won_email = _NoOpTask()
email_tasks_module.send_auction_lost_email = _NoOpTask()
email_tasks_module.send_new_listing_email = _NoOpTask()
email_tasks_module.send_driver_assignment_email = _NoOpTask()

# Also patch the router-level imports
import app.routers.auth as auth_router_module
auth_router_module.send_verification_email = _NoOpTask()
auth_router_module.send_password_reset_email = _NoOpTask()

import app.routers.orders as orders_router_module
orders_router_module.send_order_confirmation_email = _NoOpTask()

import app.routers.admin as admin_router_module
admin_router_module.send_vendor_approved_email = _NoOpTask()

import app.routers.listings as listings_router_module
listings_router_module.send_new_listing_email = _NoOpTask()

import app.routers.drivers as drivers_router_module
drivers_router_module.send_driver_assignment_email = _NoOpTask()

# ── Auto-verify users in tests (skip email verification flow) ─────────────────
_original_register_user = auth_svc.register_user

async def _auto_verified_register_user(data, session):
    user, otp_code = await _original_register_user(data, session)
    user.email_verified = True
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user, otp_code

auth_svc.register_user = _auto_verified_register_user

# ── Now import app ────────────────────────────────────────────────────────────
from app.main import app
from app.database import get_session
from app.models import *  # noqa

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

async def override_get_session():
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

app.dependency_overrides[get_session] = override_get_session

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
    await test_engine.dispose()
    if os.path.exists("test.db"):
        try:
            os.remove("test.db")
        except PermissionError:
            pass

@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

@pytest_asyncio.fixture
async def db_session():
    async with TestSessionLocal() as session:
        yield session

# ── Mock Redis stock reservation ──────────────────────────────────────────────
async def mock_reserve_stock(listing_id, quantity, ttl_seconds=300):
    pass  # no-op for tests

async def mock_release_stock_reservation(listing_id, quantity):
    pass  # no-op for tests

import app.services.order_service as order_svc
order_svc.reserve_stock = mock_reserve_stock
order_svc.release_stock_reservation = mock_release_stock_reservation
