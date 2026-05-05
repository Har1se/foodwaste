from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import create_db_and_tables
from app.core.redis import get_redis, close_redis

# Import all models so SQLModel picks them up for table creation
from app.models import *  # noqa: F401, F403

from app.routers import auth, listings, orders, vendors, admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────────────────
    print("🚀 RescueBite API starting...")

    # Validate config (Pydantic already validates on import, but re-confirm)
    print(f"   Environment: {settings.ENVIRONMENT}")
    print(f"   Database: {settings.DATABASE_URL.split('@')[-1]}")

    # Init DB tables (dev only — prod uses Alembic)
    await create_db_and_tables()
    print("   ✅ Database tables ready")

    # Connect to Redis
    await get_redis()
    print("   ✅ Redis connected")

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    await close_redis()
    print("👋 RescueBite API shutdown complete")


app = FastAPI(
    title="RescueBite API",
    description=(
        "Food Waste Reduction Marketplace — REST API\n\n"
        "Built with FastAPI + SQLModel + PostgreSQL 15\n\n"
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
    allow_origins=settings.ALLOWED_ORIGINS,  # No wildcard in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global error handlers ─────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
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


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "service": "rescuebite-api", "version": "1.0.0"}
