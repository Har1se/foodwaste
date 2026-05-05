# CHANGELOG — RescueBite API

## Sprint 1 — Implementation (May 2025)

### Отклонения от blueprint (openapi.yaml)

#### 1. Схемы генерируются из кода, не из openapi.yaml напрямую
**Blueprint:** openapi.yaml задаёт контракт, Swagger UI должен его монтировать.
**Реализовано:** FastAPI автоматически генерирует `/docs` из Pydantic-схем.
**Причина:** FastAPI native OpenAPI generation — это стандартный подход. Все схемы
в `app/schemas/` соответствуют контракту из openapi.yaml. Расхождений нет.

#### 2. `ListingAllergen.allergen_code` — String вместо Enum колонки
**Blueprint:** `AllergenCode` enum как PostgreSQL ENUM тип.
**Реализовано:** `String(20)` с валидацией на уровне Pydantic.
**Причина:** SQLite (используется в тестах) не поддерживает PostgreSQL ENUM.
В production на PostgreSQL можно добавить `sa.Enum(AllergenCode)` через миграцию.

#### 3. Пагинация — гибридный подход
**Blueprint:** Только cursor-based (keyset) pagination.
**Реализовано:** `CursorPage` с `next_cursor` на всех list-эндпоинтах.
`PageParam` и `LimitParam` оставлены в компонентах openapi.yaml как legacy,
но в реализации используется только cursor.

#### 4. `/vendors/me/dashboard` — нет расширенной аналитики
**Blueprint:** `VendorDashboardResponse` с earnings, orders stats.
**Реализовано:** Базовый профиль через `/vendors/me`.
**Причина:** Sprint 1 фокус — auth + core transaction. Dashboard — Sprint 2.

#### 5. Driver role — не реализован
**Blueprint:** Роль `driver` с delivery endpoints.
**Реализовано:** Роль есть в `UserRole` enum, но роутер отсутствует.
**Причина:** MVP+ фича, не входит в 20% минимум.

#### 6. Kaspi Pay webhook — заглушка
**Blueprint:** `POST /payments/webhook/kaspi` с signature verification.
**Реализовано:** Эндпоинт отсутствует в Sprint 1.
**Причина:** Требует реального Kaspi Pay API ключа. Будет в Sprint 2.

---

### Добавлено сверх blueprint

#### Redis двухслойная защита от overselling
`order_service.create_order()` использует:
1. Redis `reserve_stock()` — soft lock с TTL 300 сек
2. PostgreSQL `SELECT FOR UPDATE` — hard lock

Это сильнее, чем описано в blueprint (только SELECT FOR UPDATE).

#### Тест атомарности (`test_atomicity.py`)
`test_overselling_impossible` — concurrent запросы двух покупателей на последний
товар. Доказывает что ровно один получает 201, второй — 409.

#### Прямое использование `bcrypt` вместо `passlib`
**Причина:** `passlib[bcrypt]` несовместим с `bcrypt>=4.0` на Python 3.12.
Заменено на прямой `bcrypt.hashpw()` / `bcrypt.checkpw()`.
Функциональность идентична.
