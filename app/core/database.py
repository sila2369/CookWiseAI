"""
MongoDB Veritabanı Bağlantı ve İşlemleri
==========================================

🔧 Teknoloji Seçimi: MOTOR (Async PyMongo)

Neden Motor?
-----------
✓ Async/await destekleme - FastAPI ile tam uyumlu
✓ Non-blocking I/O - eş zamanlı çok kullanıcı
✓ Connection pooling - performans optimizasyonu
✓ PyMongo API'sinin async versiyonu - az öğrenme eğrisi
✓ Production-ready - açık kaynak, iyi desteklenen

PyMongo vs Motor Karşılaştırma:
--------- Motor
PyMongo:  Bloking   | Tek thread limited    | WebSocket/Stream ❌
Motor:    Non-block | Çok sayıda connection | WebSocket/Stream ✓

Bağlantı Yönetimi:
-----------------
- Centralized (merkezi): Database sınıfı aracılığıyla
- Graceful fallback: MongoDB kapıksa uygulama çalışmaya devam eder
- Lifecycle management: Startup/shutdown hooks entegre
- Dependency injection: Router ve Service'lerde kolayca kullanılabilir
"""

from typing import Optional, Any, Dict, List
import logging
from contextlib import asynccontextmanager

from .config import settings

logger = logging.getLogger(__name__)


class Database:
    """
    MongoDB bağlantısını merkezi olarak yönetir
    
    Özellikler:
    -----------
    ✓ Connection pooling (Performance)
    ✓ Graceful fallback (Reliability)
    ✓ Async/await support (FastAPI uyumlu)
    ✓ Type hints (IDE autocomplete)
    ✓ Dependency injection ready
    
    Kullanım:
    ---------
    # Uygulama açılırken (main.py lifespan'de):
    await Database.connect_db()
    
    # Router/Service'de:
    db = Database.get_database()
    users = await Database.get_collection("users")
    user = await users.find_one({"email": email})
    
    # Uygulama kapanırken:
    await Database.close_db()
    """
    
    # Class variables - tüm instance'lar tarafından paylaşılır
    client: Optional[Any] = None
    db: Optional[Any] = None
    connected: bool = False
    
    @classmethod
    async def connect_db(cls) -> None:
        """
        MongoDB'ye bağlan ve bağlantıyı test et
        
        Yanılmasız bağlantı pool'u oluşturur:
        - maxPoolSize: 50 (max concurrent connections)
        - minPoolSize: 10 (başlangıç connection'ları)
        - serverSelectionTimeoutMS: 5 saniye
        
        Çalıştır:
            # main.py lifespan'de
            await Database.connect_db()
        """
        try:
            # Motor kütüphanesini dinamik import et
            from motor.motor_asyncio import AsyncIOMotorClient
            
            logger.info(f"📡 MongoDB'ye bağlanılıyor...")
            logger.info(f"   URL: {settings.MONGODB_URL[:20]}...")
            logger.info(f"   Database: {settings.MONGODB_DB}")
            
            # Async MongoDB client'ı oluştur
            cls.client = AsyncIOMotorClient(
                settings.MONGODB_URL,
                # Connection pool seçenekleri
                maxPoolSize=50,              # Max concurrent connections
                minPoolSize=10,              # Starting connections
                serverSelectionTimeoutMS=20000,  # 20 saniye (SSL/DNS dalgalanmalarına tolerans)
                connectTimeoutMS=20000,
                retryWrites=True,
            )
            
            # Bağlantıyı test et (ping komutu)
            await cls.client.admin.command("ping")
            
            # Database nesnesini al
            cls.db = cls.client[settings.MONGODB_DB]
            cls.connected = True
            
            logger.info(f"✅ MongoDB bağlantısı başarılı!")
            logger.info(f"   Status: Connected | Pool: 10-50 connections")
            
        except ImportError:
            logger.warning("⚠️  Motor kütüphanesi bulunamadı")
            logger.warning("   MongoDB desteği devre dışı")
            logger.warning("   Komut: pip install motor pymongo")
            cls.connected = False
            
        except ConnectionError as e:
            logger.warning(f"⚠️  MongoDB bağlantı hatası: {type(e).__name__}")
            logger.warning(f"   Details: {str(e)[:100]}")
            logger.warning("   MongoDB bağlantısı opsiyonel - uygulama çalışmaya devam edecek")
            cls.connected = False
            
        except Exception as e:
            logger.warning(f"⚠️  Beklenmeyen hata: {type(e).__name__}: {str(e)[:100]}")
            logger.warning("   MongoDB opsiyonel olarak işareti edildi")
            cls.connected = False
    
    @classmethod
    async def close_db(cls) -> None:
        """
        MongoDB bağlantısını kapatır ve resource'ları serbest bırakır
        
        Çalıştır:
            # main.py lifespan shutdown'ında
            await Database.close_db()
        """
        if cls.client is not None:
            try:
                cls.client.close()
                cls.connected = False
                logger.info("✅ MongoDB bağlantısı kapatıldı")
            except Exception as e:
                logger.warning(f"⚠️  Bağlantı kapatma hatası: {e}")
    
    @classmethod
    def get_database(cls) -> Optional[Any]:
        """
        Aktif veritabanı instance'ını döndür
        
        Returns:
            Motor Database object veya None (bağlı değilse)
            
        Örnek:
            db = Database.get_database()
            if db:
                users = await db["users"].find().to_list(100)
            else:
                # MongoDB olmadan fallback
                users = []
        """
        if not cls.connected or cls.db is None:
            logger.debug("MongoDB bağlantısı mevcut değil - None döndürülüyor")
            return None
        return cls.db
    
    @classmethod
    def is_connected(cls) -> bool:
        """MongoDB'ye bağlı mı?"""
        return cls.connected and cls.db is not None
    
    # ==================== COLLECTION YARDIMCI YÖNTEMLERI ====================
    
    @classmethod
    async def get_collection(cls, collection_name: str) -> Any:
        """
        Adı verilen collection'a ulaş
        
        Örnek:
            users_col = await Database.get_collection("users")
            result = await users_col.find_one({"email": "user@example.com"})
        """
        db = cls.get_database()
        if db is None:
            logger.warning(f"Collection alınamadı: {collection_name} - DB bağlı değil")
            return None
        return db[collection_name]
    
    @classmethod
    async def create_indexes(cls) -> None:
        """
        Veritabanında indeksler oluştur (startup'ta çalıştır)
        
        İndeksler database performansını önemli ölçüde iyileştirir
        Özellikle unique fields ve sık aranan fields'ler için
        """
        try:
            db = cls.get_database()
            if db is None:
                logger.warning("İndeksler oluşturulamadı - DB bağlı değil")
                return
            
            logger.info("📊 İndeksler oluşturuluyor...")
            
            # Users collection indexes
            users = db["users"]
            await users.create_index("email", unique=True)  # Unique email
            await users.create_index("created_at")           # Sıralama
            logger.info("   ✓ users indexes oluşturuldu")
            
            # Categories collection indexes (slug benzersiz)
            categories = db["categories"]
            await categories.create_index("slug", unique=True)
            await categories.create_index("is_active")
            await categories.create_index("created_at")
            logger.info("   ✓ categories indexes oluşturuldu")

            # Products collection indexes
            products = db["products"]
            await products.create_index("slug", unique=True)
            await products.create_index("category_id")
            await products.create_index("price")
            await products.create_index("name")
            await products.create_index("is_active")
            await products.create_index([("created_at", -1)])  # M0 tier uyumlu
            logger.info("   ✓ products indexes oluşturuldu")
            
            # Orders collection indexes
            orders = db["orders"]
            await orders.create_index("user_id")             # Kullanıcıya göre araması
            await orders.create_index("status")              # Status süzme
            await orders.create_index([("created_at", -1)])  # Yeni siparişler, M0 tier uyumlu
            logger.info("   ✓ orders indexes oluşturuldu")
            
        except Exception as e:
            logger.warning(f"Index oluşturma hatası: {e}")
    
    # ==================== TEMEL CRUD OPERASYONLARI (ÖRNEKLER) ====================
    
    @classmethod
    async def find_one(cls, collection: str, query: Dict) -> Optional[Dict]:
        """
        Bir dokümanı bul
        
        Örnek:
            user = await Database.find_one("users", {"email": "user@example.com"})
        """
        col = await cls.get_collection(collection)
        if col is None:
            return None
        return await col.find_one(query)
    
    @classmethod
    async def find_many(cls, collection: str, query: Dict, limit: int = 100) -> List[Dict]:
        """
        Birden fazla dokümanı bul
        
        Örnek:
            products = await Database.find_many("products", {"category": "food"}, limit=50)
        """
        col = await cls.get_collection(collection)
        if col is None:
            return []
        return await col.find(query).limit(limit).to_list(None)
    
    @classmethod
    async def insert_one(cls, collection: str, document: Dict) -> Optional[str]:
        """
        Yeni doküman ekle
        
        Döndür: ObjectId (string) veya None
        
        Örnek:
            user_id = await Database.insert_one("users", {
                "email": "user@example.com",
                "full_name": "John Doe"
            })
        """
        col = await cls.get_collection(collection)
        if col is None:
            return None
        result = await col.insert_one(document)
        return str(result.inserted_id)
    
    @classmethod
    async def update_one(cls, collection: str, query: Dict, update_data: Dict) -> int:
        """
        Dokümanı güncelle
        
        Döndür: Güncellenen doküman sayısı
        
        Örnek:
            count = await Database.update_one(
                "users",
                {"_id": ObjectId(user_id)},
                {"$set": {"full_name": "Jane Doe"}}
            )
        """
        col = await cls.get_collection(collection)
        if col is None:
            return 0
        result = await col.update_one(query, {"$set": update_data})
        return result.modified_count
    
    @classmethod
    async def delete_one(cls, collection: str, query: Dict) -> int:
        """
        Dokümanı sil
        
        Döndür: Silinen doküman sayısı
        
        Örnek:
            count = await Database.delete_one("users", {"_id": ObjectId(user_id)})
        """
        col = await cls.get_collection(collection)
        if col is None:
            return 0
        result = await col.delete_one(query)
        return result.deleted_count


# ==================== DEPENDENCY INJECTION FONKSIYONLARI ====================

async def get_database() -> Any:
    """
    FastAPI Dependency Injection - Veritabanı nesnesi
    
    Routers'da kullanım:
    ---------------------
    from fastapi import Depends
    from app.core.database import get_database
    
    @router.get("/users")
    async def list_users(db = Depends(get_database)):
        if db is None:
            return {"error": "Database unavailable"}
        users = await db["users"].find().to_list(100)
        return users
    
    Avantaj:
    - FastAPI otomatik olarak injection sağlıyor
    - Her endpoint'te veritabanı kullanılabilir
    - MongoDB devre dışıysa None döndürür (graceful fallback)
    """
    return Database.get_database()


async def get_collection_dep(collection_name: str) -> Any:
    """
    Belirli bir collection'u alır (Dependency Injection)
    
    Örnek:
        @router.get("/users")
        async def list_users(users_col = Depends(lambda: get_collection_dep("users"))):
            if users_col is None:
                return []
            return await users_col.find().to_list(100)
    """
    return await Database.get_collection(collection_name)


# ==================== BAĞLANTI DURUM KONTROL ====================

def check_db_connected() -> bool:
    """MongoDB'ye bağlı mı?"""
    return Database.is_connected()
