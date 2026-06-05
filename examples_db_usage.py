#!/usr/bin/env python3
"""
MongoDB Kullanım Örnekleri
==========================

Bu dosya Database sınıfının ve dependency injection'ın
nasıl kullanılacağını göstermektedir.

3 Farklı Kullanım Yöntemini Gösterir:
1. Direct Database Class Methods
2. FastAPI Dependency Injection
3. Collection Operations

Dosya çalıştırılmaz - yalnızca referans olarak kullanılır!
"""

# ==================== ÖRNEK 1: ROUTER'DA DEPENDENCY INJECTION ====================

"""
Router'da Veritabanı Kullanımı (Recommended)

MongoDBye erişmek için FastAPI'nin built-in Depends() kullanılır.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from bson import ObjectId
from app.core.database import get_database, Database
from app.core.config import settings
from typing import List, Optional, Any

router = APIRouter(prefix="/users", tags=["users"])


class UserCreate(BaseModel):
    """Kullanıcı oluşturma şeması"""
    email: str
    full_name: str
    password: str


class UserResponse(BaseModel):
    """Kullanıcı yanıt şeması"""
    id: str
    email: str
    full_name: str
    
    class Config:
        from_attributes = True


# ✅ DEPENDENCY INJECTION - En basit yöntem
@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Any = Depends(get_database)  # <-- Dependency Injection
):
    """
    GET /users - Tüm kullanıcıları listele
    
    FastAPI otomatik olarak get_database() çağırır ve db parametresini doldurur.
    MongoDB bağlıysa Motor Database object, değilse None döner.
    """
    
    # MongoDB kullanılabilir mi kontrol et
    if db is None:
        return []
    
    try:
        # users collection'ına eriş
        users = db["users"]
        
        # Verileri sor (skip/limit ile pagination)
        result = await users.find().skip(skip).limit(limit).to_list(None)
        
        # ObjectId'yi string'e çevir
        for user in result:
            user["id"] = str(user.pop("_id"))
        
        return result
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )


# ✅ POST - YENİ KULLANICI OLUŞTUR
@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user: UserCreate,
    db: Any = Depends(get_database)  # <-- Dependency Injection
):
    """
    POST /users - Yeni kullanıcı oluştur
    
    Request body:
    {
        "email": "user@example.com",
        "full_name": "John Doe",
        "password": "secure_password"
    }
    """
    
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable"
        )
    
    try:
        users = db["users"]
        
        # Email zaten var mı kontrol et
        existing = await users.find_one({"email": user.email})
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )
        
        # Yeni kullanıcı ekle
        new_user = {
            "email": user.email,
            "full_name": user.full_name,
            "password": user.password,  # gerçekte hash'lenmiş olmalı
            "created_at": datetime.utcnow(),
        }
        
        result = await users.insert_one(new_user)
        
        return {
            "id": str(result.inserted_id),
            "email": user.email,
            "full_name": user.full_name,
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ==================== ÖRNEK 2: DATABASE CLASS METODLARI ====================

"""
Database Sınıfının Kolaylaştırıcı Metodları Kullanımı

Daha kısa yapı için Database class'ındaki yardımcı metodları kullanabilirsin.
"""


# ✅ SIMPLIFY ETMİŞ VERSYON - CRUD Metodları
@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str):
    """
    GET /users/{user_id} - Tek kullanıcı al
    
    Database.find_one() metodunu kullanarak
    """
    
    try:
        # ObjectId'ye çevir
        from bson import ObjectId
        user = await Database.find_one("users", {"_id": ObjectId(user_id)})
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user["id"] = str(user.pop("_id"))
        return user
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(user_id: str, user_update: dict):
    """
    PUT /users/{user_id} - Kullanıcı güncelle
    
    Database.update_one() metodunu kullanarak
    """
    
    try:
        from bson import ObjectId
        
        modified = await Database.update_one(
            "users",
            {"_id": ObjectId(user_id)},
            user_update
        )
        
        if modified == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Güncellenmiş kullanıcıyı al
        user = await Database.find_one("users", {"_id": ObjectId(user_id)})
        user["id"] = str(user.pop("_id"))
        return user
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: str):
    """
    DELETE /users/{user_id} - Kullanıcı sil
    
    Database.delete_one() metodunu kullanarak
    """
    
    try:
        from bson import ObjectId
        
        deleted = await Database.delete_one(
            "users",
            {"_id": ObjectId(user_id)}
        )
        
        if deleted == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return None
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ==================== ÖRNEK 3: COLLECTION OPERASYONLARI ====================

"""
Düşük seviye Collection Operasyonları

Bazı durumlarda direkt Motor collection nesnesi ihtiyaç duyabilirsin
(complex queries, aggregation vb.)
"""


async def search_users_by_email(email_pattern: str) -> List[dict]:
    """
    Email'i içeren tüm kullanıcıları ara (partial match)
    
    Düşük-seviye collection operasyonu örneği
    """
    
    users_collection = await Database.get_collection("users")
    
    if users_collection is None:
        return []
    
    # Regex search
    results = await users_collection.find({
        "email": {"$regex": email_pattern, "$options": "i"}  # case-insensitive
    }).to_list(100)
    
    return results


async def counting_users_by_status() -> dict:
    """
    Kullanıcıları status'a göre sayla
    
    Aggregation pipeline örneği
    """
    
    users_collection = await Database.get_collection("users")
    
    if users_collection is None:
        return {}
    
    pipeline = [
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
    ]
    
    result = await users_collection.aggregate(pipeline).to_list(None)
    return {item["_id"]: item["count"] for item in result}


async def bulk_insert_users(users: List[dict]) -> int:
    """
    Birden fazla kullanıcı ekle (Bulk insert)
    
    Performance-kritik işlemler için
    """
    
    users_collection = await Database.get_collection("users")
    
    if users_collection is None:
        return 0
    
    result = await users_collection.insert_many(users)
    return len(result.inserted_ids)


# ==================== ÖRNEK 4: ERROR HANDLING ====================

"""
Hata Yönetimi Desenleri
"""


async def safe_database_operation():
    """Güvenli database operasyonu - Graceful fallback"""
    
    try:
        db = Database.get_database()
        
        # DB bağlı değilse fallback
        if db is None:
            return {
                "data": [],
                "warning": "Database not available - using cache or defaults"
            }
        
        # Normal operasyon
        users = db["users"]
        data = await users.find().limit(10).to_list(None)
        
        return {"data": data, "warning": None}
    
    except Exception as e:
        # Log et ve fallback
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Database operation failed: {e}")
        
        return {
            "data": [],
            "error": str(e),
            "fallback": "Using cache"
        }


# ==================== ÖZET ====================

"""
MONGODB KULLANIMININ EN İYİ UYGULAMALARI
=========================================

1. DEPENDENCY INJECTION KULLAN (Önerilen)
   ✅ Database: async def endpoint(db = Depends(get_database))
   ✅ Otomatik injection
   ✅ Testing kolay
   ❌ Complex queries için sınırlanabilir

2. DATABASE CLASS METODLARINI KULLAN
   ✅ find_one(), find_many(), insert_one(), update_one(), delete_one()
   ✅ Basit CRUD operasyonları
   ✅ Kısa ve okunabilir kod
   ❌ Complex queries için yeterli değil

3. COLLECTION DOĞRUDAN KULLAN
   ✅ Complex aggregations
   ✅ Bulk operations
   ✅ Advanced queries
   ❌ Daha verbose

4. GRACEFUL FALLBACK
   ✅ MongoDB bağlıysa kullan
   ✅ Değilse null döndür ve devam et
   ✅ Cache veya defaults kullan

5. ERROR HANDLING
   ✅ DatabaseError'u yakala
   ✅ Anlamlı HTTP status döndür
   ✅ Loglama ve monitoring

6. MIGRATION & INDEXING
   ✅ Startup'ta indeksler oluştur (Database.create_indexes())
   ✅ Collection schema'larını dokümante et
   ✅ Versioning sistem kur
"""
