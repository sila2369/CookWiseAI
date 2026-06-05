# CookWise - Kurulum Kontrol Listesi

Projeyi çalıştırmadan önce kontrol etmeniz gerekenler.

---

## 1. `.env` Dosyası (Zorunlu)

`.env.example` dosyasını kopyalayıp `.env` oluşturun:

```bash
cp .env.example .env
```

### Doldurulması gereken alanlar

| Değişken | Açıklama | Örnek |
|----------|----------|-------|
| **MONGODB_URL** | MongoDB bağlantı adresi | `mongodb://localhost:27017` |
| **MONGODB_DB** | Veritabanı adı | `cookwise` |
| **SECRET_KEY** | JWT imzalama anahtarı (min 32 karakter) | Üret: `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| **APP_NAME** | Uygulama adı | `CookWise API` |

### MongoDB bağlantı örnekleri

```env
# Yerel MongoDB
MONGODB_URL=mongodb://localhost:27017

# Docker içinden
MONGODB_URL=mongodb://mongodb:27017

# MongoDB Atlas (cloud)
MONGODB_URL=mongodb+srv://kullanici:sifre@cluster.xxxxx.mongodb.net
```

---

## 2. Admin Kullanıcı (Test için)

Admin mail veya şifre `.env` veya config'de tanımlı değildir. Admin, MongoDB'de `is_admin: true` olan herhangi kullanıcıdır.

### Seçenek A: Script ile admin oluştur

```bash
python scripts/create_admin.py
```

**Varsayılan admin:**
- Email: `admin@cookwise.com`
- Şifre: `Admin123!`

### Seçenek B: API ile kayıt + manuel admin

1. `POST /api/v1/auth/register` ile kayıt ol
2. MongoDB'de o kullanıcının `is_admin: true` yap

```javascript
// mongosh veya MongoDB Compass
db.users.updateOne(
  { email: "senin@email.com" },
  { $set: { is_admin: true } }
)
```

---

## 3. Örnek Veri (İsteğe bağlı)

Kategoriler ve ürünler için:

```bash
python scripts/seed_data.py
```

---

## 4. Hızlı Başlangıç Özeti

```bash
# 1. .env oluştur ve doldur
cp .env.example .env
# MONGODB_URL, MONGODB_DB, SECRET_KEY, APP_NAME düzenle

# 2. MongoDB'nin calistigindan emin ol
mongod   # veya docker-compose up -d mongodb

# 3. Admin olustur
python scripts/create_admin.py

# 4. Ornek veri ekle (opsiyonel)
python scripts/seed_data.py

# 5. Uygulamayi baslat
uvicorn app.main:app --reload

# 6. Tarayicida test et
# http://localhost:8000/docs
# Login: admin@cookwise.com / Admin123!
```

---

## 5. Test scriptleri için not

| Script | Admin credentials |
|--------|-------------------|
| `test_week3_flow.py` | `admin@example.com` / `AdminPass123` |
| `test_auth_flow.py` | `admin@example.com` / `AdminPass123` |
| `create_admin.py` | `admin@cookwise.com` / `Admin123!` |

Test scriptlerini çalıştırmak için önce `create_admin.py` içindeki email/şifreyi kullanın veya scriptlerdeki credentials'ı kendi admin bilgilerinize göre güncelleyin.
