"""
Users Router - Örnek Template
==============================

Bu dosya, yeni router'lar oluştururken bir şablon işlevi görür.

Kullanım:
1. Bu dosyayı kopyala: cp app/routers/users_example.py app/routers/users.py
2. Gerekli değişiklikleri yap
3. app/routers/__init__.py'ye ekle: from .users import router as users_router
4. app/main.py'ye ekle: app.include_router(users_router, prefix=settings.API_PREFIX)
5. Sunucuyu restart et
"""

from fastapi import APIRouter, status, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


# ==================== SCHEMAS ====================
class UserCreate(BaseModel):
    """Kullanıcı oluşturma request schema'sı"""
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "securepass123",
                "full_name": "John Doe"
            }
        }


class UserResponse(BaseModel):
    """Kullanıcı response schema'sı"""
    id: str
    email: str
    full_name: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "email": "user@example.com",
                "full_name": "John Doe",
                "created_at": "2026-03-18T10:30:00",
                "updated_at": None
            }
        }


# ==================== ROUTER ====================
router = APIRouter(
    prefix="/users",                    # Base route: /api/v1/users
    tags=["users"],                     # Swagger'da grup adı
    responses={404: {"description": "User not found"}},
)


# ==================== MOCK DATA ====================
# Production'da bu Database.get_database() olur
fake_users_db = {
    "1": {
        "id": "1",
        "email": "john@example.com",
        "full_name": "John Doe",
        "created_at": datetime.utcnow(),
    }
}


# ==================== ENDPOINTS ====================

@router.get(
    "/",
    response_model=List[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="Tüm Kullanıcıları Listele",
    tags=["users"],
)
async def list_users(skip: int = 0, limit: int = 10):
    """
    📋 Tüm kullanıcıları listele
    
    **Query Parameters:**
    - `skip`: Kaç kullanıcıyı atla (default: 0)
    - `limit`: Almak istediğin user sayısı (default: 10)
    
    **Response:** Kullanıcı listesi
    """
    users = list(fake_users_db.values())
    return users[skip:skip + limit]


@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Yeni Kullanıcı Oluştur",
)
async def create_user(user_data: UserCreate):
    """
    ➕ Yeni kullanıcı oluştur
    
    **Request Body:**
    ```json
    {
        "email": "newuser@example.com",
        "password": "securepass123",
        "full_name": "Jane Doe"
    }
    ```
    
    **Response:**
    - Yeni oluşturulan kullanıcı bilgileri (ID, email, vb.)
    
    **Status:**
    - 201 Created: Başarılı
    - 400 Bad Request: Eksik/hatalı veri
    - 409 Conflict: Email zaten kayıtlı
    """
    # Kontrol: Email zaten var mı?
    for user in fake_users_db.values():
        if user["email"] == user_data.email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Bu email zaten kayıtlı"
            )
    
    # Yeni user oluştur
    new_user_id = str(len(fake_users_db) + 1)
    new_user = {
        "id": new_user_id,
        "email": user_data.email,
        "full_name": user_data.full_name,
        "created_at": datetime.utcnow(),
        "updated_at": None,
    }
    
    fake_users_db[new_user_id] = new_user
    return new_user


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Kullanıcı Bilgilerini Getir",
)
async def get_user(user_id: str):
    """
    🔍 Spesifik kullanıcının bilgilerini getir
    
    **Path Parameters:**
    - `user_id`: Kullanıcının ID'si (MongoDB ObjectId formatı)
    
    **Response:**
    - Kullanıcı bilgileri
    
    **Status:**
    - 200 OK: Başarılı
    - 404 Not Found: Kullanıcı bulunamadı
    """
    if user_id not in fake_users_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User ID {user_id} bulunamadı"
        )
    
    return fake_users_db[user_id]


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Kullanıcı Güncelle",
)
async def update_user(user_id: str, user_data: UserCreate):
    """
    ✏️ Kullanıcı bilgilerini güncelle
    
    **Path Parameters:**
    - `user_id`: Kullanıcının ID'si
    
    **Request Body:**
    - Email, şifre, full_name, vb.
    
    **Response:**
    - Güncellenmiş kullanıcı bilgileri
    """
    if user_id not in fake_users_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User bulunamadı"
        )
    
    fake_users_db[user_id].update({
        "email": user_data.email,
        "full_name": user_data.full_name,
        "updated_at": datetime.utcnow(),
    })
    
    return fake_users_db[user_id]


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Kullanıcı Sil",
)
async def delete_user(user_id: str):
    """
    🗑️ Kullanıcıyı sil
    
    **Path Parameters:**
    - `user_id`: Silinecek kullanıcının ID'si
    
    **Response:**
    - No content (204)
    
    **Status:**
    - 204 No Content: Başarılı
    - 404 Not Found: Kullanıcı bulunamadı
    """
    if user_id not in fake_users_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User bulunamadı"
        )
    
    del fake_users_db[user_id]
    return None


# ==================== HELPER ENDPOINTS ====================

@router.get(
    "/search/by-email",
    response_model=Optional[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="Email'e Göre Kullanıcı Ara",
)
async def search_user_by_email(email: str):
    """
    🔎 Email adresine göre kullanıcı ara
    
    **Query Parameters:**
    - `email`: Aranacak email adresi
    
    **Response:**
    - Kullanıcı bilgileri veya null
    """
    for user in fake_users_db.values():
        if user["email"].lower() == email.lower():
            return user
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Email '{email}' için kullanıcı bulunamadı"
    )


# ==================== KULLANIM NOTLARI ====================
"""
MONGODB ENTEGRASYONU ÖRNEĞİ:

from app.core.database import get_database
from bson.objectid import ObjectId

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, db = Depends(get_database)):
    # BSON ObjectId'ye çevir
    try:
        user_id_obj = ObjectId(user_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
    # MongoDB'den sor
    user = await db.users.find_one({"_id": user_id_obj})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # MongoDB'deki _id'yi string'e çevir
    user["id"] = str(user.pop("_id"))
    
    return user
"""
