# Web + Mobil Ortak Backend

Bu backend hem web hem de mobil uygulama tarafından kullanılacak.

---

## API Base URL

| Ortam | URL |
|-------|-----|
| Local (geliştirme) | `http://localhost:8000` |
| Production | `https://api.cookwise.com` (örnek) |

**API prefix:** `/api/v1`  
**Tam URL:** `http://localhost:8000/api/v1`

---

## CORS (Web için)

`.env` içinde `CORS_ORIGINS`:

```env
# Tüm origin'lere izin (geliştirme)
CORS_ORIGINS=["*"]

# Sadece belirli domain'ler (production)
# CORS_ORIGINS=["https://app.cookwise.com","https://admin.cookwise.com"]
```

Web uygulamanız farklı portta (örn. 3000) çalışıyorsa `*` ile sorun olmaz.

---

## Mobil (React Native / Flutter)

Mobil uygulamalar browser CORS kullanmaz. Emulator/simulator için:

- **Android Emulator:** `http://10.0.2.2:8000` (localhost)
- **iOS Simulator:** `http://localhost:8000`
- **Fiziksel cihaz:** Bilgisayar IP'niz: `http://192.168.x.x:8000`

---

## Authentication

1. **Register:** `POST /api/v1/auth/register`
2. **Login:** `POST /api/v1/auth/login` → `access_token` al
3. **Sonraki istekler:** `Authorization: Bearer <access_token>`

---

## Endpoint Özeti

| Endpoint | Auth | Açıklama |
|----------|------|----------|
| POST /auth/register | Hayır | Kayıt |
| POST /auth/login | Hayır | Giriş |
| GET /users/me | Evet | Profil |
| GET /products | Hayır | Ürün listesi |
| GET /products/{id} | Hayır | Ürün detay |
| GET /categories | Hayır | Kategori listesi |
| POST /categories | Admin | Kategori oluştur |
| POST /products | Admin | Ürün oluştur |
