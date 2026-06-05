# 🚀 API Çalıştırma Rehberi

## FastAPI Backend'i Başlatmak

### Seçenek 1: Development Server (Önerilen)

```bash
python run_dev.py
```

**Neler olur:**
- `.env` dosyasını otomatik yükler
- Hot-reload aktif olur (dosyayı kaydetince otomatik restart)
- Debug mode açık
- http://localhost:8000 adresinde erişilebilir

**Çıktı örneği:**
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

---

### Seçenek 2: Uvicorn ile Doğrudan

```bash
# Basic
uvicorn app.main:app --reload

# Advanced (tüm seçenekler)
uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --reload \
  --log-level info \
  --access-log
```

**Parametreler:**
- `app.main:app` - Hangi modülün hangi FastAPI instance'ını çalıştıracak
- `--host 0.0.0.0` - Tüm IP'lerden erişim
- `--port 8000` - Port numarası
- `--reload` - Code değişikliğinde otomatik restart
- `--log-level info` - Log detayı
- `--access-log` - HTTP request logları

---

### Seçenek 3: Python Modülü Olarak

```bash
python -m uvicorn app.main:app --reload
```

---

### Seçenek 4: Production (Gunicorn + Uvicorn)

```bash
# Worker process ile
gunicorn \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  -b 0.0.0.0:8000 \
  app.main:app
```

**Nedir:**
- 4 worker process
- Production-ready
- Better resource management

---

## 🌐 API Erişim

### Browser'de
- Swagger UI (Interaktif): **http://localhost:8000/docs**
- ReDoc (Alternatif): **http://localhost:8000/redoc**
- OpenAPI JSON: **http://localhost:8000/openapi.json**

### Curl ile
```bash
# Health check
curl http://localhost:8000/api/v1/health/

# Status
curl http://localhost:8000/api/v1/status

# Root
curl http://localhost:8000/
```

### Çıktı
```json
{
  "status": "healthy",
  "timestamp": "2026-03-18T10:30:00.000000",
  "app_name": "CookWise API",
  "version": "1.0.0"
}
```

---

## 📝 Mevcut Endpoints

| Method | URL | Açıklama | Tags |
|--------|-----|----------|------|
| GET | `/` | API bilgileri | root |
| GET | `/api/v1/status` | API durumu | status |
| GET | `/api/v1/health/` | Basit health check | health |
| GET | `/api/v1/health/detailed` | Detaylı health check (DB kontrol) | health |

---

## 🏗️ Mimarı

```
Browser/Mobile
     ↓
  [Uvicorn] ← ASGI Server
     ↓
[FastAPI App] ← app/main.py
     ↓
┌─────────────────────┐
│   Middleware        │
├─────────────────────┤
│ - CORS              │
│ - Logging           │
│ - Exception Handler │
└─────────────────────┘
     ↓
┌─────────────────────┐
│    Routers          │
├─────────────────────┤
│ - Health            │
│ - Users (soon)      │
│ - Products (soon)   │
└─────────────────────┘
     ↓
┌─────────────────────┐
│   Services          │
├─────────────────────┤
│ - Business Logic    │
│ - Validation        │
└─────────────────────┘
     ↓
┌─────────────────────┐
│   Database          │
├─────────────────────┤
│ - MongoDB (Motor)   │
│ - Async/Await       │
└─────────────────────┘
```

---

## ⚡ Hot Reload (Development)

Kod değişikliklerinde otomatik restart:

```bash
python run_dev.py
# veya
uvicorn app.main:app --reload
```

**Deneyelim:**
1. API çalışıyor (http://localhost:8000/docs açık)
2. `app/main.py` içinde bir docstring değiştir
3. Dosyayı kaydet (Ctrl+S)
4. Terminal'de otomatik restart görülecek
5. Browser'de refresh (F5) et - yeni versiyon yüklendi

---

## 🔧 .env Dosyası

```env
# Çalıştırma
APP_ENV=development          # development | staging | production
DEBUG=True                   # True | False

# Server
APP_HOST=0.0.0.0
APP_PORT=8000

# API
API_PREFIX=/api/v1
APP_NAME=CookWise API
```

---

## 📊 Log Seviyeleri

```bash
# Debug (çok detaylı)
uvicorn app.main:app --log-level debug

# Info (normal)
uvicorn app.main:app --log-level info

# Warning (sadece uyarılar)
uvicorn app.main:app --log-level warning

# Error (sadece hatalar)
uvicorn app.main:app --log-level error
```

---

## 🚨 Sorun Giderme

### Port zaten kullanımda
```bash
# Farklı port kullan
uvicorn app.main:app --port 8001

# veya, port'u boşala
# Windows: netstat -ano | findstr :8000
# Linux/Mac: lsof -i :8000
```

### Module import hatası
```bash
# Virtual environment aktif olduğunu kontrol et
# Bak: (venv) başında var mı Terminal'de?
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
```

### Slow reloads
```bash
# Reload geciktiyse reload zaman aşımını artır
uvicorn app.main:app --reload-delay 2
```

---

## 💡 İpuçları

### 1. Swagger UI'da Test Et
http://localhost:8000/docs açıp:
- Endpoint'leri görebilirsin
- "Try it out" ile test edebilirsin
- Request/response görebilirsin

### 2. Curl Öğren
```bash
# Basic request
curl http://localhost:8000/api/v1/health/

# Header ekle
curl -H "Content-Type: application/json" http://localhost:8000/

# POST request
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com"}'
```

### 3. Logging Kontrol Et
Terminal'de API loglarını takip et:
```
INFO:     Application startup complete
INFO:     GET /api/v1/health/ 200 OK
INFO:     POST /users 201 Created
```

---

## 📚 Sonraki Adımlar

1. **User Router Ekle**
   ```python
   # app/routers/users.py
   from fastapi import APIRouter
   
   router = APIRouter(prefix="/users", tags=["users"])
   
   @router.post("/", summary="Create User")
   async def create_user():
       pass
   ```

2. **main.py'ye Ekle**
   ```python
   from app.routers import users_router
   app.include_router(users_router, prefix=settings.API_PREFIX)
   ```

3. **Yeniden çalıştır**
   ```bash
   python run_dev.py
   ```

---

**Happy Coding! 🎉**
