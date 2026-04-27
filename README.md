# 🥗 RescueBite API

**Food Waste Reduction Marketplace** — FastAPI + SQLModel + PostgreSQL 15

---

## 🚀 Quick Start (Docker)

```bash
# 1. Clone and enter the project
git clone <repo-url>
cd rescuebite-api

# 2. Launch all services
docker compose up --build

# 3. API is live at:
#    Swagger UI  → http://localhost:8000/docs
#    ReDoc       → http://localhost:8000/redoc
#    Health      → http://localhost:8000/health
```

That's it. The app auto-creates all DB tables on startup.

---

## 🏗️ Architecture

| Layer | Technology | Why |
|---|---|---|
| Framework | FastAPI 0.111 | Native async, auto OpenAPI docs, Pydantic validation |
| ORM | SQLModel 0.0.18 | SQLAlchemy + Pydantic combined — single source of truth |
| Database | PostgreSQL 15 | ACID for financial transactions, CHECK constraints |
| Cache | Redis 7 | Rate limiting, refresh token store, stock reservation |
| Task Queue | Celery 5 + Beat | Price decay cron every 72h, background notifications |
| Auth | JWT (python-jose) | Access token 15min + Refresh token 7 days (Redis-backed) |

---

## 🔐 Auth Flow

```
POST /auth/register  →  create account
POST /auth/login     →  get access_token + refresh_token
GET  /auth/me        →  use Bearer {access_token}
POST /auth/refresh   →  exchange refresh_token → new tokens (rotation)
POST /auth/logout    →  revoke refresh_token
```

**RBAC Roles:** `customer` | `vendor` | `driver` | `admin`

- Wrong role → `403 Forbidden`
- Missing token → `403` (HTTPBearer)
- Invalid/expired token → `401 Unauthorized`

---

## 🎯 RescueBite Core Features (Sprint 1)

### 1. Food State Machine
```
ACTIVE → DISCOUNTED (days_active ≥ 30, 10% decay every 72h via Celery)
DISCOUNTED → FREE (price hits 0)
FREE → COMPOST (pickup_window_end passed)
ACTIVE/DISCOUNTED → SOLD_OUT (quantity_available = 0)
```

### 2. Allergen Parser
```
POST /listings/allergen-check
{
  "ingredients": ["wheat flour", "milk", "sugar"],
  "user_allergens": ["gluten", "dairy"]
}
→ { "safe": false, "flagged_ingredients": ["wheat flour", "milk"], ... }
```

### 3. Atomic Order (SELECT FOR UPDATE)
```
POST /orders  →  locks listings, decrements stock atomically
               →  409 if stock changes between check and lock
               →  all items must be from same vendor
```

---

## 📁 Project Structure

```
rescuebite-api/
├── app/
│   ├── main.py              # FastAPI factory, lifespan events
│   ├── config.py            # Pydantic Settings (validates on startup)
│   ├── database.py          # Async engine, get_session()
│   ├── models/              # SQLModel table definitions
│   ├── schemas/             # Pydantic request/response schemas
│   ├── routers/             # HTTP layer (thin — no business logic)
│   ├── services/            # Business logic (testable in isolation)
│   ├── tasks/               # Celery async tasks
│   └── core/                # Security, Redis, RBAC, pagination
├── migrations/              # Alembic
├── tests/                   # Pytest async test suite
├── docker-compose.yml       # api + db + redis + worker + beat
└── .github/workflows/ci.yml # CI: lint + test + docker build
```

---

## 🧪 Running Tests

```bash
# Install test deps
pip install -r requirements.txt aiosqlite

# Run all tests
pytest tests/ -v

# With coverage
pytest tests/ -v --cov=app --cov-report=term-missing
```

---

## 🔑 Environment Variables

Copy `.env.example` to `.env` and fill in real values:

```bash
cp .env.example .env
```

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | ✅ | PostgreSQL async URL |
| `REDIS_URL` | ✅ | Redis URL |
| `SECRET_KEY` | ✅ | Min 32 chars — JWT signing |
| `KASPI_API_KEY` | ✅ | Kaspi Pay integration |
| `S3_ACCESS_KEY` | ✅ | MinIO/S3 for photos |

App **refuses to start** if `SECRET_KEY` is shorter than 32 characters.

---

## 🛡️ Security

- **Passwords**: bcrypt with salt (passlib)
- **JWT**: HS256, 15-min access tokens, 7-day refresh tokens stored in Redis
- **Rate limiting**: Redis token bucket — 5 login/min, 3 register/hour per IP
- **RBAC**: Role checked server-side from DB, not from JWT payload
- **CORS**: Explicit origins only — no wildcard `*`
- **Audit log**: Append-only `audit_logs` table for all state changes
- **No hardcoded secrets**: Pydantic Settings validates all env vars at boot

---

## 📋 API Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | — | Register (customer/vendor) |
| POST | `/auth/login` | — | Login → tokens |
| POST | `/auth/refresh` | — | Rotate refresh token |
| POST | `/auth/logout` | — | Revoke refresh token |
| GET | `/auth/me` | Bearer | My profile |
| GET | `/listings` | — | Browse listings (cursor paged) |
| POST | `/listings` | Vendor | Create listing |
| GET | `/listings/{id}` | — | Get listing |
| POST | `/listings/allergen-check` | Bearer | Allergen parser |
| POST | `/orders` | Customer | Place order (atomic) |
| GET | `/orders` | Bearer | My orders |
| PATCH | `/orders/{id}/status` | Bearer | Update order status |
| POST | `/vendors/register` | Vendor | Submit vendor profile |
| GET | `/vendors/me` | Vendor | My vendor profile |
| GET | `/admin/stats` | Admin | Platform statistics |
| PATCH | `/admin/vendors/{id}/approve` | Admin | Approve/reject vendor |
| PATCH | `/admin/users/{id}/suspend` | Admin | Suspend user |
| POST | `/admin/trigger-price-decay` | Admin | Manual decay trigger |

Full interactive docs: **http://localhost:8000/docs**

---

## 🗄️ Database

Schema auto-created on startup (dev). For production use Alembic:

```bash
alembic upgrade head
alembic revision --autogenerate -m "describe change"
```
