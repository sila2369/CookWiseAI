"""
Ana Uygulama Dosyası - FastAPI Entry Point
================================================

Bu dosya FastAPI uygulamasının ana giriş noktasıdır.

Yapı:
1. Logging yapılandırması
2. Lifespan events (startup/shutdown)
3. FastAPI uygulaması oluşturma
4. Middleware'lar (CORS, vb.)
5. Router'ları kaydetme
6. Global exception handler'lar

Modüler Mimarı:
- app/core/config.py → Ayarları yönetme
- app/core/database.py → MongoDB bağlantısı
- app/routers/ → API route'ları
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from datetime import datetime
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.database import Database, get_database
from app.core.exceptions import InvalidCredentialsException
from app.core.exceptions import DatabaseConnectionException
from app.routers import (
    health_router,
    auth_router,
    users_router,
    admin_router,
    categories_router,
    products_router,
    recipes_router,
    ai_router,
    cart_router,
    orders_router,
    addresses_router,
    favorites_router,
    notifications_router,
    uploads_router,
)
from app.schemas.ai import AIGenerateRequest, AIGenerateResponse
from app.schemas.user import TokenResponse
from app.services.ai_generate_service import AIGenerateService
from app.services.auth_service import AuthService
from app.dependencies.auth import get_optional_user

# ==================== LOGGING YAPILANDIRMASI ====================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ==================== LIFESPAN EVENTS ====================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Uygulama yaşam döngüsü yönetimi
    
    Startup: Veritabanı bağlantısı, cache'ler, vb. başlatılır
    Shutdown: Kaynakları serbest bırak, bağlantıları kapat
    """
    # ▶️ STARTUP
    logger.info("🚀 Uygulama başlatılıyor...")
    logger.info(f"   Environment: {settings.APP_ENV}")
    logger.info(f"   Debug: {settings.DEBUG}")
    
    try:
        await Database.connect_db()
        
        # MongoDB indeksler oluştur (bağlıysa)
        if Database.is_connected():
            await Database.create_indexes()
        
        # Firebase (kullanıcılar için)
        from app.core.firebase import is_firebase_enabled, init_firebase
        if is_firebase_enabled():
            init_firebase(
                settings.FIREBASE_CREDENTIALS_PATH,
                settings.FIREBASE_PROJECT_ID,
            )
        auth_paths = [
            route.path for route in app.routes
            if getattr(route, "path", "").startswith(f"{settings.API_PREFIX}/auth")
        ]
        logger.info(f"🔎 Aktif auth route'ları: {auth_paths}")
        
        logger.info("✅ Startup tamamlandı")
    except Exception as e:
        logger.error(f"❌ Startup hatası: {e}")
    
    yield  # Uygulama çalışıyor
    
    # ⏹️ SHUTDOWN
    logger.info("🛑 Uygulama kapatılıyor...")
    try:
        await Database.close_db()
        logger.info("✅ Shutdown tamamlandı")
    except Exception as e:
        logger.error(f"❌ Shutdown hatası: {e}")


# ==================== FASTAPI UYGULAMASI ====================
app = FastAPI(
    # Swagger UI'da gösterilecek bilgiler
    title=settings.APP_NAME,
    description="Getir benzeri dijital market uygulaması - Modüler FastAPI backend",
    version="1.0.0",
    
    # API routes'leri otomatik dökümante et
    openapi_url="/openapi.json",
    docs_url="/docs",              # Swagger UI
    redoc_url="/redoc",            # ReDoc
    
    # Swagger UI - Authorize ile token girildiğinde sayfa yenilense bile kalsın
    swagger_ui_parameters={
        "persistAuthorization": True,
    },
    
    # Debug modu
    debug=settings.DEBUG,
    
    # Yaşam döngüsü
    lifespan=lifespan,
)

logger.info(f"✨ FastAPI uygulaması oluşturuldu: {settings.APP_NAME}")


# ==================== MIDDLEWARE'LAR ====================
# CORS: Cross-Origin isteklerine izin ver
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,          # ["*"] = hepsi
    allow_credentials=settings.CORS_CREDENTIALS,  # Cookies izni
    allow_methods=settings.CORS_METHODS,          # ["*"] = GET, POST, vb. hepsi
    allow_headers=settings.CORS_HEADERS,          # ["*"] = tüm header'lar
)

logger.info(f"✅ CORS Middleware eklendi")

Path("static/uploads").mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


# ==================== ROUTER'LAR ====================
# Health check router'ını API prefix'i ile kaydet
app.include_router(
    health_router,
    prefix=settings.API_PREFIX,
    # health_router zaten "/health" prefix'ine sahip
    # Sonuç: /api/v1/health/
)

# Auth router'ını API prefix'i ile kaydet
app.include_router(
    auth_router,
    prefix=settings.API_PREFIX,
    # auth_router zaten "/auth" prefix'ine sahip
    # Sonuç: /api/v1/auth/register, /api/v1/auth/login, vb.
)

# Users router
app.include_router(users_router, prefix=settings.API_PREFIX)

# Admin router (sadece is_admin kullanıcılar)
app.include_router(admin_router, prefix=settings.API_PREFIX)

# Categories router
app.include_router(categories_router, prefix=settings.API_PREFIX)

# Products router
app.include_router(products_router, prefix=settings.API_PREFIX)

# Recipes router
app.include_router(recipes_router, prefix=settings.API_PREFIX)

# AI router
app.include_router(ai_router, prefix=settings.API_PREFIX)

# Cart router
app.include_router(cart_router, prefix=settings.API_PREFIX)

# Orders router
app.include_router(orders_router, prefix=settings.API_PREFIX)

# Addresses router
app.include_router(addresses_router, prefix=settings.API_PREFIX)

# Favorites router
app.include_router(favorites_router, prefix=settings.API_PREFIX)

# Notifications router
app.include_router(notifications_router, prefix=settings.API_PREFIX)

app.include_router(uploads_router, prefix=settings.API_PREFIX)

logger.info("✅ Router'lar kaydedildi: health, auth, users, admin, categories, products, ai, cart, orders, addresses, favorites, uploads")


class FirebaseLoginPayload(BaseModel):
    id_token: str = Field(..., min_length=10)


def _has_firebase_login_route() -> bool:
    target_path = f"{settings.API_PREFIX}/auth/firebase-login"
    for route in app.routes:
        if getattr(route, "path", None) == target_path and "POST" in getattr(route, "methods", set()):
            return True
    return False


async def _get_auth_service_for_firebase(db=Depends(get_database)) -> AuthService:
    # Firebase OAuth login akışı MongoDB'de kullanıcıyı bulur/oluşturur.
    return AuthService(db)


# Bazı ortamlarda auth router'daki firebase-login endpoint'i import sırasında devreye girmeyebiliyor.
# Bu fallback route Google login akışının /api/v1/auth/firebase-login altında her zaman cevap vermesini sağlar.
if not _has_firebase_login_route():
    @app.post(
        f"{settings.API_PREFIX}/auth/firebase-login",
        response_model=TokenResponse,
        status_code=status.HTTP_200_OK,
        summary="Firebase Google OAuth ile giriş (fallback)",
    )
    async def firebase_login_fallback(
        payload: FirebaseLoginPayload,
        auth_service: AuthService = Depends(_get_auth_service_for_firebase),
    ) -> TokenResponse:
        try:
            return await auth_service.login_with_firebase_id_token(payload.id_token)
        except DatabaseConnectionException:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service is temporarily unavailable",
            )
        except InvalidCredentialsException as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=e.message,
                headers={"WWW-Authenticate": "Bearer"},
            )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google ile giriş sırasında beklenmeyen bir hata oluştu",
            )


# ==================== UNIFIED AI ENDPOINT (NO API PREFIX) ====================
# Kullanici tarafinda istenen endpoint: POST /ai/generate
ai_generate_service = AIGenerateService()


@app.post(
    "/ai/generate",
    response_model=AIGenerateResponse,
    summary="Unified AI generation endpoint",
)
async def ai_generate(
    payload: AIGenerateRequest,
    db=Depends(get_database),
    current_user=Depends(get_optional_user),
) -> AIGenerateResponse:
    result = await ai_generate_service.generate(
        mode=payload.mode,
        user_input=payload.input,
        preferences=payload.preferences,
        db=db,
        current_user=current_user,
    )
    return AIGenerateResponse(**result)


# ==================== GLOBAL ENDPOINTS ====================
@app.get("/", tags=["root"], summary="API Bilgileri")
async def root():
    """
    🏠 API ana sayfası
    
    Temel bilgileri ve kullanılabilir endpoint'leri göster
    """
    return {
        "title": settings.APP_NAME,
        "description": "Getir benzeri dijital market uygulaması",
        "version": "1.0.0",
        "environment": settings.APP_ENV,
        "timestamp": datetime.utcnow().isoformat(),
        
        # Kullanılabilir dokümantasyon
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc",
            "openapi": "/openapi.json",
        },
        
        # API Endpoints
        "endpoints": {
            "health": f"{settings.API_PREFIX}/health/",
            "health_detailed": f"{settings.API_PREFIX}/health/detailed",
            "categories": f"{settings.API_PREFIX}/categories",
            "products": f"{settings.API_PREFIX}/products",
        },
        
        # Kütüphaneler
        "built_with": {
            "framework": "FastAPI 0.104+",
            "database": "MongoDB (Motor async)",
            "auth": "JWT",
        },
    }


@app.get(f"{settings.API_PREFIX}/debug/config", tags=["debug"], include_in_schema=False)
async def debug_config():
    """Server'in gördüğü config (hata ayıklama için)."""
    from app.core.firebase import is_firebase_enabled
    import os
    auth_routes = [
        route.path for route in app.routes
        if getattr(route, "path", "").startswith(f"{settings.API_PREFIX}/auth")
    ]
    return {
        "use_firebase_auth": getattr(settings, "USE_FIREBASE_AUTH", False),
        "firebase_enabled": is_firebase_enabled(),
        "firebase_credentials_exists": os.path.isfile(getattr(settings, "FIREBASE_CREDENTIALS_PATH", "") or ""),
        "cwd": os.getcwd(),
        "auth_routes": auth_routes,
    }


@app.get(f"{settings.API_PREFIX}/status", tags=["status"], summary="API Durumu")
async def api_status():
    """
    📊 API durum bilgisi
    
    Uygulamanın mevcut durumunu döndür
    """
    return {
        "status": "ok",
        "api_name": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "debug_mode": settings.DEBUG,
        "timestamp": datetime.utcnow().isoformat(),
    }


# ==================== EXCEPTION HANDLERS ====================
@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    """ValueError için custom handler"""
    logger.error(f"ValueError: {exc}")
    return JSONResponse(
        status_code=400,
        content={
            "error": "Validation Error",
            "detail": str(exc),
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    """Request validation hatası için custom handler"""
    logger.error(f"Validation Error: {exc}")
    
    # Convert errors to JSON-serializable format
    errors = exc.errors()
    for error in errors:
        if "ctx" in error and "error" in error["ctx"]:
            # Convert Exception objects to strings
            error["ctx"]["error"] = str(error["ctx"]["error"])
    
    return JSONResponse(
        status_code=422,
        content={
            "error": "Request Validation Error",
            "detail": errors,
        },
    )


# ==================== ÇALIŞTIRILMA ====================
if __name__ == "__main__":
    import uvicorn
    
    logger.info("=" * 60)
    logger.info("🚀 Development Server Başlatılıyor")
    logger.info("=" * 60)
    logger.info(f"📍 http://{settings.APP_HOST}:{settings.APP_PORT}")
    logger.info(f"📖 Swagger UI: http://{settings.APP_HOST}:{settings.APP_PORT}/docs")
    logger.info(f"🔄 Auto-reload: {settings.DEBUG}")
    logger.info("=" * 60)
    
    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG,        # Code değişikliğinde otomatik restart
        log_level="info",
        access_log=True,
    )
