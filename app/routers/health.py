"""
Health Check Router - API ve MongoDB Durumu
============================================

Bu router uygulamanın ve bağımlılıklarının (özellikle MongoDB) 
durumunu kontrol etmek için endpoint'ler sağlar.

Endpoints:
- GET /api/v1/health/ → Basit status kontrolü
- GET /api/v1/health/detailed → Detaylı sistem durumu
- GET /api/v1/health/db → Sadece veritabanı kontrolü

Yanıtlar JSON formatında, şu detayları içerir:
- API durumu
- MongoDB bağlantı durumu
- Collection bilgileri (bağlı ise)
- Sistem timestamp'i
"""

from fastapi import APIRouter, Depends, status
from typing import Any
from datetime import datetime

from app.core.database import Database, get_database
from app.core.config import settings

router = APIRouter(
    prefix="/health",
    tags=["health"],
    responses={
        200: {"description": "System is healthy"},
        503: {"description": "Service unavailable"}
    },
)


@router.get("/", status_code=status.HTTP_200_OK)
async def health_check():
    """
    ✅ Basit Health Check
    
    API'nin canlı ve çalışma durumunda olup olmadığını kontrol eder.
    
    Returns:
        {
            "status": "healthy",
            "timestamp": "2026-03-18T12:34:56.789Z",
            "app_name": "CookWise API",
            "version": "1.0.0"
        }
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "app_name": settings.APP_NAME,
        "version": "1.0.0",
    }


@router.get("/db", status_code=status.HTTP_200_OK)
async def database_health(db: Any = Depends(get_database)):
    """
    🔗 Veritabanı Bağlantı Kontrolü
    
    MongoDB bağlantısının durumunu kontrol eder.
    
    Yanıt Durumları:
    - "connected" → MongoDB aktif ve ping başarılı
    - "disabled" → MongoDB kurulum yok (opsiyonel)
    - "error" → Bağlantı sorunu
    
    Returns:
        {
            "status": "ok",
            "database": {
                "connected": true,
                "name": "cookwise",
                "driver": "motor (async)",
                "status": "connected"
            }
        }
    """
    db_status = "disabled"
    
    if db is not None:
        try:
            # MongoDB'ye ping gönder
            await db.client.admin.command("ping")
            db_status = "connected"
        except Exception as e:
            db_status = f"error: {type(e).__name__}"
    
    return {
        "status": "ok",
        "database": {
            "connected": Database.is_connected(),
            "name": settings.MONGODB_DB,
            "driver": "motor 3.3.2 (async PyMongo)",
            "status": db_status,
        },
    }


@router.get("/detailed", status_code=status.HTTP_200_OK)
async def detailed_health_check(db: Any = Depends(get_database)):
    """
    📊 Detaylı Sistem Durum Raporu
    
    Uygulamanın tüm sisteminin detaylı durumunu rapor eder:
    - API çalışma durumu
    - MongoDB bağlantısı
    - Mevcut collections
    - Sistem timestamps
    
    Returns:
        {
            "status": "healthy",
            "environment": "development",
            "debug": true,
            "api": {
                "name": "CookWise API",
                "version": "1.0.0"
            },
            "database": {
                "status": "connected",
                "name": "cookwise",
                "collections": ["users", "products", "orders"],
                "driver": "motor"
            },
            "timestamp": "2026-03-18T12:34:56.789Z"
        }
    """
    
    # Veritabanı durumu
    db_status = "disabled"
    collections = []
    
    if db is not None:
        try:
            await db.client.admin.command("ping")
            db_status = "connected"
            
            # Mevcut collections listeleme
            try:
                collections = await db.list_collection_names()
            except Exception as e:
                collections = []
        except Exception as e:
            db_status = f"error: {type(e).__name__}"
    
    response = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": settings.APP_ENV,
        "debug": settings.DEBUG,
        "api": {
            "name": settings.APP_NAME,
            "version": "1.0.0",
            "host": settings.APP_HOST,
            "port": settings.APP_PORT,
            "cors_enabled": len(settings.CORS_ORIGINS) > 0,
        },
        "database": {
            "status": db_status,
            "name": settings.MONGODB_DB,
            "driver": "Motor 3.3.2 (Async AsyncClient)",
            "pool": {
                "min": 10,
                "max": 50,
                "current": "unknown (Motor manages internally)"
            },
            "collections": collections,
            "connected": Database.is_connected(),
        },
    }
    
    return response


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check(db: Any = Depends(get_database)):
    """
    ⚡ Hazır Mı? (Readiness Probe)
    
    Kubernetes/Docker Compose tarafından kullanılır.
    Uygulama trafiği kabul etmeye hazır mı kontrol eder.
    
    Returns:
        - 200 OK → Hazır
        - 503 × Service Unavailable → Hazır değil
    """
    
    # Minimum gereksinim: API çalışıyor
    if db is None:
        # MongoDB opsiyonel, sadece warning
        return {
            "ready": True,
            "reason": "API ready (MongoDB optional)",
            "database": "disabled"
        }
    
    try:
        await db.client.admin.command("ping")
        return {
            "ready": True,
            "reason": "Full system ready",
            "database": "connected"
        }
    except Exception as e:
        return {
            "ready": False,
            "reason": f"Database error: {type(e).__name__}",
            "database": "error"
        }


@router.get("/live", status_code=status.HTTP_200_OK)
async def liveness_check():
    """
    💚 Canlı Mı? (Liveness Probe)
    
    Kubernetes/Docker Compose tarafından kullanılır.
    Uygulama hala çalışıyor mu kontrol eder (basit check).
    
    Returns:
        - 200 OK → Canlı
    """
    return {
        "alive": True,
        "app": settings.APP_NAME,
        "timestamp": datetime.utcnow().isoformat()
    }

