# 🚀 CookWise Backend - Kurulum ve Çalıştırma Rehberi

## 📋 İçindekiler
1. [Gereksinimler](#gereksinimler)
2. [Kurulum Adımları](#kurulum-adımları)
3. [Environment Yapılandırması](#environment-yapılandırması)
4. [Çalıştırma](#çalıştırma)
5. [Test Etme](#test-etme)
6. [Sorun Giderme](#sorun-giderme)

---

## 🔧 Gereksinimler

- **Python:** 3.10+ (test: 3.11)
- **MongoDB:** 5.0+ (local veya Docker)
- **pip:** Python paket yöneticisi
- **Virtual Environment:** Önerilir

---

## 📦 Kurulum Adımları

### 1️⃣ Repository'yi Klonla veya Hazırla
```bash
cd CookWise
```

### 2️⃣ Virtual Environment Oluştur ve Aktifleştir

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3️⃣ Bağımlılıkları Yükle
```bash
pip install -r requirements.txt
```

> Tüm paketler `requirements.txt`'de listelenir:
> - FastAPI & Uvicorn
> - Motor (async MongoDB driver) & PyMongo
> - python-jose (JWT)
> - passlib & bcrypt (password hashing)
> - pydantic & pydantic-settings (validation)
> - python-dotenv (env yönetimi)
> - Development tools (pytest, black, flake8)

---

## 🔐 Environment Yapılandırması

### 1️⃣ .env Dosyası Oluştur

```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

### 2️⃣ .env Dosyasını Düzenle

```env
# ==================== UYGULAMA AYARLARI ====================
APP_NAME=CookWise API
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8000

# ==================== MONGODB AYARLARI ====================
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB=cookwise

# ==================== JWT AYARLARI ====================
# ⚠️ ÖNEMLI: Production'da özel bir key oluştur!
SECRET_KEY=your-super-secret-key-min-32-chars-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# ==================== DEBUG ====================
DEBUG=True
```

### 3️⃣ Production İçin Güçlü SECRET_KEY Oluştur

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Çıktıyı .env dosyasındaki `SECRET_KEY`'e yapıştır.

---

## 🎯 Çalıştırma

### Seçenek A: Direct Python ile (Development)

```bash
# Virtual env aktif olduğunu kontrol et
# (Windows: venv\Scripts\activate benzeri çıktı görülmeli)

python app/main.py
```

Beklenen çıktı:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

### Seçenek B: Uvicorn ile (Production-benzer)

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Seçenek C: Docker ile

```bash
# Tüm servisleri başlat (MongoDB + API)
docker-compose up

# Sadece API'yi başlat (MongoDB local'de varsa)
docker-compose up api
```

---

## 🧪 Test Etme

### 1️⃣ API'nin Çalışıp Çalışmadığını Kontrol Et

**Browser'de açmak:**
- Home: `http://localhost:8000/`
- Swagger Docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

**curl ile:**
```bash
curl http://localhost:8000/api/v1/health/
```

Beklenen çıktı:
```json
{
  "status": "healthy",
  "timestamp": "2026-03-18T10:30:00.000000",
  "app_name": "CookWise API",
  "version": "1.0.0"
}
```

### 2️⃣ MongoDB Bağlantısını Test Et

**Swagger UI açıp:**
1. `GET /api/v1/health/detailed` endpoint'ine tıkla
2. "Try it out" → "Execute"

Beklenen çıktı (veritabanı bağlı ise):
```json
{
  "status": "healthy",
  "timestamp": "2026-03-18T10:30:00.000000",
  "app_name": "CookWise API",
  "version": "1.0.0",
  "environment": "development",
  "database": {
    "status": "connected",
    "name": "cookwise"
  }
}
```

### 3️⃣ Unit Tests Çalıştır

```bash
pytest
```

Verbose mode:
```bash
pytest -v
```

Coverage ile:
```bash
pytest --cov=app
```

---

## MongoDB Kurulumu

### Seçenek A: Local MongoDB (Windows)

1. [MongoDB Community Edition İndir](https://www.mongodb.com/try/download/community)
2. Yükle (varsayılan ayarlar)
3. Terminal'de `mongod` komutunu çalıştır

### Seçenek B: Docker ile MongoDB

```bash
# Sadece MongoDB'yi başlat (arka planda)
docker run -d \
  --name cookwise-mongodb \
  -p 27017:27017 \
  -v mongodb_data:/data/db \
  mongo:7.0
```

### Seçenek C: MongoDB Atlas (Cloud)

1. [mongodb.com/atlas](https://www.mongodb.com/atlas) kayıt ol
2. Cluster oluştur
3. Connection string'i kopyala
4. `.env` dosyasında `MONGODB_URL` güncelle:
```env
MONGODB_URL=mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority
```

---

## 📝 Dosya Açıklamaları

| Dosya | Açıklama |
|-------|----------|
| **app/main.py** | FastAPI uygulaması, startup/shutdown, middleware'lar |
| **app/core/config.py** | Pydantic Settings - environment değişkenlerini `.env`'den oku |
| **app/core/database.py** | MongoDB async bağlantısı (Motor) |
| **app/core/security.py** | JWT token işlemleri & password hashing |
| **app/routers/health.py** | Health check endpoint'leri |
| **.env** | Environment değişkenleri (git'e ekleme!) |
| **requirements.txt** | Python bağımlılıkları |
| **docker-compose.yml** | Docker orchestration |

---

## 🐛 Sorun Giderme

### ❌ "ModuleNotFoundError: No module named 'fastapi'"
**Çözüm:**
```bash
# Virtual env aktif olduğunu kontrol et
pip install -r requirements.txt
```

### ❌ "MongoDB bağlantı hatası"
**Çözüm:**
1. MongoDB'nin çalışıp çalışmadığını kontrol et:
   ```bash
   # MongoDB running mi?
   mongosh  # Bağlanmayı dene
   ```
2. `.env`'de `MONGODB_URL` doğru olduğunu kontrol et
3. Firewall ayarlarını kontrol et (port 27017)

### ❌ "Port 8000 kullanımda"
**Çözüm:**
```bash
# Farklı bir port kullan
python app/main.py --port 8001

# veya .env'de değiştir
APP_PORT=8001
```

### ❌ ".env dosyası bulunamadı"
```bash
cp .env.example .env
# Sonra .env'yi düzenle
```

### ❌ "SECRET_KEY çok kısa"
**Hata:** `Pydantic validation error`
**Çözüm:** `.env`'de `SECRET_KEY` en az 32 karakterli bir string olmalı

---

## ✅ Başarılı Kurulum Kontrol Listesi

- [ ] Virtual environment oluşturuldu
- [ ] Bağımlılıklar yüklendi (`pip install -r requirements.txt`)
- [ ] `.env` dosyası oluşturuldu ve düzenlendi
- [ ] MongoDB çalışıyor (`mongosh` ile bağlanabiliyor)
- [ ] `python app/main.py` çalışıyor
- [ ] `http://localhost:8000/api/v1/health/` yanıt veriyor
- [ ] Swagger UI açılıyor (`http://localhost:8000/docs`)

---

## 🎓 Sonraki Adımlar

1. **User modeli ekle** → `app/models/`, `app/schemas/` kısımlarını doldur
2. **User router yazı** → `app/routers/users.py` oluştur
3. **Authentication middleware** → `app/dependencies/auth.py` yaz
4. **Product CRUD** → Product model ve endpoints ekle
5. **Order yönetimi** → Order servisleri geliştir

---

## 📞 Yardım ve Destek

**Hata mesajı var mı?**
1. Hata mesajını kopyala
2. [GitHub Issues](https://github.com/your-repo/issues) açabilirsin
3. Veya:
   - MongoDB çalışıyor mu? → `mongosh`
   - Virtual env aktif? → `pip list`
   - Port meşgul? → `netstat -an | grep 8000`

---

**Ver: 1.0.0 | Mart 2026**
