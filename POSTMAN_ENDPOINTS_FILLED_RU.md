# RescueBite: готовые заполненные endpoints для Postman

Импортируй в Postman два файла:

- `RescueBite_READY.postman_collection.json`
- `RescueBite_READY.postman_environment.json`

Потом выбери environment `RescueBite Local READY`.

## Общие правила

Base URL:

```text
{{base_url}} = http://localhost:8000
```

Для всех JSON-запросов header:

```http
Content-Type: application/json
```

Для защищенных endpoints добавляй один из headers:

```http
Authorization: Bearer {{customer_token}}
Authorization: Bearer {{vendor_token}}
Authorization: Bearer {{admin_token}}
```

## Правильный порядок проверки

1. `00 System / Health`
2. `01 Auth - Customer / Register Customer`
3. Получи OTP из email, вставь в переменную `otp_code`
4. `01 Auth - Customer / Verify Customer Email`
5. `01 Auth - Customer / Login Customer - save tokens`
6. Повтори register -> verify -> login для vendor
7. Повтори register -> verify -> login для admin
8. `04 Vendors / Register Vendor Profile`
9. `08 Admin / List Vendors`, если `vendor_id` не сохранился
10. `08 Admin / Approve Vendor`
11. `05 Listings / Create Listing`
12. `06 Orders / Create Order`
13. `07 Payments / Initiate Payment`
14. `07 Payments / Simulate Payment Success`
15. `07 Payments / Payment Status`

## 00 System

### Health

```http
GET {{base_url}}/health
```

Auth: no.

Ожидаемый ответ: `200`.

## 01 Auth - Customer

### Register Customer

```http
POST {{base_url}}/auth/register
```

Body:

```json
{
  "email": "{{customer_email}}",
  "password": "{{password}}",
  "role": "customer",
  "full_name": "Test Customer"
}
```

Ожидаемый ответ: `201`. Если пользователь уже есть: `409`.

### Verify Customer Email

```http
POST {{base_url}}/auth/verify-email
```

Body:

```json
{
  "email": "{{customer_email}}",
  "code": "{{otp_code}}"
}
```

Перед отправкой вставь код из письма в переменную `otp_code`.

Ожидаемый ответ: `200`.

### Login Customer

```http
POST {{base_url}}/auth/login
```

Body:

```json
{
  "email": "{{customer_email}}",
  "password": "{{password}}"
}
```

Ожидаемый ответ: `200`.

Postman сам сохранит:

- `customer_token`
- `customer_refresh`

### Customer Me

```http
GET {{base_url}}/auth/me
Authorization: Bearer {{customer_token}}
```

Ожидаемый ответ: `200`.

### Update Customer Profile

```http
PATCH {{base_url}}/auth/me
Authorization: Bearer {{customer_token}}
```

Body:

```json
{
  "full_name": "Updated Customer",
  "phone": "+77000000001",
  "allergen_profile": ["gluten", "dairy"]
}
```

Ожидаемый ответ: `200`.

### Refresh Customer Token

```http
POST {{base_url}}/auth/refresh
```

Body:

```json
{
  "refresh_token": "{{customer_refresh}}"
}
```

Ожидаемый ответ: `200`. Postman обновит `customer_token` и `customer_refresh`.

### Forgot Password

```http
POST {{base_url}}/auth/forgot-password
```

Body:

```json
{
  "email": "{{customer_email}}"
}
```

Ожидаемый ответ: `200`. На email должна прийти ссылка/token reset password.

### Reset Password

```http
POST {{base_url}}/auth/reset-password
```

Body:

```json
{
  "token": "{{reset_token}}",
  "new_password": "NewSecure123!"
}
```

Перед отправкой вставь reset token из письма в переменную `reset_token`.

Ожидаемый ответ: `200`.

### Logout Customer

```http
POST {{base_url}}/auth/logout
```

Body:

```json
{
  "refresh_token": "{{customer_refresh}}"
}
```

Ожидаемый ответ: `204`.

## 02 Auth - Vendor

### Register Vendor User

```http
POST {{base_url}}/auth/register
```

Body:

```json
{
  "email": "{{vendor_email}}",
  "password": "{{password}}",
  "role": "vendor",
  "full_name": "Test Vendor"
}
```

Ожидаемый ответ: `201` или `409`, если уже существует.

### Verify Vendor Email

```http
POST {{base_url}}/auth/verify-email
```

Body:

```json
{
  "email": "{{vendor_email}}",
  "code": "{{otp_code}}"
}
```

Ожидаемый ответ: `200`.

### Login Vendor

```http
POST {{base_url}}/auth/login
```

Body:

```json
{
  "email": "{{vendor_email}}",
  "password": "{{password}}"
}
```

Ожидаемый ответ: `200`. Postman сохранит `vendor_token` и `vendor_refresh`.

## 03 Auth - Admin

### Register Admin User

```http
POST {{base_url}}/auth/register
```

Body:

```json
{
  "email": "{{admin_email}}",
  "password": "{{password}}",
  "role": "admin",
  "full_name": "Test Admin"
}
```

Ожидаемый ответ: `201` или `409`, если уже существует.

### Verify Admin Email

```http
POST {{base_url}}/auth/verify-email
```

Body:

```json
{
  "email": "{{admin_email}}",
  "code": "{{otp_code}}"
}
```

Ожидаемый ответ: `200`.

### Login Admin

```http
POST {{base_url}}/auth/login
```

Body:

```json
{
  "email": "{{admin_email}}",
  "password": "{{password}}"
}
```

Ожидаемый ответ: `200`. Postman сохранит `admin_token` и `admin_refresh`.

## 04 Vendors

### Register Vendor Profile

```http
POST {{base_url}}/vendors/register
Authorization: Bearer {{vendor_token}}
```

Body:

```json
{
  "business_name": "Green Cafe",
  "bin_number": "123456789012",
  "address": "Almaty, Abaya 1",
  "latitude": 43.238,
  "longitude": 76.945
}
```

Ожидаемый ответ: `201`. Postman сохранит `vendor_id`.

### Get My Vendor Profile

```http
GET {{base_url}}/vendors/me
Authorization: Bearer {{vendor_token}}
```

Ожидаемый ответ: `200`.

### Get Vendor By ID

```http
GET {{base_url}}/vendors/{{vendor_id}}
```

Auth: no.

Ожидаемый ответ: `200`.

## 05 Listings

### Browse Listings

```http
GET {{base_url}}/listings?limit=20
```

Auth: no.

Ожидаемый ответ: `200`.

### Create Listing

Сначала admin должен выполнить `Approve Vendor`.

```http
POST {{base_url}}/listings
Authorization: Bearer {{vendor_token}}
```

Body:

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

Ожидаемый ответ: `201`. Postman сохранит `listing_id`.

### Allergen Check

```http
POST {{base_url}}/listings/allergen-check
Authorization: Bearer {{customer_token}}
```

Body:

```json
{
  "ingredients": ["wheat flour", "salmon", "rice"],
  "user_allergens": ["gluten", "dairy"]
}
```

Ожидаемый ответ: `200`.

### My Vendor Listings

```http
GET {{base_url}}/listings/vendor/my-listings?limit=20
Authorization: Bearer {{vendor_token}}
```

Ожидаемый ответ: `200`.

### Get Listing By ID

```http
GET {{base_url}}/listings/{{listing_id}}
```

Auth: no.

Ожидаемый ответ: `200`.

### Update Listing

```http
PATCH {{base_url}}/listings/{{listing_id}}
Authorization: Bearer {{vendor_token}}
```

Body:

```json
{
  "title": "Updated Sushi Box",
  "quantity_total": 8,
  "status": "active"
}
```

Ожидаемый ответ: `200`.

### Delete Listing

```http
DELETE {{base_url}}/listings/{{listing_id}}
Authorization: Bearer {{vendor_token}}
```

Ожидаемый ответ: `204`. Если по listing уже есть заказ, будет `409`.

## 06 Orders

### Create Order

```http
POST {{base_url}}/orders
Authorization: Bearer {{customer_token}}
```

Body:

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

Ожидаемый ответ: `201`. Postman сохранит `order_id`.

### My Orders

```http
GET {{base_url}}/orders?limit=20
Authorization: Bearer {{customer_token}}
```

Ожидаемый ответ: `200`.

### Get Order By ID

```http
GET {{base_url}}/orders/{{order_id}}
Authorization: Bearer {{customer_token}}
```

Ожидаемый ответ: `200`.

### Update Order Status

```http
PATCH {{base_url}}/orders/{{order_id}}/status
Authorization: Bearer {{vendor_token}}
```

Body:

```json
{
  "status": "confirmed",
  "reason": "Confirmed by vendor"
}
```

Ожидаемый ответ: `200`.

Статусы заказа:

```text
pending
confirmed
ready_for_pickup
picked_up
cancelled
expired
```

## 07 Payments

### Initiate Payment

```http
POST {{base_url}}/payments/{{order_id}}/initiate
Authorization: Bearer {{customer_token}}
```

Body: empty.

Ожидаемый ответ: `200`.

### Simulate Payment Success

```http
POST {{base_url}}/payments/{{order_id}}/simulate-success
Authorization: Bearer {{customer_token}}
```

Body: empty.

Ожидаемый ответ: `200`.

### Payment Status

```http
GET {{base_url}}/payments/{{order_id}}/status
Authorization: Bearer {{customer_token}}
```

Ожидаемый ответ: `200`.

## 08 Admin

### Stats

```http
GET {{base_url}}/admin/stats
Authorization: Bearer {{admin_token}}
```

Ожидаемый ответ: `200`.

### List Users

```http
GET {{base_url}}/admin/users?limit=20
Authorization: Bearer {{admin_token}}
```

Ожидаемый ответ: `200`.

### Get User By ID

```http
GET {{base_url}}/admin/users/{{user_id}}
Authorization: Bearer {{admin_token}}
```

Ожидаемый ответ: `200`.

### Update User

```http
PATCH {{base_url}}/admin/users/{{user_id}}
Authorization: Bearer {{admin_token}}
```

Body:

```json
{
  "full_name": "Admin Updated User",
  "is_active": true
}
```

Ожидаемый ответ: `200`.

### Suspend User

```http
PATCH {{base_url}}/admin/users/{{user_id}}/suspend?is_active=false
Authorization: Bearer {{admin_token}}
```

Body: empty.

Ожидаемый ответ: `200`.

### List Vendors

```http
GET {{base_url}}/admin/vendors
Authorization: Bearer {{admin_token}}
```

Ожидаемый ответ: `200`.

### Approve Vendor

```http
PATCH {{base_url}}/admin/vendors/{{vendor_id}}/approve
Authorization: Bearer {{admin_token}}
```

Body:

```json
{
  "action": "approve",
  "reason": "Documents verified"
}
```

Ожидаемый ответ: `200`.

### List Admin Listings

```http
GET {{base_url}}/admin/listings?limit=20
Authorization: Bearer {{admin_token}}
```

Ожидаемый ответ: `200`.

### Update Admin Listing

```http
PATCH {{base_url}}/admin/listings/{{listing_id}}
Authorization: Bearer {{admin_token}}
```

Body:

```json
{
  "status": "active"
}
```

Ожидаемый ответ: `200`.

### List Admin Orders

```http
GET {{base_url}}/admin/orders?limit=20
Authorization: Bearer {{admin_token}}
```

Ожидаемый ответ: `200`.

### Get Admin Order By ID

```http
GET {{base_url}}/admin/orders/{{order_id}}
Authorization: Bearer {{admin_token}}
```

Ожидаемый ответ: `200`.

### Trigger Price Decay

```http
POST {{base_url}}/admin/trigger-price-decay
Authorization: Bearer {{admin_token}}
```

Body: empty.

Ожидаемый ответ: `200`.

## 09 Jobs

### Jobs Status

```http
GET {{base_url}}/jobs/status
Authorization: Bearer {{admin_token}}
```

Ожидаемый ответ:

- `200`, если Celery worker доступен;
- `503`, если worker не запущен.

### Get Job By Task ID

```http
GET {{base_url}}/jobs/{{task_id}}
Authorization: Bearer {{admin_token}}
```

Перед отправкой вставь реальный task id в переменную `task_id`.

Ожидаемый ответ: `200`.

## Важные замечания

- `otp_code` всегда разный. Его нужно брать из письма.
- Если email не настроен, registration пройдет, но письмо не придет.
- Если login возвращает `403 Please verify your email before logging in`, значит email еще не подтвержден.
- Если `Create Listing` возвращает `403 Vendor account is pending approval`, сначала выполни `Approve Vendor`.
- Если endpoint возвращает `401`, проверь token в Authorization.
- Если endpoint возвращает `422`, проверь JSON body.
