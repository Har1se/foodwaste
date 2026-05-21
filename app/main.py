import re
import time
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.logging_config import configure_logging
from app.database import AsyncSessionLocal, create_db_and_tables, engine
from app.core.redis import get_redis, close_redis

# Import all models so SQLModel picks them up for table creation
from app.models import *  # noqa: F401, F403
from app.models.log import SystemLog

from app.routers import auth, listings, orders, vendors, admin, payments, jobs
from app.routers import auctions, drivers
from app.demo_seed import auto_seed
from app.models.listing import Listing
from sqlmodel import select, func

logger = configure_logging(debug=settings.DEBUG)

# Paths that are too noisy to log (health checks, Swagger assets)
_SKIP_LOG_PATHS = frozenset({
    "/health", "/docs", "/redoc", "/openapi.json", "/favicon.ico",
})

# Mask sensitive fields in request body before logging
_SENSITIVE_RE = re.compile(
    r'"(password|token|secret|api_key|authorization)[^"]*"\s*:\s*"[^"]*"',
    re.IGNORECASE,
)


def _client_ip(request: Request) -> str:
    """Extract real IP, honouring X-Forwarded-For from trusted proxies."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()[:45]
    return (request.client.host if request.client else "unknown")[:45]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────────────────
    logger.info("RescueBite API starting — environment: %s", settings.ENVIRONMENT)

    await create_db_and_tables()
    logger.info("Database tables ready")

    await get_redis()
    logger.info("Redis connected")

    try:
        async with AsyncSessionLocal() as session:
            count = await session.scalar(select(func.count()).select_from(Listing))
            if count == 0:
                logger.info("Database empty — seeding demo data…")
                n = await auto_seed(session)
                logger.info("Seeded %d demo listings", n)
            else:
                logger.info("Database has %d listings — skipping seed", count)
    except Exception as exc:
        logger.warning("Auto-seed skipped: %s", exc)

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    await close_redis()
    await engine.dispose()
    logger.info("RescueBite API shutdown complete")


app = FastAPI(
    title="RescueBite API",
    description=(
        "Food Waste Reduction Marketplace — REST API\n\n"
        "Built with FastAPI + SQLModel + PostgreSQL\n\n"
        "**Auth flow:** Register → Login → Use Bearer token → Refresh → Logout"
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)


# ── Security headers ──────────────────────────────────────────────────────────
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=()"
    if settings.ENVIRONMENT == "production":
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )
    return response


# ── Request / response logger ─────────────────────────────────────────────────
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    path = request.url.path
    if path in _SKIP_LOG_PATHS or path.startswith(("/docs", "/redoc")):
        return await call_next(request)

    start = time.perf_counter()

    # Decode JWT for user context (no DB hit needed)
    user_id: int | None = None
    user_role: str | None = None
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        from app.core.security import decode_access_token
        payload = decode_access_token(auth_header[7:])
        if payload:
            user_id = payload.get("user_id")
            user_role = payload.get("role")

    # Capture JSON body for mutating requests (Starlette caches it after first read)
    body_str: str | None = None
    if request.method in ("POST", "PATCH", "PUT"):
        if "application/json" in request.headers.get("content-type", ""):
            try:
                raw = await request.body()
                body_str = _SENSITIVE_RE.sub(
                    r'"\1": "***"',
                    raw.decode("utf-8", errors="replace")[:2000],
                )
            except Exception:
                pass

    error_msg: str | None = None
    error_tb: str | None = None
    status_code = 500

    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception as exc:
        error_msg = str(exc)[:1000]
        error_tb = traceback.format_exc()[:5000]
        logger.error("Unhandled exception on %s %s: %s", request.method, path, exc)
        raise
    finally:
        duration_ms = int((time.perf_counter() - start) * 1000)
        level = (
            "error" if status_code >= 500
            else "warning" if status_code >= 400
            else "info"
        )

        if level != "info":
            log_fn = logger.error if level == "error" else logger.warning
            log_fn(
                "%s %s → %d (%dms) user_id=%s",
                request.method, path, status_code, duration_ms, user_id,
            )

        try:
            async with AsyncSessionLocal() as db:
                db.add(SystemLog(
                    user_id=user_id,
                    role=user_role,
                    endpoint=path[:255],
                    method=request.method,
                    ip_address=_client_ip(request),
                    user_agent=request.headers.get("user-agent", "")[:500],
                    request_body=body_str,
                    response_status=status_code,
                    error_message=error_msg,
                    error_traceback=error_tb,
                    duration_ms=duration_ms,
                    level=level,
                ))
                await db.commit()
        except Exception as log_exc:
            logger.warning("Failed to persist system log: %s", log_exc)

    return response


# ── Global error handler ──────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        "Unhandled exception on %s %s: %s\n%s",
        request.method, request.url.path, exc, traceback.format_exc(),
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(listings.router)
app.include_router(orders.router)
app.include_router(vendors.router)
app.include_router(admin.router)
app.include_router(payments.router)
app.include_router(jobs.router)
app.include_router(auctions.router)
app.include_router(drivers.router)


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "service": "rescuebite-api", "version": "1.0.0"}
