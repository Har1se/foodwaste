# RescueBite API

**Food Waste Reduction Marketplace** — FastAPI + SQLModel + PostgreSQL + Redis

---

## Quick Start (Docker)

```bash
git clone https://github.com/Har1se/foodwaste.git
cd foodwaste

docker compose up --build
```

| URL | Description |
|---|---|
| http://localhost:8000/docs | Swagger UI (interactive) |
| http://localhost:8000/redoc | ReDoc |
| http://localhost:8000/health | Health check |

Tables are created automatically on startup.

---

## Architecture

| Layer | Technology | Purpose |
|---|---|---|
| Framework | FastAPI 0.111 | Async, auto OpenAPI docs, Pydantic v2 validation |
| ORM | SQLModel 0.0.38 | SQLAlchemy + Pydantic — single source of truth |
| Database | PostgreSQL 16 | ACID transactions, CHECK constraints, enums |
| Cache | Redis 7 | Rate limiting, refresh tokens, stock reservation |
| Tasks | Celery 5 + Beat | Price decay cron every 72h |
| Auth | JWT (python-jose) | 15-min access token + 7-day opaque refresh token |

---

## Environment Variables

Copy `.env.example` to `.env`:

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | ✅ | `postgresql+asyncpg://user:pass@host/db` |
| `REDIS_URL` | ✅ | `redis://localhost:6379` |
| `SECRET_KEY` | ✅ | Min 32 chars — JWT signing key |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | — | Default: 15 |
| `REFRESH_TOKEN_EXPIRE_DAYS` | — | Default: 7 |

App refuses to start if `SECRET_KEY` < 32 characters.

---

## Auth Flow

```
POST /auth/register   →  create account (customer / vendor / admin)
POST /auth/login      →  receive access_token + refresh_token
GET  /auth/me         →  Bearer {access_token}
PATCH /auth/me        →  update own profile
PATCH /auth/me/password → change password
DELETE /auth/me       →  deactivate own account
POST /auth/refresh    →  rotate refresh_token → new tokens
POST /auth/logout     →  revoke refresh_token
```

**RBAC Roles:** `customer` | `vendor` | `driver` | `admin`

| Error | Reason |
|---|---|
| `401` | Invalid or expired access token |
| `403` | Missing token or insufficient role |
| `429` | Rate limit exceeded (5 logins/min, 3 registers/hour per IP) |

---

## Core Features

### 1. Food State Machine
```
ACTIVE → DISCOUNTED   (days_active ≥ 30, 10% price decay every 72h via Celery)
DISCOUNTED → FREE     (current_price hits 0)
FREE → COMPOST        (pickup_window_end passed)
any → SOLD_OUT        (quantity_available = 0)
```
Manual trigger: `POST /admin/trigger-price-decay`

### 2. Allergen Parser
```json
POST /listings/allergen-check
{
  "ingredients": ["wheat flour", "milk", "sugar"],
  "user_allergens": ["gluten", "dairy"]
}
→ { "safe": false, "flagged_ingredients": ["wheat flour", "milk"], "message": "WARNING: ..." }
```
Supports Russian and English ingredient names.

### 3. Atomic Order (two-layer oversell prevention)
```
POST /orders
  1. Redis soft lock (5-min TTL reservation)
  2. SELECT FOR UPDATE — DB-level row lock
  3. Decrement quantity_available atomically
  → 409 if out of stock at either layer
```

### 4. Audit Log
Every admin action writes to `audit_logs` table: table, record_id, actor, old/new data.

---

## API Endpoints

### Auth — `/auth`
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | — | Register new account |
| POST | `/auth/login` | — | Login, get tokens |
| POST | `/auth/refresh` | — | Rotate refresh token |
| POST | `/auth/logout` | — | Revoke refresh token |
| GET | `/auth/me` | Bearer | Get own profile |
| PATCH | `/auth/me` | Bearer | Update full_name / phone / allergen_profile |
| PATCH | `/auth/me/password` | Bearer | Change password (requires current password) |
| DELETE | `/auth/me` | Bearer | Deactivate own account (soft delete) |

### Listings — `/listings`
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/listings` | — | Browse active listings. Params: `cursor`, `limit`, `lat`, `lng` |
| POST | `/listings` | Vendor | Create listing (vendor must be approved) |
| GET | `/listings/{id}` | — | Get single listing |
| POST | `/listings/allergen-check` | Bearer | Check ingredients against allergen profile |

### Orders — `/orders`
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/orders` | Customer | Place order `{"items":[{"listing_id":1,"quantity":2}]}` |
| GET | `/orders` | Bearer | My orders (cursor paginated) |
| GET | `/orders/{id}` | Bearer | Get single order |
| PATCH | `/orders/{id}/status` | Bearer | Update order status |

### Vendors — `/vendors`
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/vendors/register` | Vendor | Submit vendor profile for approval |
| GET | `/vendors/me` | Vendor | My vendor profile |
| GET | `/vendors/{id}` | — | Get vendor by ID |

### Admin — `/admin`
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/admin/stats` | Admin | Platform statistics |
| GET | `/admin/users` | Admin | List users. Params: `role`, `is_active`, `cursor`, `limit` |
| GET | `/admin/users/{id}` | Admin | Get user by ID |
| PATCH | `/admin/users/{id}` | Admin | Update user (role, full_name, phone, is_active) |
| DELETE | `/admin/users/{id}` | Admin | Hard delete (blocked if user has orders/vendor profile) |
| PATCH | `/admin/users/{id}/suspend` | Admin | Quick suspend toggle (`?is_active=false`) |
| GET | `/admin/vendors` | Admin | List vendors. Param: `is_approved` |
| PATCH | `/admin/vendors/{id}/approve` | Admin | Approve/reject `{"action":"approve"}` |
| DELETE | `/admin/vendors/{id}` | Admin | Delete vendor + listings (blocked if active orders) |
| GET | `/admin/listings` | Admin | All listings. Params: `status`, `vendor_id`, `cursor` |
| PATCH | `/admin/listings/{id}` | Admin | Edit listing fields or force status change |
| DELETE | `/admin/listings/{id}` | Admin | Hard delete (blocked if has order items) |
| GET | `/admin/orders` | Admin | All orders. Params: `status`, `vendor_id`, `customer_id` |
| GET | `/admin/orders/{id}` | Admin | Get any order by ID |
| POST | `/admin/trigger-price-decay` | Admin | Manually trigger price decay |

### System
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` | — | Service health check |

---

## Project Structure

```
rescuebite-api/
├── app/
│   ├── main.py              # FastAPI app factory, lifespan events
│   ├── config.py            # Pydantic Settings (validates env vars at boot)
│   ├── database.py          # Async engine, get_session()
│   ├── models/              # SQLModel table definitions (user, vendor, listing, order)
│   ├── schemas/             # Pydantic request/response schemas
│   ├── routers/             # HTTP layer — auth, listings, orders, vendors, admin
│   ├── services/            # Business logic — auth_service, listing_service, order_service
│   ├── tasks/               # Celery tasks — price decay
│   └── core/                # Security (JWT/bcrypt), Redis, RBAC deps, pagination
├── tests/                   # Pytest async suite (33 tests, SQLite in-memory)
├── docker-compose.yml       # api + db + redis + worker + beat
├── Dockerfile
└── requirements.txt
```

---

## Running Tests

```bash
# Uses SQLite automatically — no PostgreSQL or Redis needed
pytest tests/ -v

# With coverage
pytest tests/ -v --cov=app --cov-report=term-missing
```

33 tests, 1 skipped (SELECT FOR UPDATE — PostgreSQL only).

---

## Security

- **Passwords**: bcrypt with random salt
- **JWT**: HS256, 15-min access tokens; refresh tokens are opaque hex stored in Redis
- **Rate limiting**: Redis counter — 5 login/min, 3 register/hour per IP
- **RBAC**: Role verified server-side from DB on every request
- **Audit log**: Every admin write action is logged to `audit_logs`
- **No secrets in code**: All config via environment variables, validated at startup
