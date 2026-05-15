from typing import Optional

import redis.asyncio as aioredis
from fastapi import HTTPException
from app.config import settings

_redis: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = await aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


async def close_redis():
    global _redis
    if _redis:
        await _redis.close()
        _redis = None


# ── Rate Limiting (token bucket) ──────────────────────────────────────────────

async def check_rate_limit(key: str, max_requests: int, window_seconds: int):
    if not settings.ENABLE_RATE_LIMIT:
        return
    r = await get_redis()
    current = await r.incr(key)
    if current == 1:
        await r.expire(key, window_seconds)
    if current > max_requests:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")


# ── Refresh Token Storage ──────────────────────────────────────────────────────

async def store_refresh_token(user_id: int, token: str, expires_days: int):
    r = await get_redis()
    key = f"refresh:{token}"
    await r.setex(key, expires_days * 86400, str(user_id))


async def get_user_id_from_refresh_token(token: str) -> Optional[int]:
    r = await get_redis()
    key = f"refresh:{token}"
    val = await r.get(key)
    return int(val) if val else None


async def revoke_refresh_token(token: str):
    r = await get_redis()
    await r.delete(f"refresh:{token}")


# ── Stock Reservation (checkout) ──────────────────────────────────────────────

async def reserve_stock(listing_id: int, quantity: int, ttl_seconds: int = 300) -> bool:
    """Reserve stock in Redis during checkout (5 min TTL)."""
    r = await get_redis()
    key = f"reserve:{listing_id}"
    # Atomic increment
    current = await r.incrby(key, quantity)
    if current == quantity:
        await r.expire(key, ttl_seconds)
    return True


async def release_stock_reservation(listing_id: int, quantity: int):
    r = await get_redis()
    key = f"reserve:{listing_id}"
    await r.decrby(key, quantity)
