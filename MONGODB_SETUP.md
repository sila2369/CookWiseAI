
# MongoDB Bağlantı Yapısı - Kapsamlı Rehber

## 📋 İçindekiler

1. [Teknoloji Seçimi](#teknoloji-seçimi-neden-motor)
2. [Mimarı](#mimarı-merkezi-yönetim)
3. [Lifecycle Yönetimi](#lifecycle-yönetimi)
4. [Kullanım Örnekleri](#kullanım-örnekleri)
5. [Dependency Injection](#dependency-injection)
6. [Collection Operasyonları](#collection-operasyonları)
7. [Health Checks](#health-checks)
8. [Troubleshooting](#troubleshooting)

---

## 🎯 Teknoloji Seçimi: Neden Motor?

### Motor mı, PyMongo mu?

| Özellik | Motor | PyMongo |
|---------|-------|---------|
| **Async/Await** | ✅ Full support | ❌ Blocking calls |
| **FastAPI Uyumlu** | ✅ Perfect | ❌ Thread-based |
| **Eş zamanlılık** | ✅ N connectors | ❌ Thread limited |
| **WebSocket** | ✅ Possible | ❌ Difficult |
| **Performance** | ✅ Non-blocking | ❌ Blocking threads |
| **Learning Curve** | ⭐ Easy | ⭐ Easy |
| **Production Ready** | ✅ Yes | ✅ Yes |

### Neden Motor Seçtik?

✅ **Non-blocking I/O** - FastAPI'nin asycio döngüsünü bloke etmez  
✅ **Connection Pooling** - Otomatik olarak 10-50 concurrent connections  
✅ **PyMongo Kompabilitesi** - Aynı API'yi bildiğin Motor async'idir  
✅ **Scalability** - Binlerce simultaneous request'i handle edebilir  
✅ **Development** - Hot-reload ile mükemmel çalışır  

### Motor 3.3.2 + PyMongo 4.5.0

Bu proje şu versiyonları kullanıyor:
```
motor==3.3.2        # Async MongoDB driver
pymongo==4.5.0      # Motor'ün bağımlılığı (verified compatible)
```

---

## 🏗️ Mimarı: Merkezi Yönetim

### Dosya Yapısı
```
app/
├── core/
│   ├── database.py          # 👈 Database bağlantı yönetimi
│   ├── config.py            # .env değişkenleri
│   └── security.py          # JWT & password
├── routers/
│   └── health.py            # ✅ Health check endpoints
└── main.py                  # FastAPI app + lifespan
```

### Database Sınıfı (app/core/database.py)

```python
class Database:
    # Class variables - singleton pattern
    client: Optional[Any] = None    # Motor AsyncClient
    db: Optional[Any] = None        # Database instance
    connected: bool = False          # Connection status
    
    @classmethod
    async def connect_db():      # Startup'ta çağır
    
    @classmethod  
    async def close_db():        # Shutdown'da çağır
    
    @classmethod
    def get_database():          # Dependency injection
    
    @classmethod
    async def get_collection():  # Collection erişimi
    
    @classmethod
    async def create_indexes():  # Performance optimization
```

### Connection Pool Yapısı

Motor otomatik olarak connection pool yönetir:

```
┌─────────────────────────────────────────┐
│     FastAPI Application                 │
│  (async requests handling)              │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│     Motor AsyncClient                   │
│  (Connection Pool Manager)              │
│  ┌────────────────────────────────────┐ │
│  │  Connection 1                      │ │
│  │  Connection 2                      │ │
│  │  ...                               │ │
│  │  Connection 10-50 (adaptive)       │ │
│  └────────────────────────────────────┘ │
└──────────────┬──────────────────────────┘
               │
               ▼
        MongoDB Server
        (localhost:27017)
```

### Graceful Fallback Mekanizması

MongoDB bağlı değilse, API yine de çalışır:

```python
# ✅ Safer pattern
db = Database.get_database()  # None döner
if db is None:
    # Fallback: return default data, use cache, etc.
    return {"data": []}

# ✅ Check status
if Database.is_connected():
    # Use database
    ...
else:
    # Use alternatives
    ...
```

---

## ⚙️ Lifecycle Yönetimi

### Startup Events (app/main.py)

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ▶️ STARTUP
    logger.info("🚀 Uygulama başlatılıyor...")
    
    # 1. MongoDB'ye bağlan
    await Database.connect_db()
    
    # 2. İndeksler oluştur (performance)
    if Database.is_connected():
        await Database.create_indexes()
    
    logger.info("✅ Startup tamamlandı")
    
    yield  # App is running
    
    # ⏹️ SHUTDOWN
    logger.info("🛑 Uygulama kapatılıyor...")
    await Database.close_db()
    logger.info("✅ Shutdown tamamlandı")
```

### .env Yapılandırması

```bash
# MongoDB bağlantı bilgileri (.env)
MONGODB_URL=mongodb://localhost:27017/
MONGODB_DB=cookwise

# Local development
MONGODB_URL=mongodb://mongodb:27017/  # Docker container
MONGODB_DB=cookwise_dev

# Production (MongoDB Atlas)
MONGODB_URL=mongodb+srv://user:password@cluster.mongodb.net/
MONGODB_DB=cookwise_prod
```

---

## 💡 Kullanım Örnekleri

### Örnek 1: Dependency Injection (Önerilen)

```python
from fastapi import APIRouter, Depends
from app.core.database import get_database

router = APIRouter(prefix="/users")

@router.get("/")
async def list_users(db = Depends(get_database)):
    """
    FastAPI otomatik olarak get_database() çağırır.
    MongoDB bağlıysa db = Database object
    Değilse db = None
    """
    if db is None:
        return []
    
    users = db["users"]
    return await users.find().to_list(100)
```

### Örnek 2: Direct Collection Access

```python
@router.post("/")
async def create_user(user: UserCreate):
    """
    Collection'ı doğrudan eriş
    """
    
    users_col = await Database.get_collection("users")
    if users_col is None:
        raise HTTPException(status_code=503, detail="DB unavailable")
    
    # Insert
    result = await users_col.insert_one({
        "email": user.email,
        "full_name": user.full_name,
        "created_at": datetime.utcnow()
    })
    
    return {"id": str(result.inserted_id)}
```

### Örnek 3: CRUD Operasyonları

```python
# 1. Okuma
user = await Database.find_one("users", {"email": "user@example.com"})

# 2. Yazan
users = await Database.find_many("products", {"category": "food"}, limit=50)

# 3. Oluşturma
user_id = await Database.insert_one("users", {
    "email": "new@example.com",
    "full_name": "John Doe"
})

# 4. Güncelleme
updated = await Database.update_one(
    "users",
    {"_id": ObjectId(user_id)},
    {"full_name": "Jane Doe"}
)

# 5. Silme
deleted = await Database.delete_one(
    "users",
    {"_id": ObjectId(user_id)}
)
```

---

## 🔌 Dependency Injection

FastAPI's `Depends()` sistemini kullanarak injection yapılır.

### Basit Versiyonu

```python
async def get_database() -> Any:
    return Database.get_database()
```

### Router'da Kullanım

```python
from fastapi import Depends
from app.core.database import get_database

@router.get("/users")
async def get_users(db = Depends(get_database)):
    if db is None:
        return []
    return await db["users"].find().to_list(100)
```

### Birden Fazla Dependencies

```python
@router.post("/order")
async def create_order(
    order: OrderCreate,
    current_user = Depends(get_current_user),  # Auth
    db = Depends(get_database)                   # DB
):
    # current_user'dan user_id al
    # db ile database operasyonları yap
    pass
```

---

## 🗄️ Collection Operasyonları

### İndeksler (Performance)

```python
# Startup'ta otomatik oluşturulur
await Database.create_indexes()

# Manual olarak:
users_col = db["users"]
await users_col.create_index("email", unique=True)
await users_col.create_index("created_at")
```

### Motor Collection Methods

```python
users_col = db["users"]

# Find one
user = await users_col.find_one({"email": "user@example.com"})

# Find many
users = await users_col.find({"status": "active"}).to_list(100)

# Count
count = await users_col.count_documents({"role": "admin"})

# Insert
result = await users_col.insert_one({"email": "..."})
user_id = result.inserted_id

# Update
result = await users_col.update_one(
    {"_id": user_id},
    {"$set": {"status": "inactive"}}
)

# Delete
result = await users_col.delete_one({"_id": user_id})

# Bulk operations
await users_col.insert_many([{...}, {...}])
```

### Aggregation Pipeline

```python
# Complex queries
pipeline = [
    {"$match": {"status": "active"}},
    {"$group": {"_id": "$category", "count": {"$sum": 1}}},
    {"$sort": {"count": -1}},
    {"$limit": 10}
]

results = await users_col.aggregate(pipeline).to_list(None)
```

---

## 🏥 Health Checks

### Endpoint'ler

| Path | Status | Açıklama |
|------|--------|------------|
| `GET /api/v1/health/` | 200 | Basit health check |
| `GET /api/v1/health/db` | 200 | Veritabanı durumu |
| `GET /api/v1/health/detailed` | 200 | Full sistem raporu |
| `GET /api/v1/health/ready` | 200/503 | Readiness probe |
| `GET /api/v1/health/live` | 200 | Liveness probe |

### Test

```bash
# Basit health check
curl http://localhost:8000/api/v1/health/

# Detaylı rapor
curl http://localhost:8000/api/v1/health/detailed | jq

# Veritabanı durumu
curl http://localhost:8000/api/v1/health/db | jq
```

### Python ile

```python
import requests

# DB health
r = requests.get("http://localhost:8000/api/v1/health/db")
print(r.json())
# {
#   "status": "ok",
#   "database": {
#       "connected": false,
#       "status": "disabled"  or "connected" or "error"
#   }
# }

# Detailed system status
r = requests.get("http://localhost:8000/api/v1/health/detailed")
print(r.json())
# {
#   "status": "healthy",
#   "database": {"status": "disabled", "collections": [...]},
#   "api": {...},
#   "timestamp": "..."
# }
```

---

## 🛠️ Troubleshooting

### Problem 1: "Motor AsyncClient not found"

**Çözüm:**
```bash
pip install --force-reinstall motor==3.3.2 pymongo==4.5.0
```

### Problem 2: "Connection refused"

```bash
# MongoDB'yi Docker'da çalıştır
docker-compose up -d mongodb

# veya local:
mongod --dbpath /path/to/data
```

### Problem 3: "Database disabled in health check"

```
Bu normaldir! MongoDB opsiyonel olarak tasarlandı.
API MongoDB olmadan da çalışır.

Log'ta göreceksin:
⚠️  Motor import hatası: ...
```

### Problem 4: "Timeout on connection"

```python
# .env kontrol et
MONGODB_URL=mongodb://localhost:27017/  # URL doğru mu?
MONGODB_DB=cookwise                      # DB adı doğru mu?

# Bağlantı test et
python -c "import motor.motor_asyncio; print('Motor OK')"
```

### Problem 5: "Too many connections"

```python
# Connection pool ayarlarını .env'e ekle:
MONGO_MAX_POOL_SIZE=50
MONGO_MIN_POOL_SIZE=10

# app/core/database.py'de:
cls.client = AsyncClient(
    settings.MONGODB_URL,
    maxPoolSize=50,
    minPoolSize=10
)
```

---

## 📚 Best Practices

### ✅ DO

```python
# 1. Dependency injection kullan
async def get_users(db = Depends(get_database)):
    pass

# 2. None kontrol et
if db is None:
    return {"data": []}

# 3. İndeksler oluştur
await Database.create_indexes()

# 4. Error handling
try:
    result = await collection.find_one(...)
except Exception as e:
    logger.error(f"DB error: {e}")
    raise HTTPException(status_code=500)

# 5. Pagination kullan
await collection.find().skip(skip).limit(limit).to_list(None)
```

### ❌ DON'T

```python
# 1. Global database nesnesi
db = Database.get_database()  # Her fonksiyonun başında

# 2. None kontrol etmeme
collection = await Database.get_collection("users")
await collection.find_one(...)  # Crash!

# 3. Tüm verileri bellekte yükle
data = list(await collection.find().to_list(None))  # 1M+ docs?

# 4. İndeksler olmadan
collection.find({"email": ...})  # Slow!

# 5. Error handling olmadan
result = await collection.insert_one(doc)
```

---

## 🚀 Production Deployment

### Docker Compose

```yaml
version: '3.8'
services:
  mongodb:
    image: mongo:latest
    volumes:
      - mongo_data:/data/db
    environment:
      MONGO_INITDB_DATABASE: cookwise

  api:
    build: .
    environment:
      MONGODB_URL: mongodb://mongodb:27017/
      MONGODB_DB: cookwise
      APP_ENV: production
    depends_on:
      - mongodb
```

### Health Check Integration

```yaml
services:
  api:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health/ready"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

---

## 📖 İlgili Belgeler

- [Motor Documentation](https://motor.readthedocs.io/)
- [PyMongo Documentation](https://pymongo.readthedocs.io/)
- [FastAPI Dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [MongoDB Query Language](https://docs.mongodb.com/manual/reference/operator/query/)

---

## 📞 Quick Reference

```python
# Import
from app.core.database import Database, get_database
from bson import ObjectId

# Bağlantı kontrol
if Database.is_connected():
    print("MongoDB active")

# Collection al
users = await Database.get_collection("users")
products = await Database.get_collection("products")

# CRUD
user = await Database.find_one("users", {"email": "..."})
users = await Database.find_many("users", {"role": "admin"})
id = await Database.insert_one("users", {...})
await Database.update_one("users", {"_id": ObjectId(id)}, {...})
await Database.delete_one("users", {"_id": ObjectId(id)})

# Aggregation
pipeline = [{"$match": {...}}, {"$group": {...}}]
await collection.aggregate(pipeline).to_list(None)

# Dependency
async def my_route(db = Depends(get_database)):
    if db:
        # Use database
        pass
```

---

✅ **MongoDB Bağlantı Yapısı Kuruldu!**

Şu anda proje şunları içeriyor:
- ✅ Motor async driver (3.3.2)
- ✅ Connection pooling (10-50 connections)
- ✅ Graceful fallback (DB optional)
- ✅ Lifecycle management (startup/shutdown)
- ✅ Health check endpoints (5 endpoints)
- ✅ Dependency injection ready
- ✅ CRUD helper methods
- ✅ Index creation at startup
- ✅ Full error handling

Şimdi Users, Products, Orders router'ları oluşturmaya başlayabilirsin!

