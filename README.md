# RescueBite API

**Food Waste Reduction Marketplace** — production-grade backend + frontend system.

Vendors list surplus food at discounted prices. Customers buy it before it expires.
Everyone wins: less waste, cheaper meals.

---

## Live Deployment

| Service | URL |
|---------|-----|
| Frontend | https://foodwaste-1-fe33.onrender.com |
| API (production) | https://foodwaste-gcjn.onrender.com |
| Swagger UI | https://foodwaste-gcjn.onrender.com/docs |
| ReDoc | https://foodwaste-gcjn.onrender.com/redoc |

**Demo accounts (seeded on first deploy):**

| Email | Password | Role |
|-------|----------|------|
| admin@test.kz | Secure123! | admin |
| vendor@test.kz | Secure123! | vendor |
| customer@test.kz | Secure123! | customer |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI 0.111 (async) |
| ORM | SQLModel + SQLAlchemy (async) |
| Database | PostgreSQL 16 (Render managed) |
| Cache / Queue Broker | Redis 7 (Upstash TLS) |
| Background Workers | Celery 5.3 + Celery Beat |
| Auth | JWT (HS256) + Redis-backed refresh tokens |
| Password | bcrypt |
| Frontend | React 18 + Vite + Tailwind CSS |
| Tests | pytest + pytest-asyncio |
| Containerization | Docker + Docker Compose |
| Platform | Render.com |

---

## Quick Start (Docker)

```bash
git clone https://github.com/Har1se/foodwaste.git
cd rescuebite-api

cp .env.example .env
# Edit .env — set SECRET_KEY, DATABASE_URL, REDIS_URL

docker compose up --build

# API:     http://localhost:8000
# Swagger: http://localhost:8000/docs
# Frontend: http://localhost:3000
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

# New terminal — Celery Beat scheduler
celery -A app.tasks.celery_app beat --loglevel=info
```

### Frontend

```bash
cd frontend
npm install
VITE_API_URL=http://localhost:8000 npm run dev   # http://localhost:3000
```

---

## Environment Variables

```env
DATABASE_URL=postgresql+asyncpg://rescuebite:rescuebite@localhost:5432/rescuebite_db
REDIS_URL=redis://localhost:6379/0

# REQUIRED: at least 32 characters
SECRET_KEY=your-very-long-random-secret-key-here-at-least-32-chars

ACCESS_TOKEN_EXPIRE_MINUTES=43200
REFRESH_TOKEN_EXPIRE_DAYS=7

# Email (Gmail / SendGrid / Yandex)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=noreply@rescuebite.kz

FRONTEND_URL=http://localhost:3000
CORS_ORIGINS=http://localhost:3000,http://localhost:8000

ENVIRONMENT=development
DEBUG=true
```

---

## API Overview

### Auth (`/auth`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/register` | Register → sends OTP to email |
| POST | `/auth/verify-email` | Verify OTP code |
| POST | `/auth/login` | Login → returns JWT tokens |
| POST | `/auth/refresh` | Rotate refresh token |
| POST | `/auth/logout` | Revoke session |
| GET | `/auth/me` | Get own profile |
| PATCH | `/auth/me` | Update profile |
| PATCH | `/auth/me/password` | Change password |

### Listings (`/listings`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/listings` | Browse active listings (category, cursor pagination) |
| GET | `/listings/{id}` | Get single listing |
| POST | `/listings` | Create listing (vendor only) |
| PATCH | `/listings/{id}` | Update own listing |
| DELETE | `/listings/{id}` | Delete own listing |
| GET | `/listings/vendor/my-listings` | Vendor's own listings |
| POST | `/listings/allergen-check` | Check ingredients against allergen profile |

### Orders (`/orders`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/orders` | Place order (atomic, oversell-safe) |
| GET | `/orders` | List own orders |
| GET | `/orders/{id}` | Get order details |
| PATCH | `/orders/{id}/status` | Update order status |

### Payments (`/payments`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/payments/{id}/initiate` | Initiate Kaspi Pay |
| POST | `/payments/{id}/simulate-success` | Simulate payment (demo) |
| GET | `/payments/{id}/status` | Check payment status |

### Auctions (`/auctions`)
Lowest unique bid wins reverse auction.
| Method | Path | Description |
|--------|------|-------------|
| GET | `/auctions` | List active auctions |
| POST | `/auctions` | Create auction |
| GET | `/auctions/{id}` | Get auction + bid count |
| POST | `/auctions/{id}/bid` | Place bid |
| POST | `/auctions/{id}/end` | End auction manually |

### Vendors (`/vendors`)
| POST | `/vendors/register` | Submit vendor application |
| GET | `/vendors/me` | Own vendor profile |
| GET | `/vendors/{id}` | Public vendor profile |

### Drivers (`/drivers`, `/deliveries`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/drivers/register` | Register as driver |
| PATCH | `/drivers/me/location` | Update GPS location |
| GET | `/drivers/nearby` | Find nearby available drivers |
| POST | `/drivers/assign/{order_id}` | Assign driver to order |
| GET | `/drivers/route-optimize` | Nearest-neighbor route for driver |
| GET | `/deliveries/my` | Driver's delivery queue |
| PATCH | `/deliveries/{id}/status` | Update delivery status |

### Admin (`/admin`) — requires admin role
| Method | Path | Description |
|--------|------|-------------|
| GET | `/admin/stats` | Platform statistics |
| GET/PATCH/DELETE | `/admin/users/{id}` | User management |
| GET/PATCH/DELETE | `/admin/vendors/{id}` | Vendor management |
| PATCH | `/admin/vendors/{id}/approve` | Approve/reject vendor |
| GET/PATCH/DELETE | `/admin/listings/{id}` | Full listing control |
| GET | `/admin/orders` | All orders |
| GET | `/admin/logs` | System request logs |
| POST | `/admin/trigger-price-decay` | Manual price decay trigger |
| POST | `/admin/seed-reset` | Re-seed demo data |

### Jobs (`/jobs`) — requires admin role
| GET | `/jobs/status` | Celery worker + Beat schedule |
| GET | `/jobs/{task_id}` | Specific task result |

---

## User Roles & Permissions

| Role | Capabilities |
|------|-------------|
| `customer` | Browse listings, place orders, pay, view own orders, bid on auctions |
| `vendor` | Manage own listings, view vendor orders, create auctions |
| `driver` | Register, update location, manage own deliveries |
| `admin` | Full CRUD on all resources + stats + job control |

---

## Key Business Workflows

### 1. Food State Machine (Celery Beat — every 72h)
```
ACTIVE → DISCOUNTED  (days_active ≥ 30, 10% price decay per cycle)
DISCOUNTED → FREE    (current_price hits 0)
FREE → COMPOST       (pickup_window_end passed)
any → SOLD_OUT       (quantity_available = 0)
```

### 2. Atomic Order (2-layer oversell prevention)
1. Redis soft lock (5-min TTL per listing slot)
2. PostgreSQL `SELECT FOR UPDATE` row lock + atomic decrement

### 3. Allergen Parser
`POST /listings/allergen-check` — detects allergens in ingredients list, compares with user's allergen profile, returns safe/unsafe result.

### 4. Reverse Auction
Lowest **unique** bid at deadline wins. Standard auctions: highest bid wins. Reverse: the rarest low price wins.

### 5. Payment Flow
```
POST /payments/{id}/initiate         → Kaspi Pay redirect URL (production)
POST /payments/{id}/simulate-success → instant success (demo/dev)
```

---

## Email Notifications

| Event | Trigger |
|-------|---------|
| Email verification OTP | User registers |
| Order confirmation + pickup token | Order placed |
| Vendor approved | Admin approves vendor |
| Password reset link | User requests reset |

Sent via Celery queue — non-blocking.

---

## Running Tests

```bash
pytest tests/ -v

# With coverage report
pytest tests/ -v --cov=app --cov-report=term-missing
```

Uses SQLite in-memory + mocked Redis/Celery — no external services needed.

---

## Database Migrations

```bash
alembic upgrade head                          # apply all migrations
alembic current                               # current revision
alembic history                               # migration history
alembic revision --autogenerate -m "message"  # new migration
```

---

## Background Jobs

```bash
celery -A app.tasks.celery_app worker --loglevel=info
celery -A app.tasks.celery_app beat --loglevel=info
```

| Job | Schedule | Description |
|-----|----------|-------------|
| price_decay_task | Every 72 hours | Age listings, decay price, change status |
| process_expired_auctions | Every 5 minutes | End auctions past deadline |

Monitor (admin token required):
```
GET  /jobs/status               — workers, active tasks, Beat schedule
POST /admin/trigger-price-decay — manual trigger
```

---

## Frontend Pages

| Path | Description | Access |
|------|-------------|--------|
| `/` | Marketplace — browse food listings | Public |
| `/login` | Login | Public |
| `/register` | Register (customer or vendor) | Public |
| `/verify-email` | OTP verification | Public |
| `/forgot-password` | Password reset request | Public |
| `/reset-password` | Set new password | Public |
| `/auctions` | Active auctions | Public |
| `/orders` | My orders + Kaspi payment | Customer |
| `/vendor` | Vendor dashboard — listings + orders | Vendor |
| `/admin` | Admin panel — full management | Admin |

---

## Project Structure

```
rescuebite-api/
├── app/
│   ├── main.py              # FastAPI factory + lifespan + middleware
│   ├── config.py            # Pydantic Settings (validates on boot)
│   ├── database.py          # Async SQLAlchemy engine
│   ├── demo_seed.py         # Auto-seed demo data
│   ├── core/
│   │   ├── dependencies.py  # JWT auth + RBAC decorators
│   │   ├── security.py      # bcrypt + JWT token creation
│   │   ├── redis.py         # Rate limiting + token storage
│   │   └── pagination.py    # Cursor-based pagination
│   ├── models/              # SQLModel ORM models
│   ├── schemas/             # Pydantic request/response schemas
│   ├── routers/             # FastAPI route handlers
│   │   ├── auth.py
│   │   ├── listings.py
│   │   ├── orders.py
│   │   ├── vendors.py
│   │   ├── payments.py
│   │   ├── auctions.py
│   │   ├── drivers.py
│   │   ├── jobs.py
│   │   └── admin.py
│   ├── services/            # Business logic layer
│   └── tasks/               # Celery tasks
│       ├── celery_app.py
│       ├── price_decay.py
│       ├── auction_tasks.py
│       └── email_tasks.py
├── frontend/                # React 18 + Vite + Tailwind CSS
│   └── src/
│       ├── api/client.js    # Axios with auto-refresh interceptor
│       ├── contexts/        # AuthContext
│       ├── pages/           # Home, Login, Register, Orders, Vendor, Admin, Auctions
│       └── components/      # Navbar, ListingCard, Modal
├── migrations/              # Alembic migration history (001–004)
├── tests/                   # pytest async test suite (62%+ coverage)
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── RescueBite.postman_collection.json  # Import into Postman
└── DEPLOYED_URL.txt
```

---

## Docker Compose Services

| Service | Port | Description |
|---------|------|-------------|
| `api` | 8000 | FastAPI application |
| `db` | 5432 | PostgreSQL 16 |
| `redis` | 6379 | Redis 7 |
| `worker` | — | Celery worker |
| `beat` | — | Celery Beat scheduler |
| `flower` | 5555 | Celery monitoring UI |

---

## Postman Collection

Import `RescueBite.postman_collection.json` for all endpoints pre-configured.

Collection variables auto-populated after login:
- `access_token` — set after "Login as Customer"
- `vendor_token` — set after "Login as Vendor"
- `admin_token` — set after "Login as Admin"

---

## Defense Demo Checklist

### Setup
- [ ] Open https://foodwaste-1-fe33.onrender.com
- [ ] Open https://foodwaste-gcjn.onrender.com/docs
- [ ] Import `RescueBite.postman_collection.json`

### Customer Flow
- [ ] Register new account → receive OTP → verify email
- [ ] Login → JWT token returned
- [ ] Browse marketplace → filter by category → search
- [ ] Place order → show atomic stock decrement
- [ ] Simulate Kaspi payment → show pickup token in order

### Vendor Flow
- [ ] Login as vendor@test.kz
- [ ] Open vendor dashboard → see own listings
- [ ] Create new listing with price, quantity, category, pickup window
- [ ] See new listing appear on marketplace

### Admin Flow
- [ ] Login as admin@test.kz
- [ ] GET /admin/stats → platform overview
- [ ] View users list, inspect vendor application
- [ ] Approve a vendor
- [ ] POST /admin/trigger-price-decay → show state machine
- [ ] GET /admin/logs → show request audit trail

### Advanced Features
- [ ] POST /listings/allergen-check → demonstrate allergen parser
- [ ] Create auction → place bids → end auction → show winner
- [ ] GET /jobs/status → show Celery workers + Beat schedule
- [ ] pytest tests/ -v → all tests green
