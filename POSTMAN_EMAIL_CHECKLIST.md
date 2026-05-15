# RescueBite: проверка email и API в Postman

## 1. Запуск backend

Самый простой вариант:

```powershell
docker compose up --build
docker compose exec api alembic upgrade head
```

API должен отвечать:

```http
GET http://localhost:8000/health
```

Ожидаемый ответ:

```json
{
  "status": "ok",
  "service": "rescuebite-api",
  "version": "1.0.0"
}
```

## 2. Как проверить email

Email в проекте отправляется не напрямую из endpoint, а через Celery:

- `POST /auth/register` ставит задачу `send_verification_email`
- `POST /auth/resend-verification` ставит задачу `send_verification_email`
- `POST /auth/forgot-password` ставит задачу `send_password_reset_email`
- `POST /orders` ставит задачу `send_order_confirmation_email`
- `PATCH /admin/vendors/{vendor_id}/approve` ставит задачу `send_vendor_approved_email`

Для реальной отправки должны быть заполнены SMTP-переменные у `api` и `worker`:

```env
SMTP_HOST=smtp.your-provider.com
SMTP_PORT=587
SMTP_USER=your-user
SMTP_PASSWORD=your-password-or-api-key
SMTP_FROM=noreply@rescuebite.kz
FRONTEND_URL=http://localhost:3000
```

Важно: сейчас в `docker-compose.yml` эти `SMTP_*` переменные не передаются в `api` и `worker`. Если запуск через Docker, добавь их в `environment` для обоих сервисов или подключи `.env`.

Проверка по шагам:

1. Запусти `api`, `redis`, `worker`.
2. В Postman выполни `POST /auth/register`.
3. В логах worker должно появиться выполнение email-задачи.
4. В почтовом ящике должен прийти OTP-код.
5. Введи код в `POST /auth/verify-email`.
6. После успешной верификации `POST /auth/login` должен вернуть `access_token`.

Если письмо не пришло:

- проверь, что worker запущен;
- проверь, что SMTP-переменные есть именно у worker;
- проверь spam/junk;
- проверь логи worker: ошибка SMTP будет там;
- если в логах есть `SMTP not configured`, значит `SMTP_HOST` или `SMTP_USER` пустые.

## 3. Postman: базовая настройка

Импортируй `RescueBite.postman_collection.json` или `openapi.yaml`.

Создай переменные коллекции:

```text
base_url = http://localhost:8000
customer_token =
vendor_token =
admin_token =
customer_refresh =
vendor_refresh =
admin_refresh =
customer_email = customer@test.kz
vendor_email = vendor@test.kz
admin_email = admin@test.kz
password = Secure123!
vendor_id =
listing_id =
order_id =
task_id =
```

Для protected endpoints добавляй header:

```http
Authorization: Bearer {{customer_token}}
```

или `{{vendor_token}}`, `{{admin_token}}` в зависимости от роли.

## 4. Основной порядок проверки

### 4.1 Health

```http
GET {{base_url}}/health
```

Ожидай `200`.

### 4.2 Регистрация customer

```http
POST {{base_url}}/auth/register
Content-Type: application/json
```

```json
{
  "email": "{{customer_email}}",
  "password": "{{password}}",
  "role": "customer",
  "full_name": "Test Customer"
}
```

Ожидай `201`. На email должен прийти OTP.

### 4.3 Подтверждение email

```http
POST {{base_url}}/auth/verify-email
Content-Type: application/json
```

```json
{
  "email": "{{customer_email}}",
  "code": "123456"
}
```

Вместо `123456` поставь код из письма. Ожидай `200`.

### 4.4 Login customer

```http
POST {{base_url}}/auth/login
Content-Type: application/json
```

```json
{
  "email": "{{customer_email}}",
  "password": "{{password}}"
}
```

Ожидай `200`. Сохрани:

- `access_token` в `customer_token`
- `refresh_token` в `customer_refresh`

Postman Tests:

```javascript
const json = pm.response.json();
pm.collectionVariables.set("customer_token", json.access_token);
pm.collectionVariables.set("customer_refresh", json.refresh_token);
pm.test("login ok", () => pm.response.to.have.status(200));
```

### 4.5 Повтори для vendor и admin

Регистрируй так же, но с ролями:

```json
{
  "email": "{{vendor_email}}",
  "password": "{{password}}",
  "role": "vendor",
  "full_name": "Test Vendor"
}
```

```json
{
  "email": "{{admin_email}}",
  "password": "{{password}}",
  "role": "admin",
  "full_name": "Test Admin"
}
```

Каждый email нужно подтвердить через `POST /auth/verify-email`, потом залогиниться и сохранить соответствующий token.

## 5. Все endpoints и как их проверять

### Auth

| Method | URL | Auth | Body / query | Успех |
|---|---|---|---|---|
| GET | `/health` | no | - | `200` |
| POST | `/auth/register` | no | `email,password,role,full_name,phone` | `201` |
| POST | `/auth/verify-email` | no | `email,code` | `200` |
| POST | `/auth/resend-verification` | no | `email` | `200` |
| POST | `/auth/forgot-password` | no | `email` | `200` |
| POST | `/auth/reset-password` | no | `token,new_password` | `200` |
| POST | `/auth/login` | no | `email,password` | `200`, tokens |
| POST | `/auth/refresh` | no | `refresh_token` | `200`, new tokens |
| POST | `/auth/logout` | no | `refresh_token` | `204` |
| GET | `/auth/me` | user | - | `200` |
| PATCH | `/auth/me` | user | `full_name,phone,allergen_profile` | `200` |
| PATCH | `/auth/me/password` | user | `current_password,new_password` | `204` |
| DELETE | `/auth/me` | user | - | `204` |

### Vendors

| Method | URL | Auth | Body / query | Успех |
|---|---|---|---|---|
| POST | `/vendors/register` | vendor/admin | `business_name,bin_number,address,latitude,longitude` | `201` |
| GET | `/vendors/me` | vendor/admin | - | `200` |
| GET | `/vendors/{vendor_id}` | no | - | `200` |

Vendor сначала будет `is_approved=false`. До approval он не сможет создать listing.

### Admin vendor approval

```http
PATCH {{base_url}}/admin/vendors/{{vendor_id}}/approve
Authorization: Bearer {{admin_token}}
Content-Type: application/json
```

```json
{
  "action": "approve",
  "reason": "Documents verified"
}
```

Ожидай `200`. После этого vendor может создавать listings.

### Listings

| Method | URL | Auth | Body / query | Успех |
|---|---|---|---|---|
| GET | `/listings?limit=20` | no | optional `cursor,lat,lng` | `200` |
| POST | `/listings` | vendor/admin | listing body | `201` |
| POST | `/listings/allergen-check` | user | `ingredients,user_allergens` | `200` |
| GET | `/listings/vendor/my-listings` | vendor/admin | optional `cursor,limit,status` | `200` |
| GET | `/listings/{listing_id}` | no | - | `200` |
| PATCH | `/listings/{listing_id}` | owner vendor/admin | partial listing body | `200` |
| DELETE | `/listings/{listing_id}` | owner vendor/admin | - | `204` |

Create listing body:

```json
{
  "title": "Sushi Box",
  "description": "Fresh sushi set",
  "original_price": 5000,
  "discount_percentage": 40,
  "quantity_total": 10,
  "pickup_window_start": "2026-12-31T18:00:00",
  "pickup_window_end": "2026-12-31T21:00:00",
  "allergens": ["fish", "gluten"],
  "latitude": 43.238,
  "longitude": 76.945,
  "photo_url": null
}
```

После создания сохрани `id` в `listing_id`.

### Orders

| Method | URL | Auth | Body / query | Успех |
|---|---|---|---|---|
| POST | `/orders` | customer/admin | `items` | `201` |
| GET | `/orders?limit=20` | user | optional `cursor,limit` | `200` |
| GET | `/orders/{order_id}` | owner/admin/vendor rules | - | `200` |
| PATCH | `/orders/{order_id}/status` | user | `status,reason` | `200` |

Create order body:

```json
{
  "items": [
    {
      "listing_id": {{listing_id}},
      "quantity": 2
    }
  ]
}
```

После создания сохрани `id` в `order_id`.

### Payments

| Method | URL | Auth | Body / query | Успех |
|---|---|---|---|---|
| POST | `/payments/{order_id}/initiate` | customer/admin | - | `200` |
| POST | `/payments/{order_id}/simulate-success` | customer/admin | - | `200` |
| GET | `/payments/{order_id}/status` | user | - | `200` |

Порядок: `initiate` -> `simulate-success` -> `status`.

### Admin

| Method | URL | Auth | Body / query | Успех |
|---|---|---|---|---|
| GET | `/admin/stats` | admin | - | `200` |
| GET | `/admin/users` | admin | optional `cursor,limit,role,is_active` | `200` |
| GET | `/admin/users/{user_id}` | admin | - | `200` |
| PATCH | `/admin/users/{user_id}` | admin | `full_name,phone,role,is_active` | `200` |
| DELETE | `/admin/users/{user_id}` | admin | - | `204` или business error |
| PATCH | `/admin/users/{user_id}/suspend?is_active=false` | admin | query | `200` |
| GET | `/admin/vendors` | admin | optional `is_approved` | `200` |
| PATCH | `/admin/vendors/{vendor_id}/approve` | admin | `action,reason` | `200` |
| DELETE | `/admin/vendors/{vendor_id}` | admin | - | `204` или `409` |
| GET | `/admin/listings` | admin | optional `cursor,limit,status,vendor_id` | `200` |
| PATCH | `/admin/listings/{listing_id}` | admin | partial listing body | `200` |
| DELETE | `/admin/listings/{listing_id}` | admin | - | `204` или `409` |
| GET | `/admin/orders` | admin | optional `cursor,limit,status,vendor_id,customer_id` | `200` |
| GET | `/admin/orders/{order_id}` | admin | - | `200` |
| POST | `/admin/trigger-price-decay` | admin | - | `200` |

### Jobs

| Method | URL | Auth | Body / query | Успех |
|---|---|---|---|---|
| GET | `/jobs/status` | admin | - | `200` или `503` если worker недоступен |
| GET | `/jobs/{task_id}` | admin | - | `200` |

## 6. Правильная последовательность для полной проверки

1. `GET /health`
2. Register customer -> получить OTP -> verify -> login -> сохранить `customer_token`
3. Register vendor -> получить OTP -> verify -> login -> сохранить `vendor_token`
4. Register admin -> получить OTP -> verify -> login -> сохранить `admin_token`
5. Vendor: `POST /vendors/register` -> сохранить `vendor_id`
6. Admin: `PATCH /admin/vendors/{vendor_id}/approve`
7. Vendor: `POST /listings` -> сохранить `listing_id`
8. Public: `GET /listings`, `GET /listings/{listing_id}`
9. Customer: `POST /listings/allergen-check`
10. Customer: `POST /orders` -> сохранить `order_id`
11. Customer: `POST /payments/{order_id}/initiate`
12. Customer: `POST /payments/{order_id}/simulate-success`
13. Customer: `GET /payments/{order_id}/status`
14. Vendor/Admin: `PATCH /orders/{order_id}/status`
15. Admin: проверить `/admin/stats`, `/admin/users`, `/admin/vendors`, `/admin/listings`, `/admin/orders`
16. Admin: `GET /jobs/status`

## 7. Частые ошибки

- `403 Please verify your email before logging in` - сначала выполни `/auth/verify-email`.
- `403 Vendor account is pending approval` - admin должен approve vendor.
- `401 Not authenticated` - нет `Authorization: Bearer ...`.
- `422` - неправильный JSON или не хватает поля.
- `409 Email already registered` - используй другой email или очисти базу.
- `503 Could not reach Celery workers` - worker не запущен.
- Письма не приходят - SMTP не передан в worker или неверные SMTP credentials.
