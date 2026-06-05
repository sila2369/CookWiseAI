# CookWise Auth Test Senaryoları

FastAPI authentication sistemi için kapsamlı test senaryoları.

---

## Senaryo 1: Başarılı Kayıt

**Endpoint:** `POST /api/v1/auth/register`

### Request

```json
{
  "full_name": "Ahmet Yılmaz",
  "email": "ahmet@example.com",
  "password": "SecurePass123",
  "phone": "+905551234567"
}
```

### Beklenen Sonuç

| Alan | Değer |
|------|-------|
| **Status Code** | `201 Created` |
| **Response** | UserResponse (hashed_password yok) |

### Örnek Response

```json
{
  "id": "674a1b2c3d4e5f6a7b8c9d0e",
  "full_name": "Ahmet Yılmaz",
  "email": "ahmet@example.com",
  "phone": "+905551234567",
  "is_active": true,
  "is_admin": false,
  "created_at": "2026-03-20T12:00:00",
  "updated_at": "2026-03-20T12:00:00"
}
```

### cURL

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Ahmet Yılmaz",
    "email": "ahmet@example.com",
    "password": "SecurePass123",
    "phone": "+905551234567"
  }'
```

### Swagger

1. `/docs` → **POST /api/v1/auth/register**
2. **Try it out** → Request body'yi yapıştır → **Execute**

---

## Senaryo 2: Aynı Email ile Tekrar Kayıt

**Endpoint:** `POST /api/v1/auth/register`

### Request

```json
{
  "full_name": "Ahmet Yılmaz",
  "email": "ahmet@example.com",
  "password": "AnotherPass456",
  "phone": "+905559999999"
}
```

*Not: ahmet@example.com zaten kayıtlı olmalı*

### Beklenen Sonuç

| Alan | Değer |
|------|-------|
| **Status Code** | `409 Conflict` |
| **Response** | Hata mesajı |

### Örnek Response

```json
{
  "detail": "Email 'ahmet@example.com' is already registered"
}
```

### cURL

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Ahmet Yılmaz",
    "email": "ahmet@example.com",
    "password": "AnotherPass456"
  }'
```

---

## Senaryo 3: Başarılı Login

**Endpoint:** `POST /api/v1/auth/login`

### Request

```json
{
  "email": "ahmet@example.com",
  "password": "SecurePass123"
}
```

### Beklenen Sonuç

| Alan | Değer |
|------|-------|
| **Status Code** | `200 OK` |
| **Response** | TokenResponse (access_token + user) |

### Örnek Response

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": "674a1b2c3d4e5f6a7b8c9d0e",
    "full_name": "Ahmet Yılmaz",
    "email": "ahmet@example.com",
    "phone": "+905551234567",
    "is_active": true,
    "is_admin": false,
    "created_at": "2026-03-20T12:00:00",
    "updated_at": "2026-03-20T12:00:00"
  }
}
```

### cURL

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "ahmet@example.com",
    "password": "SecurePass123"
  }'
```

### Token Kullanımı

```bash
# Token'ı değişkene al (jq gerekli)
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"ahmet@example.com","password":"SecurePass123"}' \
  | jq -r '.access_token')
```

---

## Senaryo 4: Yanlış Şifre

**Endpoint:** `POST /api/v1/auth/login`

### Request

```json
{
  "email": "ahmet@example.com",
  "password": "WrongPassword123"
}
```

### Beklenen Sonuç

| Alan | Değer |
|------|-------|
| **Status Code** | `401 Unauthorized` |
| **Response** | Genel hata (güvenlik: email vs şifre ayırt edilmez) |

### Örnek Response

```json
{
  "detail": "Invalid username or password"
}
```

### cURL

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "ahmet@example.com",
    "password": "WrongPassword123"
  }'
```

---

## Senaryo 5: Token Olmadan /users/me

**Endpoint:** `GET /api/v1/users/me`

### Request

- **Authorization header:** Yok

### Beklenen Sonuç

| Alan | Değer |
|------|-------|
| **Status Code** | `403 Forbidden` |
| **Response** | Not authenticated |

### Örnek Response

```json
{
  "detail": "Not authenticated"
}
```

### cURL

```bash
curl -X GET http://localhost:8000/api/v1/users/me
```

### Swagger

1. **Authorize** butonuna token girmeden
2. **GET /api/v1/users/me** → Try it out → Execute

---

## Senaryo 6: Geçersiz Token

**Endpoint:** `GET /api/v1/users/me`

### Request

```
Authorization: Bearer geçersiz-token-xyz123
```

### Beklenen Sonuç

| Alan | Değer |
|------|-------|
| **Status Code** | `401 Unauthorized` |
| **Response** | Token doğrulama hatası |

### Örnek Response

```json
{
  "detail": "Invalid token. Could not validate credentials."
}
```

### cURL

```bash
curl -X GET http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer geçersiz-token-xyz123"
```

### Süresi Dolmuş Token

Aynı response formatı, mesaj farklı olabilir:

```json
{
  "detail": "Token has expired. Please login again."
}
```

---

## Senaryo 7: Geçerli Token ile /users/me

**Endpoint:** `GET /api/v1/users/me`

### Request

```
Authorization: Bearer <geçerli_access_token>
```

### Beklenen Sonuç

| Alan | Değer |
|------|-------|
| **Status Code** | `200 OK` |
| **Response** | UserResponse (hashed_password yok) |

### Örnek Response

```json
{
  "id": "674a1b2c3d4e5f6a7b8c9d0e",
  "full_name": "Ahmet Yılmaz",
  "email": "ahmet@example.com",
  "phone": "+905551234567",
  "is_active": true,
  "is_admin": false,
  "created_at": "2026-03-20T12:00:00",
  "updated_at": "2026-03-20T12:00:00"
}
```

### cURL

```bash
# Önce login ile token al
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"ahmet@example.com","password":"SecurePass123"}' \
  | jq -r '.access_token')

# Token ile /users/me çağır
curl -X GET http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer $TOKEN"
```

### Swagger

1. **POST /auth/login** ile giriş yap → `access_token` kopyala
2. **Authorize** → Value: token'ı yapıştır → Authorize
3. **GET /api/v1/users/me** → Try it out → Execute

---

## Senaryo 8: Admin Olmayan User ile Admin Endpoint

**Endpoint:** `GET /api/v1/admin/test`

### Request

```
Authorization: Bearer <normal_user_token>
```

*Normal user: is_admin=false*

### Beklenen Sonuç

| Alan | Değer |
|------|-------|
| **Status Code** | `403 Forbidden` |
| **Response** | Admin yetkisi gerekli |

### Örnek Response

```json
{
  "detail": "Admin access required"
}
```

### cURL

```bash
# Normal user ile login
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"ahmet@example.com","password":"SecurePass123"}' \
  | jq -r '.access_token')

# Admin endpoint'e erişim dene (403 beklenir)
curl -X GET http://localhost:8000/api/v1/admin/test \
  -H "Authorization: Bearer $TOKEN"
```

### Karşılaştırma: Admin User

```bash
# Admin user ile login (MongoDB'de is_admin=true olmalı)
ADMIN_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"AdminPass123"}' \
  | jq -r '.access_token')

# Admin endpoint (200 beklenir)
curl -X GET http://localhost:8000/api/v1/admin/test \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Admin response (200):**

```json
{
  "message": "Admin access OK",
  "user_email": "admin@example.com"
}
```

---

## Özet Tablo

| # | Senaryo | Endpoint | Status | Özet |
|---|---------|----------|--------|------|
| 1 | Başarılı kayıt | POST /auth/register | 201 | Yeni kullanıcı oluşur |
| 2 | Aynı email kayıt | POST /auth/register | 409 | Email zaten kayıtlı |
| 3 | Başarılı login | POST /auth/login | 200 | Token + user döner |
| 4 | Yanlış şifre | POST /auth/login | 401 | Invalid credentials |
| 5 | Token yok | GET /users/me | 403 | Not authenticated |
| 6 | Geçersiz token | GET /users/me | 401 | Token doğrulanamadı |
| 7 | Geçerli token | GET /users/me | 200 | Profil döner |
| 8 | Admin değil | GET /admin/test | 403 | Admin access required |

---

## Ek Senaryolar (Opsiyonel)

### Geçersiz Email Format

**POST /auth/register** `{"email": "invalid-email", ...}` → `422 Unprocessable Entity`

### Zayıf Şifre

**POST /auth/register** `{"password": "123", ...}` → `422` (validation error)

### Eksik Alan

**POST /auth/login** `{"email": "a@b.com"}` (password yok) → `422`
