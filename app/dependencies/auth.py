"""
Authentication Dependencies
============================

FastAPI Dependency Injection için Authentication fonksiyonları.

Bu dosya router'larda şu şekilde kullanılır:
    from app.dependencies.auth import get_current_user
    
    @router.get("/me")
    async def get_current_user_info(
        current_user = Depends(get_current_user)
    ) -> UserResponse:
        return current_user
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer

from app.core.security import verify_token
from app.core.database import get_database
from app.core.exceptions import UserNotAuthenticatedException

logger = logging.getLogger(__name__)

# HTTP Bearer token scheme - Swagger Authorize ile kullanılır
security = HTTPBearer()
# Opsiyonel auth için (token yoksa 401 vermez)
security_optional = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials = Depends(security)
) -> Dict[str, Any]:
    """
    Mevcut (logged-in) kullanıcıyı token'dan al
    
    Route'da kullanım:
        @router.get("/me")
        async def get_me(user = Depends(get_current_user)):
            return {"user_id": user["sub"]}
    
    Token format:
        Authorization: Bearer <JWT_TOKEN>
    
    Raises:
        HTTPException (401): Token geçersiz/süresi dolmuş
    """
    try:
        token = credentials.credentials
        
        # Token'ı doğrula ve payload'ı al
        payload = verify_token(token)
        
        # Token'dan user_id çıkar
        user_id = payload.get("sub")
        if not user_id:
            logger.warning("Token'da 'sub' claim bulunamadı")
            raise InvalidTokenException("Token missing 'sub' claim")
        
        logger.debug(f"User authenticated: {user_id}")
        
        return {
            "user_id": user_id,
            "payload": payload,  # Tüm token claims
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_from_db(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db = Depends(get_database)
) -> Dict[str, Any]:
    """
    Mevcut kullanıcıyı veritabanından al (MongoDB veya Firestore).
    """
    from app.core.config import settings
    from app.core.firebase import is_firebase_enabled

    def apply_config_admin(user: Dict[str, Any]) -> Dict[str, Any]:
        legacy_field_map = {
            "Email": "email",
            "Full_Name": "full_name",
            "FullName": "full_name",
            "Phone": "phone",
            "is_Active": "is_active",
            "is_Admin": "is_admin",
            "Is_Admin": "is_admin",
            "is_Verified": "is_verified",
        }
        for legacy_key, normalized_key in legacy_field_map.items():
            if normalized_key not in user and legacy_key in user:
                user[normalized_key] = user[legacy_key]
        email = str(user.get("email") or "").strip().lower()
        if email:
            user["email"] = email
        if "full_name" not in user and email:
            user["full_name"] = email.split("@")[0]
        admin_emails = {item.strip().lower() for item in settings.ADMIN_EMAILS}
        if email and email in admin_emails:
            user["is_admin"] = True
        return user
    
    user_id = current_user["user_id"]
    
    # Firebase: önce Firestore'dan al, bulunamazsa MongoDB'ye fallback yap.
    # Not: Google login akışında app JWT 'sub' alanı Mongo user id olabiliyor.
    if is_firebase_enabled():
        try:
            from app.services.firebase_user_service import get_firebase_user_service
            svc = get_firebase_user_service()
            user = await svc.get_user_by_uid(user_id)
            if user:
                return apply_config_admin(user)

            # Firebase uid ile bulunamadıysa MongoDB'de id/email ile dene
            if db is not None:
                from bson import ObjectId

                mongo_user = None
                try:
                    mongo_user = await db["users"].find_one({"_id": ObjectId(user_id)})
                except Exception:
                    mongo_user = None

                if not mongo_user:
                    email = (current_user.get("payload") or {}).get("email")
                    if email:
                        mongo_user = await db["users"].find_one({"email": str(email).lower()})

                if mongo_user:
                    mongo_user["id"] = str(mongo_user.pop("_id"))
                    return apply_config_admin(mongo_user)

            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Firebase user fetch failed: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch user")
    
    # MongoDB
    if db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")
    
    try:
        from bson import ObjectId
        user = await db["users"].find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        user["id"] = str(user.pop("_id"))
        return apply_config_admin(user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch user: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch user information")


async def get_optional_user(
    credentials=Depends(security_optional),
) -> Optional[Dict[str, Any]]:
    """
    Authentication isteğe bağlı (public endpoint'ler için)
    
    Route'da kullanım (public endpoint):
        @router.get("/products")
        async def list_products(
            user = Depends(get_optional_user)  # Can be None
        ):
            if user:
                return get_personalized_products(user["user_id"])
            return get_default_products()
    
    Returns:
        Dict[str, Any] | None: User object veya None
    """
    if credentials is None or not credentials.credentials:
        return None
    try:
        token = credentials.credentials
        payload = verify_token(token)
        
        return {
            "user_id": payload.get("sub"),
            "payload": payload,
        }
    except Exception as e:
        logger.debug(f"Optional auth failed (expected): {str(e)}")
        return None


# Admin kontrolü: app.dependencies.admin.get_admin_user kullanın


# ==================== RATE LIMITING ====================

# Not: Gerçek rate limiting için slowapi kütüphanesi kullan
# Bu örnek SimpleLRU cache kullanılıyor (production-ready değildir)

from datetime import timedelta
from collections import defaultdict

class SimpleRateLimiter:
    """Basit rate limiter implementation (production'da slowapi kullan)"""
    
    def __init__(self):
        self.requests = defaultdict(list)
    
    async def check_rate_limit(
        self,
        user_id: str,
        limit: int = 100,
        window_seconds: int = 60
    ) -> bool:
        """
        Rate limit kontrolü
        
        Örnek: user_id'ye ait son 1 dakika içinde 100'den fazla request varsa False
        """
        import time
        
        now = time.time()
        window_start = now - window_seconds
        
        # Eski requestleri temizle
        self.requests[user_id] = [
            req_time for req_time in self.requests[user_id]
            if req_time > window_start
        ]
        
        # Limiti kontrol et
        if len(self.requests[user_id]) >= limit:
            return False
        
        # Request'i kaydıt
        self.requests[user_id].append(now)
        return True


rate_limiter = SimpleRateLimiter()


async def check_user_rate_limit(
    current_user: Dict[str, Any] = Depends(get_current_user),
    limit: int = 100
) -> Dict[str, Any]:
    """
    Kullanıcı için rate limit kontrolü (slowapi'ye geçilene kadar)
    
    Route'da kullanım:
        @router.post("/api/data")
        async def get_data(user = Depends(check_user_rate_limit)):
            pass
    """
    user_id = current_user.get("user_id")
    
    allowed = await rate_limiter.check_rate_limit(
        user_id=user_id,
        limit=limit,
        window_seconds=60
    )
    
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )
    
    return current_user


# ==================== SCOPED DEPENDENCIES (Advanced) ====================

class ActiveUserDependency:
    """
    Scope'lu dependency - multiple stages
    
    Örnek:
        @router.get("/me")
        async def get_me(user = Depends(ActiveUserDependency())):
            return user
    """
    
    async def __call__(
        self,
        current_user: Dict[str, Any] = Depends(get_current_user_from_db),
    ) -> Dict[str, Any]:
        """
        1. Token'ı doğrula
        2. Veritabanından kullanıcıyı al
        3. Kullanıcının aktif olup olmadığını kontrol et
        """
        is_active = current_user.get("is_active", True)
        
        if is_active is not True:
            user_email = current_user.get("email")
            logger.warning(f"Inactive user tried to access protected endpoint: {user_email}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account has been deactivated"
            )
        
        logger.debug(f"Active user accessed: {current_user.get('email')}")
        return current_user


get_active_user = ActiveUserDependency()


# ==================== USAGE EXAMPLES & DOCUMENTATION ====================

"""
📚 AUTHENTICATION DEPENDENCIES KULLANIM REHBERI
================================================

Bu modül OAuth2 Bearer token + MongoDB kullanıcı doğrulaması sağlar.

MEVCUT DEPENDENCIES:
====================

1️⃣ get_current_user
   - Sadece token'ı doğrular, user_id çıkarır
   - MongoDB'ye bakmaz
   - Hızlı, basit operations için
   
   Status: 401 (token geçersiz/süresi dolmuş)

2️⃣ get_current_user_from_db
   - Token'ı doğrular + MongoDB'den user bilgilerini çeker
   - Tam user object'i döner (email, is_admin, is_active, vb.)
   - Kullanıcı bulunmazsa 404 döner
   
   Status: 401 (token), 404 (user not found), 503 (DB error)

3️⃣ get_optional_user
   - AuthORIZASYON isteğe bağlı
   - Token yoksa None döner, hata vermez
   - Public endpoint'ler için
   
   Status: Asla 401, token geçersizse sadece None

4️⃣ get_admin_user
   - Kullanıcı is_admin=True olmalı
   - Admin-only endpoint'ler için
   
   Status: 403 (non-admin user)

5️⃣ get_store_owner_user
   - Admin veya store owner scope'u gerekli
   - Store management endpoint'leri için
   
   Status: 403 (insufficient permissions)

6️⃣ get_active_user
   - Kullanıcı is_active=True olmalı
   - Deaktif hesapları engeller
   
   Status: 403 (inactive account)


ENDPOINT ÖRNEKLERI:
===================

▶️ ÖRNEK 1: Public endpoint (Authentication isteğe bağlı)

    @router.get("/products")
    async def list_products(
        user = Depends(get_optional_user)
    ):
        \"\"\"Herkese açık, ama login yapanlar personalized öneriler alır\"\"\"
        if user:
            # Login yapan kullanıcı
            user_id = user["user_id"]
            return get_personalized_products(user_id)
        else:
            # Login yapmayan ziyaretçi
            return get_default_products()


▶️ ÖRNEK 2: Protected endpoint (Login gerekli)

    from app.dependencies.auth import get_active_user
    from app.schemas.user import UserResponse
    
    @router.get("/me", response_model=UserResponse)
    async def get_profile(user = Depends(get_active_user)):
        \"\"\"Sadece aktif, login yapmış kullanıcılar\"\"\"
        return user
    
    Response (200 OK):
    {
        "id": "507f1f77bcf86cd799439011",
        "full_name": "John Doe",
        "email": "john@example.com",
        "phone": "+905551234567",
        "is_active": true,
        "is_admin": false,
        "created_at": "2026-03-18T10:30:00",
        "updated_at": "2026-03-18T10:30:00"
    }


▶️ ÖRNEK 3: Admin-only endpoint

    from app.dependencies.auth import get_admin_user
    
    @router.post("/admin/users")
    async def create_user(
        new_user: UserCreate,
        admin = Depends(get_admin_user)
    ):
        \"\"\"Sadece admin kullanıcılar yeni user oluşturabilir\"\"\"
        # Admin-only logic
        return await create_user_in_db(new_user)
    
    Başarısız: 403 Forbidden
    {
        "detail": "Admin access required"
    }


▶️ ÖRNEK 4: Chained dependencies

    @router.put("/users/{user_id}")
    async def update_user_profile(
        user_id: str,
        update_data: UserUpdate,
        current_user = Depends(get_active_user),
        db = Depends(get_database)
    ):
        \"\"\"Aktif kullanıcı kendi profilini update edebilir\"\"\"
        
        # Kendi profilini update edip etmediğini kontrol et
        if current_user["id"] != user_id and not current_user.get("is_admin"):
            raise HTTPException(
                status_code=403,
                detail="Can only update own profile"
            )
        
        # Update işlemi
        return await update_user_in_db(user_id, update_data, db)


▶️ ÖRNEK 5: Birden fazla kontrol

    from app.dependencies.auth import get_current_user_from_db
    from fastapi import Query
    
    @router.get("/users/{user_id}/orders")
    async def get_user_orders(
        user_id: str,
        current_user = Depends(get_active_user),
        skip: int = Query(0),
        limit: int = Query(10),
        db = Depends(get_database)
    ):
        \"\"\"Aktif kullanıcı kendi siparişlerini görüntüleyebilir\"\"\"
        
        # Yetkilendirme kontrol et
        if current_user["id"] != user_id and not current_user.get("is_admin"):
            raise HTTPException(
                status_code=403,
                detail="Unauthorized"
            )
        
        # Siparişleri getir
        orders = await get_orders_from_db(user_id, skip, limit, db)
        return {"items": orders, "skip": skip, "limit": limit}


CURL ÖRNEKLERI:
===============

1️⃣ Public endpoint (auth yok):
   
   curl -X GET http://localhost:8000/api/v1/products


2️⃣ Protected endpoint:

   curl -X GET http://localhost:8000/api/v1/users/me \\
     -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."


3️⃣ Admin endpoint:

   curl -X POST http://localhost:8000/api/v1/admin/users \\
     -H "Authorization: Bearer <ADMIN_TOKEN>" \\
     -H "Content-Type: application/json" \\
     -d '{"full_name": "Admin User", "email": "admin@example.com", "password": "Pass123"}'


4️⃣ With query parameters:

   curl -X GET "http://localhost:8000/api/v1/users/507f1f77bcf86cd799439011/orders?skip=0&limit=10" \\
     -H "Authorization: Bearer <TOKEN>"


PYTHON REQUESTS ÖRNEKLERI:
==========================

import requests

# Token al
login_response = requests.post(
    'http://localhost:8000/api/v1/auth/login',
    json={'email': 'john@example.com', 'password': 'SecurePass123'}
)
token = login_response.json()['access_token']

# Protected endpoint'e eriş
headers = {'Authorization': f'Bearer {token}'}
profile = requests.get(
    'http://localhost:8000/api/v1/users/me',
    headers=headers
)
print(profile.json())


HTTP STATUS KODLARI:
====================

✅ 200 OK
   - Request başarılı

✅ 201 Created
   - Yeni resource oluşturuldu

❌ 400 Bad Request
   - Request body validation hatası

❌ 401 Unauthorized
   - Token yok
   - Token geçersiz
   - Token süresi dolmuş
   Örnek: {"detail": "Invalid token"}

❌ 403 Forbidden
   - is_active = False
   - Admin endpoint'e non-admin erişim
   - Yetersiz permissions
   Örnek: {"detail": "Admin access required"}

❌ 404 Not Found
   - User veritabanında bulunamadı
   Örnek: {"detail": "User not found"}

❌ 503 Service Unavailable
   - Database bağlantısı error
   Örnek: {"detail": "Database unavailable"}


JWT TOKEN İÇERİĞİ:
==================

Header:
{
    "alg": "HS256",
    "typ": "JWT"
}

Payload:
{
    "sub": "507f1f77bcf86cd799439011",      // User ID (ObjectId as string)
    "email": "john@example.com",             // Email
    "type": "access",                        // Token tipi (access/refresh)
    "scope": "user",                         // Scope (user/store_owner/admin)
    "is_admin": false,                       // Admin flag
    "exp": 1626785504,                       // Expiration timestamp (30 dak)
    "iat": 1626783704                        // Issued at timestamp
}


SWAGGER UI'DE TEST:
===================

1. http://localhost:8000/docs açın
2. "GET /api/v1/users/me" endpoint'ini bulun
3. "Try it out" basın
4. Login endpoint'inden aldığınız token'ı Authorization header'ına yapıştırın
5. "Execute" basın

Swagger UI "Authorize" butonundan da token girebilirsiniz!
"""
