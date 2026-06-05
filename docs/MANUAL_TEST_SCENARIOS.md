# Manuel Test Senaryoları - Ürün & Kategori Sistemi

Bu dokümanda FastAPI ürün ve kategori API'leri için manuel test senaryoları yer almaktadır.

**Ön hazırlık:**
- Uygulama çalışır: `uvicorn app.main:app --reload`
- Swagger: http://localhost:8000/docs
- Admin kullanıcı: `admin@example.com` (is_admin=true)
- Normal kullanıcı: `testuser@example.com` (is_admin=false)
- Token almak: `POST /api/v1/auth/login` → `access_token`

---

## Senaryo 1: Admin ile Kategori Oluşturma

| Alan | Değer |
|------|-------|
| **Endpoint** | `POST /api/v1/categories` |
| **Auth** | Bearer token (admin) |
| **Expected Status** | 201 |

**Request Body:**
```json
{
  "name": "Test Kategori",
  "slug": "test-kategori",
  "description": "Test için oluşturulmuş kategori",
  "is_active": true
}
```

**Expected Response (201):**
```json
{
  "id": "674a1b2c3d4e5f6a7b8c9d0e",
  "name": "Test Kategori",
  "slug": "test-kategori",
  "description": "Test için oluşturulmuş kategori",
  "image_url": null,
  "is_active": true,
  "created_at": "2026-03-20T12:00:00.000000",
  "updated_at": "2026-03-20T12:00:00.000000"
}
```

**Swagger ile Test:**
1. `/docs` sayfasına git
2. Önce `POST /auth/login` ile admin girişi yap, token al
3. Sağ üst "Authorize" → Bearer token gir
4. `POST /categories` → Try it out → Request body yapıştır → Execute

**cURL:**
```bash
# 1. Admin token al
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"AdminPass123"}' | jq -r '.access_token')

# 2. Kategori oluştur
curl -X POST http://localhost:8000/api/v1/categories \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Kategori","slug":"test-kategori","description":"Test için oluşturulmuş kategori","is_active":true}'
```

---

## Senaryo 2: Normal User ile Kategori Oluşturamama

| Alan | Değer |
|------|-------|
| **Endpoint** | `POST /api/v1/categories` |
| **Auth** | Bearer token (normal user) |
| **Expected Status** | 403 |

**Request Body:**
```json
{
  "name": "Yasak Kategori",
  "slug": "yasak-kategori",
  "description": "Normal kullanıcı ekleyemez",
  "is_active": true
}
```

**Expected Response (403):**
```json
{
  "detail": "Admin access required"
}
```

**Swagger ile Test:**
1. Authorize ile normal user token gir (admin değil)
2. `POST /categories` → Try it out → Execute

**cURL:**
```bash
# Normal user token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"testuser@example.com","password":"SecurePass123"}' | jq -r '.access_token')

curl -X POST http://localhost:8000/api/v1/categories \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Yasak Kategori","slug":"yasak-kategori","description":"Normal kullanıcı ekleyemez","is_active":true}'
# Beklenen: 403
```

---

## Senaryo 3: Admin ile Ürün Ekleme

| Alan | Değer |
|------|-------|
| **Endpoint** | `POST /api/v1/products` |
| **Auth** | Bearer token (admin) |
| **Expected Status** | 201 |

**Request Body:**
```json
{
  "name": "Test Ürün",
  "slug": "test-urun",
  "description": "Manuel test ürünü",
  "price": 29.99,
  "stock": 50,
  "category_id": "<CATEGORY_ID>",
  "brand": "Test Marka",
  "unit": "adet",
  "is_active": true
}
```
*`<CATEGORY_ID>` yerine geçerli bir kategori ObjectId (24 hex) yaz. Örn: `GET /categories` ile bir id al.*

**Expected Response (201):**
```json
{
  "id": "674a1b2c3d4e5f6a7b8c9d0f",
  "name": "Test Ürün",
  "slug": "test-urun",
  "description": "Manuel test ürünü",
  "price": 29.99,
  "stock": 50,
  "image_url": null,
  "category_id": "674a1b2c3d4e5f6a7b8c9d0e",
  "brand": "Test Marka",
  "unit": "adet",
  "is_active": true,
  "created_at": "2026-03-20T12:00:00.000000",
  "updated_at": "2026-03-20T12:00:00.000000"
}
```

**Swagger ile Test:**
1. Önce `GET /categories` ile bir category_id al
2. Admin token ile `POST /products` → Request body'de category_id yaz → Execute

**cURL:**
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"AdminPass123"}' | jq -r '.access_token')

# Önce bir kategori id al (seed_data.py çalıştırılmışsa mevcut)
CAT_ID=$(curl -s http://localhost:8000/api/v1/categories?limit=1 | jq -r '.items[0].id')

curl -X POST http://localhost:8000/api/v1/products \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"Test Urun\",\"slug\":\"test-urun-manuel\",\"description\":\"Manuel test\",\"price\":29.99,\"stock\":50,\"category_id\":\"$CAT_ID\",\"brand\":\"Test\",\"unit\":\"adet\",\"is_active\":true}"
```

---

## Senaryo 4: Geçersiz Kategori ile Ürün Ekleyememe

| Alan | Değer |
|------|-------|
| **Endpoint** | `POST /api/v1/products` |
| **Auth** | Bearer token (admin) |
| **Expected Status** | 404 |

**Request Body:**
```json
{
  "name": "Geçersiz Kategori Ürünü",
  "slug": "gecersiz-kategori-urunu",
  "description": "Olmayan kategori",
  "price": 10.00,
  "stock": 5,
  "category_id": "000000000000000000000000",
  "is_active": true
}
```

**Expected Response (404):**
```json
{
  "detail": "Category with id '000000000000000000000000' not found"
}
```

**Swagger:** `POST /products` → category_id olarak `000000000000000000000000` gir → Execute

**cURL:**
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"AdminPass123"}' | jq -r '.access_token')

curl -X POST http://localhost:8000/api/v1/products \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Gecersiz Urun","slug":"gecersiz-urun","description":"Test","price":10,"stock":5,"category_id":"000000000000000000000000","is_active":true}'
# Beklenen: 404
```

---

## Senaryo 5: Ürün Listeleme

| Alan | Değer |
|------|-------|
| **Endpoint** | `GET /api/v1/products` |
| **Auth** | Gerekmez (public) |
| **Expected Status** | 200 |

**Query Params (opsiyonel):**
- `skip`: 0 (varsayılan)
- `limit`: 50 (varsayılan, max 100)

**Expected Response (200):**
```json
{
  "items": [
    {
      "id": "674a1b2c3d4e5f6a7b8c9d0f",
      "name": "Süt 1L",
      "slug": "sut-1l",
      "description": "Günlük süt",
      "price": 24.99,
      "stock": 150,
      "image_url": null,
      "category_id": "674a1b2c3d4e5f6a7b8c9d0e",
      "brand": "Pınar",
      "unit": "litre",
      "is_active": true,
      "created_at": "2026-03-20T12:00:00",
      "updated_at": "2026-03-20T12:00:00"
    }
  ],
  "total": 19,
  "skip": 0,
  "limit": 50
}
```

**Swagger:** `GET /products` → Try it out → Execute

**cURL:**
```bash
curl "http://localhost:8000/api/v1/products?skip=0&limit=20"
```

---

## Senaryo 6: Ürün Detay Görüntüleme

| Alan | Değer |
|------|-------|
| **Endpoint** | `GET /api/v1/products/{product_id}` |
| **Auth** | Gerekmez (public) |
| **Expected Status** | 200 |

**Expected Response (200):**
```json
{
  "id": "674a1b2c3d4e5f6a7b8c9d0f",
  "name": "Süt 1L",
  "slug": "sut-1l",
  "description": "Günlük süt 1 litre",
  "price": 24.99,
  "stock": 150,
  "image_url": null,
  "category_id": "674a1b2c3d4e5f6a7b8c9d0e",
  "brand": "Pınar",
  "unit": "litre",
  "is_active": true,
  "created_at": "2026-03-20T12:00:00",
  "updated_at": "2026-03-20T12:00:00"
}
```

**Olmayan ID için Expected (404):**
```json
{
  "detail": "Product not found"
}
```

**Swagger:** `GET /products/{product_id}` → product_id gir → Execute

**cURL:**
```bash
PRODUCT_ID="674a1b2c3d4e5f6a7b8c9d0f"  # Geçerli ID ile değiştir
curl "http://localhost:8000/api/v1/products/$PRODUCT_ID"
```

---

## Senaryo 7: Category Filtreleme

| Alan | Değer |
|------|-------|
| **Endpoint** | `GET /api/v1/products?category_id={id}` |
| **Auth** | Gerekmez (public) |
| **Expected Status** | 200 |

**Query Params:**
- `category_id`: Geçerli kategori ObjectId (24 hex)

**Expected Response (200):**
```json
{
  "items": [ /* sadece o kategoriye ait ürünler */ ],
  "total": 4,
  "skip": 0,
  "limit": 50
}
```

**Swagger:** `GET /products` → category_id parametresine değer gir → Execute

**cURL:**
```bash
# Önce bir kategori id al
CAT_ID=$(curl -s "http://localhost:8000/api/v1/categories?limit=1" | jq -r '.items[0].id')
curl "http://localhost:8000/api/v1/products?category_id=$CAT_ID"
```

---

## Senaryo 8: Search ile Ürün Arama

| Alan | Değer |
|------|-------|
| **Endpoint** | `GET /api/v1/products?search={term}` |
| **Auth** | Gerekmez (public) |
| **Expected Status** | 200 |

**Query Params:**
- `search`: name veya description içinde aranacak metin

**Expected Response (200):**
```json
{
  "items": [ /* name/description'da "süt" geçen ürünler */ ],
  "total": 2,
  "skip": 0,
  "limit": 50
}
```

**Swagger:** `GET /products` → search parametresine "süt" yaz → Execute

**cURL:**
```bash
curl "http://localhost:8000/api/v1/products?search=süt"
curl "http://localhost:8000/api/v1/products?search=coca"
```

---

## Senaryo 9: min_price ve max_price Filtreleme

| Alan | Değer |
|------|-------|
| **Endpoint** | `GET /api/v1/products?min_price={x}&max_price={y}` |
| **Auth** | Gerekmez (public) |
| **Expected Status** | 200 |

**Query Params:**
- `min_price`: Minimum fiyat (>= 0)
- `max_price`: Maximum fiyat (>= 0)

**Expected Response (200):**
```json
{
  "items": [ /* 10 <= price <= 50 olan ürünler */ ],
  "total": 8,
  "skip": 0,
  "limit": 50
}
```

**Swagger:** `GET /products` → min_price: 10, max_price: 50 → Execute

**cURL:**
```bash
curl "http://localhost:8000/api/v1/products?min_price=10&max_price=50"
# Sadece min
curl "http://localhost:8000/api/v1/products?min_price=20"
# Sadece max
curl "http://localhost:8000/api/v1/products?max_price=30"
```

---

## Senaryo 10: Ürünü Soft Delete Yapma

| Alan | Değer |
|------|-------|
| **Endpoint** | `DELETE /api/v1/products/{product_id}` |
| **Auth** | Bearer token (admin) |
| **Expected Status** | 200 |

**Expected Response (200):**
```json
{
  "id": "674a1b2c3d4e5f6a7b8c9d0f",
  "name": "Test Ürün",
  "slug": "test-urun",
  "description": "...",
  "price": 29.99,
  "stock": 50,
  "image_url": null,
  "category_id": "...",
  "brand": "Test",
  "unit": "adet",
  "is_active": false,
  "created_at": "...",
  "updated_at": "..."
}
```
*`is_active` artık `false` olmalı.*

**Doğrulama:** Soft delete sonrası `GET /products` ve `GET /products/{id}` bu ürünü döndürmez (liste dışı, detay 404).

**Swagger:** Admin token ile `DELETE /products/{product_id}` → Execute

**cURL:**
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"AdminPass123"}' | jq -r '.access_token')

PRODUCT_ID="674a1b2c3d4e5f6a7b8c9d0f"
curl -X DELETE "http://localhost:8000/api/v1/products/$PRODUCT_ID" \
  -H "Authorization: Bearer $TOKEN"
# Beklenen: 200, response'ta is_active: false

# Doğrulama: artık 404 dönmeli
curl "http://localhost:8000/api/v1/products/$PRODUCT_ID"
# Beklenen: 404
```

---

## Özet Tablo

| # | Senaryo | Method | Endpoint | Auth | Expected |
|---|---------|--------|----------|------|----------|
| 1 | Admin kategori oluştur | POST | /categories | Admin | 201 |
| 2 | Normal user kategori oluşturamaz | POST | /categories | User | 403 |
| 3 | Admin ürün ekle | POST | /products | Admin | 201 |
| 4 | Geçersiz kategori ile ürün eklenemez | POST | /products | Admin | 404 |
| 5 | Ürün listele | GET | /products | - | 200 |
| 6 | Ürün detay | GET | /products/{id} | - | 200 / 404 |
| 7 | Category filtre | GET | /products?category_id= | - | 200 |
| 8 | Search | GET | /products?search= | - | 200 |
| 9 | Fiyat filtre | GET | /products?min_price=&max_price= | - | 200 |
| 10 | Soft delete | DELETE | /products/{id} | Admin | 200 |
