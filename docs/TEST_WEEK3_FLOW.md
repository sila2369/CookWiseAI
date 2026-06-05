# 3. Hafta - Ürün & Kategori Test Akışı

## Hızlı Test (Script)

```bash
# 1. Uygulamayı başlat
uvicorn app.main:app --reload

# 2. Admin kullanıcı oluştur (ilk kez)
python scripts/test_auth_flow.py

# 3. 3. Hafta akışını çalıştır
python scripts/test_week3_flow.py
```

## Manuel Test Akışı

### 1. Admin Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"AdminPass123"}'
```

Response: `access_token` al, sonraki isteklerde `Authorization: Bearer <TOKEN>` kullan.

### 2. Kategori Oluştur

```bash
curl -X POST http://localhost:8000/api/v1/categories \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"name":"Süt Ürünleri","slug":"sut-urunleri","description":"Süt ürünleri kategorisi","is_active":true}'
```

Response: `id` değerini al, ürün oluştururken `category_id` olarak kullan.

### 3. Ürün Oluştur

```bash
curl -X POST http://localhost:8000/api/v1/products \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "name":"Günlük Süt 1 Litre",
    "slug":"gunluk-sut-1-litre",
    "description":"Günlük taze süt",
    "price":24.99,
    "stock":50,
    "category_id":"<CATEGORY_ID>",
    "brand":"Pınar",
    "unit":"litre",
    "is_active":true
  }'
```

### 4. Ürünleri Listele (Public)

```bash
curl "http://localhost:8000/api/v1/products?skip=0&limit=20"
```

### 5. Ürün Detay Getir

```bash
curl "http://localhost:8000/api/v1/products/<PRODUCT_ID>"
```

### 6. Ürün Filtrele

```bash
# Kategoriye göre
curl "http://localhost:8000/api/v1/products?category_id=<CATEGORY_ID>"

# Arama (name/description)
curl "http://localhost:8000/api/v1/products?search=süt"

# Fiyat aralığı
curl "http://localhost:8000/api/v1/products?min_price=10&max_price=50"
```

### 7. Ürünü Pasife Çek (Soft Delete)

```bash
curl -X DELETE http://localhost:8000/api/v1/products/<PRODUCT_ID> \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
```

Sonrasında GET /products ve GET /products/{id} bu ürünü döndürmez (404).
