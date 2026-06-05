# Auth Test Akışı

## Test Sırası

1. **Register** - Yeni kullanıcı kaydı
2. **Login** - JWT token al
3. **Authorize** - Token'ı header'a ekle
4. **GET /users/me** - Profil bilgisi (tüm giriş yapmış kullanıcılar)
5. **GET /admin/test** - Sadece admin (is_admin=True) erişebilir

---

## Swagger UI ile Test

1. `http://localhost:8000/docs` aç
2. **POST /api/v1/auth/register** → Kayıt ol
3. **POST /api/v1/auth/login** → Giriş yap, `access_token` kopyala
4. Sağ üst **Authorize** → Token yapıştır → Authorize
5. **GET /api/v1/users/me** → Try it out → Execute (200)
6. **GET /api/v1/admin/test** → Try it out → Execute
   - Normal user: 403 Forbidden
   - Admin user: 200 OK

### Admin Kullanıcı Oluşturma

Varsayılan kayıt `is_admin=False` atar. Test için admin:

```bash
# MongoDB shell veya Compass
use cookwise
db.users.updateOne(
  { email: "admin@example.com" },
  { $set: { is_admin: true } }
)
```

---

## cURL ile Test

```bash
# 1. Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"full_name":"Test User","email":"test@example.com","password":"SecurePass123"}'

# 2. Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"SecurePass123"}' \
  | jq -r '.access_token')

# 3-4. /users/me
curl -X GET http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer $TOKEN"

# 5. /admin/test (403 if not admin)
curl -X GET http://localhost:8000/api/v1/admin/test \
  -H "Authorization: Bearer $TOKEN"
```

---

## Python Script ile Test

```bash
python scripts/test_auth_flow.py
```

Script otomatik olarak:
- Normal ve admin user kaydeder
- Admin'ı MongoDB'de is_admin yapar
- Login → /users/me → /admin/test akışını test eder
