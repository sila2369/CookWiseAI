# 🚀 CookWise Backend - Hızlı Çalıştırma Kılavuzu

> ⚠️ **Motor 3.3.2 uyumlu yapı güncellenmiştir!**

## 📋 Adım Adım Kurulum

### 1️⃣ Virtual Environment Oluştur
```powershell
python -m venv venv
venv\Scripts\activate
```

### 2️⃣ Bağımlılıkları Yükle
```powershell
pip install -r requirements.txt
```

### 3️⃣ .env Dosyası Oluştur
```powershell
copy .env.example .env
```

### 4️⃣ Config'i Doğrula
```powershell
python check_config.py
```

**Beklenen çıktı:**
```
✅ CookWise Config Checker
✅ .env dosyası
✅ requirements.txt
✅ Config yüklendi
✅ Konfigürasyon Özeti
✅ Güvenlik Kontrolü
⚠️ MongoDB Bağlantısı (opsiyonel)
✅ Tüm zorunlu kontroller başarılı!
```

---

## 🎯 API'yi Çalıştırma

### Seçenek A: Development Server (Tavsiye Edilen)
```powershell
python run_dev.py
```

**Çıktı:**
```
🚀 CookWise API - Development Server
================================================
App Name:    CookWise API
Environment: development
Host:        0.0.0.0
Port:        8000
Debug Mode:  True
================================================

📖 Swagger UI: http://0.0.0.0:8000/docs
🏥 Health Check: http://0.0.0.0:8000/api/v1/health/

INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

### Seçenek B: Doğrudan Uvicorn ile
```powershell
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Seçenek C: Python Modül Olarak
```powershell
python -m app.main
```

---

## 🧪 API'yi Test Etme

### Quick Test (MongoDB olmadan)
```powershell
python test_quick.py
```

Beklenen çıktı:
```
✅ FastAPI app yüklendi
✅ Settings: CookWise API (development)
✅ GET / → 200
✅ GET /api/v1/health/ → 200
✅ GET /docs (Swagger UI) → 200
✅ Tüm testler başarılı!
```

### Browser'de Test Etme

**API Endpoints:**
- Home: http://localhost:8000/
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health Check: http://localhost:8000/api/v1/health/

**curl ile:**
```powershell
curl http://localhost:8000/api/v1/health/
```

---

## 🔧 MongoDB Kurulum (Opsiyonel - Hali Yazılı)

API şu anda MongoDB olmadan çalışır. Veritabanı işlemleri için:

### Option 1: Docker ile MongoDB
```powershell
docker run -d -p 27017:27017 --name cookwise-mongo mongo:7.0
```

### Option 2: Docker Compose ile (Tümü Birlikte)
```powershell
docker-compose up
```

### Option 3: Local MongoDB
1. [MongoDB indır](https://www.mongodb.com/try/download/community)
2. Yükle
3. `mongod` komutunu çalıştır

---

## 📝 Dosya Yapısı

```
CookWise/
├── app/
│   ├── core/
│   │   ├── config.py          ← Pydantic Settings (.env'yi oku)
│   │   ├── database.py        ← Motor async MongoDB (fixed!)
│   │   └── security.py        ← JWT token + password hashing
│   ├── routers/
│   │   └── health.py          ← Health check endpoints
│   └── main.py                ← FastAPI app
│
├── run_dev.py                 ← ✨ Yeni: Development server launcher
├── check_config.py            ← Config doğrulama
├── test_quick.py              ← ✨ Yeni: MongoDB olmadan quick test
├── requirements.txt           ← Python dependencies
├── .env.example               ← Environment şablonu
├── .env                       ← Actual config (.gitignore'da)
├── docker-compose.yml         ← Docker orchestration (updated)
├── Dockerfile                 ← API container
└── SETUP.md                   ← Detaylı rehber
```

---

## ✅ Yapılması Gereken İşler

- [x] Motor 3.3.2 uyumluluğu sağlandi
- [x] Config doğrulama scripti (`check_config.py`)
- [x] Development launcher (`run_dev.py`)
- [x] Quick test script'i (`test_quick.py`)
- [x] Docker-compose güncellemesi
- [ ] User authentication router
- [ ] Product CRUD endpoints
- [ ] Order management
- [ ] Payment integration

---

## 🐛 Sık Karşılaşılan Sorunlar

### ❌ "ModuleNotFoundError: No module named 'app'"
**Çözüm:** `run_dev.py` veya `test_quick.py` kullan
```powershell
python run_dev.py  # Tavsiye edilen
```

### ❌ "cannot import name 'AsyncClient'"
**Çözüm:** Motor 3.3.2 uyumluluğu güncellenmiştir
```bash
pip install --upgrade motor==3.3.2
python test_quick.py  # Başarılı test et
```

### ❌ "MongoDB bağlantı hatası"
**Çözüm:** MongoDB zorunlu değildir, `test_quick.py` ile test et
```powershell
python test_quick.py  # Başarılı olmalı
# MongoDB'ye ihtiyaç duyarsan:
docker run -d -p 27017:27017 mongo:7.0
```

### ❌ ".env dosyası bulunamadı"
```powershell
copy .env.example .env
```

---

## 🎓 Sonraki Adımlar

### 1. User Modeli Ekle
```python
# app/models/user.py
from datetime import datetime
from typing import Optional

class User:
    def __init__(self, email: str, password_hash: str, **kwargs):
        self.email = email
        self.password_hash = password_hash
        self.created_at = datetime.utcnow()
```

### 2. User Schema Oluştur
```python
# app/schemas/user.py
from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "securepass123"
            }
        }
```

### 3. User Service Yaz
```python
# app/services/user_service.py
from app.core.database import Database
from app.core.security import hash_password

class UserService:
    async def create_user(self, user_data):
        db = Database.get_database()
        hashed_password = hash_password(user_data['password'])
        # ...
```

---

## 📊 API Mimarisi

```
Browser / Mobile ↓
        ↓
   [FastAPI] ← app/main.py
        ↓
  [Routers] ← app/routers/
     ↙ ↘
    ↙   ↘
[Health] [Users] ← Gelecek
    ↓     ↓
  [Services] ← app/services/
    ↓     ↓
 [Database] ← Motor + MongoDB
    ↓
  [Security] ← JWT, Password Hash
```

---

## 🚀 Production Deployment

### Docker ile
```powershell
docker-compose up -d
# URL: http://your-server:8000/docs
```

### Standalone
```powershell
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app.main:app
```

---

## 📞 Destek

❓ Soru mu var?
- Config: `python check_config.py`
- Test: `python test_quick.py`
- Help: `python run_dev.py --help`

---

**Version: 1.0.1 | Mart 2026**
