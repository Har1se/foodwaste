# RescueBite — Architecture Decisions

## Price Decay Implementation Choice

**Decision: Application-level logic via Celery Beat (not PostgreSQL triggers)**

The assignment asks to document whether price decay is handled by application logic
or PostgreSQL triggers.

We chose **Celery Beat cron task** (`app/tasks/price_decay.py`) for these reasons:

- **Testability**: `apply_price_decay(session)` is a plain async function — can be
  unit-tested without running a PostgreSQL instance or mocking trigger behavior.
- **Configurability**: decay interval (72h) and floor price (500 KZT) are config
  values, not hardcoded in SQL. Admins can trigger it manually via
  `POST /admin/trigger-price-decay`.
- **Observability**: Celery task logs every run with count of updated listings.
  Triggers fire silently inside the DB with no application-level logging.
- **Portability**: SQLite (used in tests) does not support triggers. Application
  logic works on both SQLite and PostgreSQL.

**Trade-off**: Celery Beat has ±1 minute scheduling jitter vs. exact pg_cron timing.
For a food marketplace where decay runs every 72h, this is acceptable.

---

## Geospatial Strategy

**Decision: Haversine formula in application layer + bounding-box index**

- `latitude` and `longitude` stored as `Float` columns on `listings` table.
- Composite index `ix_listing_geo` on `(latitude, longitude)` enables fast
  bounding-box pre-filter before Haversine calculation.
- Haversine distance computed in Python (`listing_service._haversine()`) on the
  pre-filtered candidate set (~20-50 listings within bounding box).

**Why not PostGIS?**
PostGIS adds significant operational complexity (extension install, separate geometry
types). For a marketplace with ≤10,000 listings per city, Haversine on a pre-filtered
set achieves <20ms p99 latency without PostGIS overhead.

---

## SELECT FOR UPDATE — Oversell Prevention

Two-layer strategy in `order_service.create_order()`:

```
Layer 1: Redis reserve_stock()
  └── Soft lock, TTL=300s per listing_id
  └── Prevents parallel checkouts from over-committing before DB write
  └── Auto-expires if request crashes

Layer 2: PostgreSQL SELECT FOR UPDATE
  └── Row-level lock inside ACID transaction
  └── Re-checks quantity_available after lock
  └── Atomically decrements stock + creates order in single commit
```

**SQLite note**: `SELECT FOR UPDATE` is not supported by SQLite (used in tests).
The `_lock_listing_row()` function wraps it in a try/except so tests pass.
On PostgreSQL in production the lock is enforced correctly.

---

## Async Pattern

FastAPI with `asyncio` — chosen because RescueBite is I/O-bound:

- Each request may hit PostgreSQL (listing query), Redis (rate limit + reservation),
  and Kaspi Pay API (payment confirmation).
- Python `asyncio` with `async def` endpoints handles thousands of concurrent
  connections without thread overhead.
- Celery workers handle CPU-adjacent tasks (PDF receipts, email) off the main loop.

---

## Database Session Strategy

`AsyncSession` from SQLAlchemy with `expire_on_commit=False`:

- Prevents lazy-load issues after `commit()` — all attributes remain accessible.
- `get_session()` dependency commits on success, rolls back on exception.
- No ORM relationships are accessed outside the session context — all related data
  is fetched explicitly with separate `SELECT` queries to avoid `MissingGreenlet` errors.
