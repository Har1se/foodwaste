import asyncio
import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

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

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
    if os.path.exists("test.db"):
        os.remove("test.db")

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
