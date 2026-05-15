# RescueBite API

**Food Waste Reduction Marketplace** — production-grade backend + frontend system.

Vendors list surplus food at discounted prices. Customers buy it before it expires.  
Everyone wins: less waste, cheaper meals.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI 0.111 (async) |
| ORM | SQLModel + SQLAlchemy (async) |
| Database | PostgreSQL 16 |
| Cache / Queue Broker | Redis 7 |
| Background Workers | Celery 5.3 + Celery Beat |
| Auth | JWT (HS256) + Redis-backed refresh tokens |
| Password | bcrypt |
| Frontend | React 18 + Vite + Tailwind CSS |
| Tests | pytest + pytest-asyncio |
| Containerization | Docker + Docker Compose |

---

## Quick Start (Docker)

```bash
# 1. Clone and enter
git clone <repo-url>
cd rescuebite-api

# 2. Configure environment
cp .env.example .env
# Edit .env — set SECRET_KEY, SMTP_*, etc.

# 3. Start all services
docker compose up --build

# 4. Run migrations
docker compose exec api alembic upgrade head

# API:     http://localhost:8000
# Swagger: http://localhost:8000/docs
```

---

## Quick Start (Local Development)

### Backend

```bash
# Python 3.11+ required
pip install -r requirements.txt

# Start PostgreSQL + Redis
docker compose up db redis -d

cp .env.example .env   # edit as needed

alembic upgrade head

uvicorn app.main:app --reload --port 8000

# New terminal — Celery worker
celery -A app.tasks.celery_app worker --loglevel=info

# New terminal — Celery Beat
celery -A app.tasks.celery_app beat --loglevel=info
```

### Frontend

```bash
cd frontend
npm install
npm run dev   # http://localhost:3000
```

---

## Environment Variables

Copy `.env.example` and fill in the values:

```env
DATABASE_URL=postgresql+asyncpg://rescuebite:rescuebite@localhost:5432/rescuebite_db
REDIS_URL=redis://localhost:6379/0

# REQUIRED: at least 32 characters
SECRET_KEY=your-very-long-random-secret-key-here-at-least-32-chars

ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Email (e.g. Resend, SendGrid, Brevo)
SMTP_HOST=smtp.resend.com
SMTP_PORT=587
SMTP_USER=resend
SMTP_PASSWORD=your-api-key
SMTP_FROM=noreply@rescuebite.kz

FRONTEND_URL=http://localhost:3000

ENVIRONMENT=development
DEBUG=true
ALLOWED_ORIGINS=["http://localhost:3000","http://localhost:8000"]
```

---

## API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI contract**: `openapi.yaml` in project root

---

## Authentication Flow

```
Register → OTP to email → POST /auth/verify-email → Login → Bearer token → Refresh → Logout
```

All protected endpoints require `Authorization: Bearer <access_token>`.

---

## User Roles & Permissions

| Role | Capabilities |
|------|-------------|
| `customer` | Browse listings, place orders, pay, view own orders |
| `vendor` | Manage own listings + view vendor orders |
| `admin` | Full CRUD on all resources + stats + job control |

---

## Key Business Workflows

### 1. Food State Machine (Celery Beat — every 72h)
```
ACTIVE → DISCOUNTED (days_active ≥ 30, 10% price decay)
DISCOUNTED → FREE (price hits 0)
FREE → COMPOST (pickup_window_end passed)
any → SOLD_OUT (quantity_available = 0)
```

### 2. Allergen Parser
`POST /listings/allergen-check` → detects allergens in ingredient list against user profile.

### 3. Atomic Order (2-layer oversell prevention)
1. Redis soft lock (5-min TTL)
2. PostgreSQL `SELECT FOR UPDATE` row lock + atomic decrement

### 4. Payment Flow
```
POST /payments/{order_id}/initiate         → Kaspi URL
POST /payments/{order_id}/simulate-success → dev/demo mode
```

---

## Email Notifications (4 real events)

| Event | Trigger |
|-------|---------|
| Email verification OTP | User registers |
| Order confirmation + pickup token | Order placed |
| Vendor approved | Admin approves vendor |
| Password reset link | User requests reset |

All emails sent via Celery queue — non-blocking API.

---

## Running Tests

```bash
pytest tests/ -v

# With coverage
pytest tests/ -v --cov=app --cov-report=term-missing
```

Uses SQLite in-memory + mocked Redis/Celery — no external services needed.

---

## Database Migrations

```bash
alembic upgrade head      # apply all
alembic current           # show current revision
alembic history           # show migration history
alembic revision --autogenerate -m "description"  # new migration
```

---

## Background Jobs

```bash
# Worker
celery -A app.tasks.celery_app worker --loglevel=info

# Beat scheduler
celery -A app.tasks.celery_app beat --loglevel=info
```

| Job | Schedule | Task |
|-----|----------|------|
| price_decay_task | Every 72 hours | Apply price decay to aging listings |

Monitor via API (admin token required):
```
GET  /jobs/status        — queue overview, workers, Beat schedule
GET  /jobs/{task_id}     — specific task result
POST /admin/trigger-price-decay  — manual trigger
```

---

## Frontend Pages

| Path | Description | Role |
|------|-------------|------|
| `/` | Marketplace — browse food listings | Public |
| `/login` | Login | Public |
| `/register` | Register (customer or vendor) | Public |
| `/verify-email` | OTP verification | Public |
| `/forgot-password` | Request password reset | Public |
| `/reset-password` | Set new password | Public |
| `/orders` | My orders + Kaspi payment | Customer |
| `/vendor` | Vendor dashboard — listings + orders | Vendor |
| `/admin` | Admin panel — full management | Admin |

---

## Docker Compose Services

| Service | Port | Description |
|---------|------|-------------|
| `api` | 8000 | FastAPI application |
| `db` | 5432 | PostgreSQL 16 |
| `redis` | 6379 | Redis 7 |
| `worker` | — | Celery worker |
| `beat` | — | Celery Beat scheduler |

---

## Project Structure

```
rescuebite-api/
├── app/
│   ├── main.py              # FastAPI factory + lifespan
│   ├── config.py            # Pydantic Settings (validates on boot)
│   ├── database.py          # Async SQLAlchemy engine
│   ├── core/
│   │   ├── dependencies.py  # JWT auth + RBAC decorators
│   │   ├── security.py      # bcrypt + JWT token creation
│   │   ├── redis.py         # Rate limiting + token storage
│   │   └── pagination.py    # Cursor-based pagination
│   ├── models/              # SQLModel ORM (User, Vendor, Listing, Order, Payment)
│   ├── schemas/             # Pydantic request/response schemas
│   ├── routers/
│   │   ├── auth.py          # Register, verify, login, refresh, logout, profile
│   │   ├── listings.py      # Browse, create, update, delete, allergen-check
│   │   ├── orders.py        # Place, list, get, update status
│   │   ├── vendors.py       # Register vendor, get profile
│   │   ├── payments.py      # Kaspi Pay integration + simulation
│   │   ├── jobs.py          # Celery queue visibility
│   │   └── admin.py         # Full admin CRUD + stats + price decay trigger
│   ├── services/            # Business logic layer
│   └── tasks/               # Celery tasks (email, price decay)
├── frontend/                # React 18 + Vite + Tailwind CSS
│   └── src/
│       ├── api/client.js    # Axios with auto-refresh interceptor
│       ├── contexts/        # AuthContext
│       ├── pages/           # Home, Login, Register, Orders, Vendor, Admin
│       └── components/      # Navbar, ListingCard, Modal
├── migrations/              # Alembic migration history
├── tests/                   # pytest async test suite
├── openapi.yaml             # Complete OpenAPI 3.1 contract
├── docker-compose.yml
├── Dockerfile
└── .env.example
```

---

## Postman Collection

Import `RescueBite.postman_collection.json` for all endpoints pre-configured.

---

## Defense Demo Flow

1. `docker compose up` → wait for all green
2. `alembic upgrade head`
3. Open Swagger: http://localhost:8000/docs
4. Open Frontend: http://localhost:3000
5. Register → receive OTP email → verify → Login
6. Browse marketplace, place order, simulate Kaspi payment, show pickup token
7. Switch to vendor account → create listing
8. Switch to admin → approve vendor, view stats, trigger price decay
9. Show Celery queue: `GET /jobs/status`
10. `pytest tests/ -v` — all green
