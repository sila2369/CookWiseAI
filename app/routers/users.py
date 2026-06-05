"""
Users Router - Kullanıcı yönetimi endpoint'leri
=================================================

Endpoint'ler:
- GET /users/me → Kendi profili görüntüle
- GET /users/{user_id} → Başka kullanıcı profili (admin veya kendi)
- PUT /users/me → Profil güncelle
- DELETE /users/me → Hesabı sil

Resources:
- Authentication: get_active_user dependency
- Database: get_database dependency
- Response: UserResponse schema
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.database import get_database
from app.core.exceptions import DatabaseConnectionException
from app.dependencies.auth import get_active_user
from app.schemas.user import UserResponse, UserUpdate, FcmTokenRequest

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/users",
    tags=["Users"],
    responses={
        401: {"description": "Unauthorized - Token geçersiz/süresi dolmuş"},
        403: {"description": "Forbidden - Hesap pasif"},
        404: {"description": "User not found"},
        500: {"description": "Server error"},
    }
)


# ==================== ENDPOINTS ====================

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Giriş yapmış kullanıcı profili",
    description=(
        "Bearer token ile doğrulanmış kullanıcının profil bilgilerini döndürür. "
        "Swagger'da test için: /auth/login ile giriş yap → token'ı Authorize'a yapıştır."
    ),
    responses={
        200: {
            "description": "Kullanıcı bilgileri başarıyla döndürüldü",
            "content": {
                "application/json": {
                    "example": {
                        "id": "507f1f77bcf86cd799439011",
                        "full_name": "John Doe",
                        "email": "john@example.com",
                        "phone": "+905551234567",
                        "is_active": True,
                        "is_admin": False,
                        "created_at": "2026-03-18T10:30:00",
                        "updated_at": "2026-03-18T10:30:00"
                    }
                }
            }
        },
        401: {
            "description": "Bearer token eksik, geçersiz veya süresi dolmuş",
            "content": {
                "application/json": {
                    "example": {"detail": "Could not validate credentials"}
                }
            }
        },
        403: {
            "description": "Hesap devre dışı (is_active=false)",
            "content": {
                "application/json": {
                    "example": {"detail": "User account has been deactivated"}
                }
            }
        }
    },
)
async def get_current_user_profile(
    current_user=Depends(get_active_user)
) -> UserResponse:
    """
    Giriş yapmış kullanıcının profil bilgilerini döndür.

    **Bearer token zorunludur.** Token Authorization header'ında gönderilmelidir.

    **Dönen alanlar:** id, full_name, email, phone, is_active, is_admin, created_at, updated_at
    **hashed_password asla dönmez** (güvenlik)

    **Swagger test:** 1) /auth/login ile giriş 2) Authorize butonuna token yapıştır 3) Execute
    """
    logger.info(f"User profile accessed: {current_user.get('email')}")

    # hashed_password kesinlikle response'dan çıkarılır
    user_data = {k: v for k, v in current_user.items() if k != "hashed_password"}
    return UserResponse(**user_data)


@router.put(
    "/me",
    response_model=UserResponse,
    summary="Profil güncelle",
    description="Kendi profil bilgilerini güncelle (full_name, phone)",
)
async def update_current_user_profile(
    update_data: UserUpdate,
    current_user = Depends(get_active_user),
    db = Depends(get_database)
) -> UserResponse:
    """
    Kendi profil bilgilerini güncelle
    
    HTTP Method: PUT
    Endpoint: /users/me
    
    Request Body:
    {
        "full_name": "Jane Doe",  # optional
        "phone": "+905559876543"   # optional
    }
    
    Response (200 OK):
    {
        "id": "507f1f77bcf86cd799439011",
        "full_name": "Jane Doe",
        "email": "john@example.com",
        "phone": "+905559876543",
        "is_active": true,
        "is_admin": false,
        "created_at": "2026-03-18T10:30:00",
        "updated_at": "2026-03-20T15:45:30"
    }
    """
    from app.core.firebase import is_firebase_enabled
    
    user_id = current_user.get("id")
    update_fields = {}
    if update_data.full_name:
        update_fields["full_name"] = update_data.full_name
    if update_data.phone:
        update_fields["phone"] = update_data.phone
    
    if not update_fields:
        return UserResponse(**current_user)
    
    try:
        # Firebase
        if is_firebase_enabled():
            from app.services.firebase_user_service import get_firebase_user_service
            svc = get_firebase_user_service()
            updated_user = await svc.update_user(user_id, **update_fields)
            if not updated_user:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
            logger.info(f"User profile updated: {updated_user.get('email')}")
            return UserResponse(**updated_user)
        
        # MongoDB
        from bson import ObjectId
        from datetime import datetime
        if db is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")
        update_fields["updated_at"] = datetime.utcnow()
        users_collection = db["users"]
        result = await users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_fields}
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        updated_user = await users_collection.find_one({"_id": ObjectId(user_id)})
        updated_user["id"] = str(updated_user.pop("_id"))
        logger.info(f"User profile updated: {updated_user.get('email')}")
        return UserResponse(**updated_user)
    
    except DatabaseConnectionException:
        logger.error(f"Database error during profile update: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database error"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Kullanıcı profilini getir",
    description="Belirtilen kullanıcının profilini getir (admin veya kendi profili)",
)
async def get_user_profile(
    user_id: str,
    current_user = Depends(get_active_user),
    db = Depends(get_database)
) -> UserResponse:
    """
    Belirtilen kullanıcının profilini getir
    
    HTTP Method: GET
    Endpoint: /users/{user_id}
    
    Parametreler:
    - user_id: MongoDB ObjectId (string)
    
    Yetkilendirme:
    - Kendi profil: Her zaman görüntüleyebilir
    - Başka profil: Sadece admin
    
    Response (200 OK):
    {
        "id": "507f1f77bcf86cd799439011",
        "full_name": "Another User",
        "email": "other@example.com",
        "is_active": true,
        "is_admin": false,
        "created_at": "2026-03-18T10:30:00",
        "updated_at": "2026-03-18T10:30:00"
    }
    
    Başarısız:
    - 403: Başka kullanıcının profilini admin olmayan user görüntülemeye çalışması
    - 404: User bulunamadı
    """
    from app.core.firebase import is_firebase_enabled
    
    try:
        current_user_id = current_user.get("id")
        is_admin = current_user.get("is_admin", False)
        
        if user_id != current_user_id and not is_admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot access other user's profile")
        
        # Firebase
        if is_firebase_enabled():
            from app.services.firebase_user_service import get_firebase_user_service
            svc = get_firebase_user_service()
            user = await svc.get_user_by_uid(user_id)
            if not user:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
            return UserResponse(**user)
        
        # MongoDB
        from bson import ObjectId
        if db is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")
        user = await db["users"].find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        user["id"] = str(user.pop("_id"))
        return UserResponse(**user)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user profile"
        )


@router.post(
    "/fcm-token",
    summary="FCM Token Kaydet",
    description="Kullanıcının cihazına gönderilen Firebase Push Notification (FCM) token'ını kaydeder."
)
async def update_fcm_token(
    data: FcmTokenRequest,
    current_user=Depends(get_active_user),
    db=Depends(get_database)
):
    from bson import ObjectId
    from datetime import datetime
    
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
        
    user_id = current_user.get("id")
    
    # Add token to user document (using addToSet to prevent duplicates)
    await db["users"].update_one(
        {"_id": ObjectId(user_id)},
        {
            "$addToSet": {"fcm_tokens": data.token},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    
    return {"success": True, "message": "FCM Token registered successfully"}


# ==================== ÖRNEK KULLANIM ====================

"""
GET /users/me - ÖRNEK KULLANIM
==============================

1️⃣ CURL:
   curl -X GET http://localhost:8000/api/v1/users/me \\
     -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>"

2️⃣ Swagger UI (Önerilen):
   - http://localhost:8000/docs açın
   - POST /auth/login ile giriş yapın, response'dan access_token kopyalayın
   - Sağ üstte "Authorize" butonuna tıklayın
   - Value alanına token'ı yapıştırın (Bearer yazmadan, sadece token)
   - Authorize → Close
   - GET /api/v1/users/me → Try it out → Execute

3️⃣ Python requests:
   import requests
   login = requests.post('http://localhost:8000/api/v1/auth/login',
       json={'email': 'user@example.com', 'password': 'SecurePass123'})
   token = login.json()['access_token']
   me = requests.get('http://localhost:8000/api/v1/users/me',
       headers={'Authorization': f'Bearer {token}'})
   print(me.json())

4️⃣ JavaScript fetch:
   const login = await fetch('/api/v1/auth/login', {
     method: 'POST',
     headers: {'Content-Type': 'application/json'},
     body: JSON.stringify({email: 'user@example.com', password: 'SecurePass123'})
   });
   const {access_token} = await login.json();
   const me = await fetch('/api/v1/users/me', {
     headers: {'Authorization': `Bearer ${access_token}`}
   });
   console.log(await me.json());

5️⃣ Başarılı Response (200):
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
   (hashed_password YOK - güvenlik)

CURL ÖRNEKLERI (diğer endpoint'ler):
===============

1️⃣ Kendi profili görüntüle:

curl -X GET http://localhost:8000/api/v1/users/me \\
  -H "Authorization: Bearer <YOUR_TOKEN>"


2️⃣ Profil güncelle:

curl -X PUT http://localhost:8000/api/v1/users/me \\
  -H "Authorization: Bearer <YOUR_TOKEN>" \\
  -H "Content-Type: application/json" \\
  -d '{
    "full_name": "Jane Doe Updated",
    "phone": "+905559876543"
  }'


3️⃣ Başka kullanıcıyı görüntüle (admin):

curl -X GET http://localhost:8000/api/v1/users/507f1f77bcf86cd799439011 \\
  -H "Authorization: Bearer <ADMIN_TOKEN>"


4️⃣ Kendi profilini güncelle (sadece phone):

curl -X PUT http://localhost:8000/api/v1/users/me \\
  -H "Authorization: Bearer <YOUR_TOKEN>" \\
  -H "Content-Type: application/json" \\
  -d '{
    "phone": "+905551111111"
  }'


SWAGGER UI:
===========

1. http://localhost:8000/docs açın
2. "GET /api/v1/users/me" endpoint'i bulun
3. "Try it out" basın
4. Token'ı Authorization header'ına yapıştırın
5. "Execute" basın


PYTHON TEST:
============

import requests

# Login
login_resp = requests.post(
    'http://localhost:8000/api/v1/auth/login',
    json={'email': 'john@example.com', 'password': 'SecurePass123'}
)
token = login_resp.json()['access_token']

# Kendi profili görüntüle
headers = {'Authorization': f'Bearer {token}'}
profile = requests.get(
    'http://localhost:8000/api/v1/users/me',
    headers=headers
)
print(profile.json())

# Profil güncelle
update = requests.put(
    'http://localhost:8000/api/v1/users/me',
    json={'full_name': 'Jane Doe'},
    headers=headers
)
print(update.json())
"""
