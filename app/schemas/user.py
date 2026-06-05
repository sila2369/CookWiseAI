"""
User Schemas - Pydantic Request/Response Models
================================================

API request/response validation ve documentation.
TypeScript/Swagger documentation otomatik oluşur.

Kullanım:
    # Request validation
    @router.post("/register", response_model=UserResponse)
    async def register(user: UserCreate):
        # Pydantic otomatik validate eder
        # email format, password uzunluk, vb.
        pass
    
    # Response serialization
    user_response = UserResponse.model_validate(user_dict)
"""

from pydantic import BaseModel, EmailStr, field_validator, ConfigDict
from typing import Optional
from datetime import datetime


# ==================== REQUEST SCHEMAS ====================

class UserCreate(BaseModel):
    """
    Kullanıcı Kayıt (Register) Request Schema
    
    POST /api/v1/auth/register
    İstek gövdesi
    """
    
    full_name: str
    """Tam ad (minimum 2 karakter)"""
    
    email: EmailStr
    """Email adresi (unique, validate edilir)"""
    
    password: str
    """Şifre (minimum 8 karakter, 1 büyük harf, 1 rakam)"""
    
    phone: Optional[str] = None
    """Telefon numarası (opsiyonel, +905551234567 formatı)"""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "full_name": "John Doe",
                "email": "john@example.com",
                "password": "SecurePass123",
                "phone": "+905551234567"
            }
        }
    )
    
    @field_validator('full_name')
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        """
        Tam adını doğrula
        - Minimum 2 karakter
        - Boş olmayacak
        """
        v = v.strip()
        
        if len(v) < 2:
            raise ValueError('Full name must be at least 2 characters')
        
        if len(v) > 100:
            raise ValueError('Full name must be less than 100 characters')
        
        return v
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """
        Şifre gücünü doğrula
        - Minimum 8 karakter
        - En az 1 büyük harf
        - En az 1 rakam
        - Zayıf şifreler kabul etme
        """
        from string import ascii_uppercase, digits
        
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        
        if len(v) > 128:
            raise ValueError('Password must be less than 128 characters')
        
        if not any(c in ascii_uppercase for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        
        if not any(c in digits for c in v):
            raise ValueError('Password must contain at least one digit')
        
        # Genel zayıf şifreler
        weak_passwords = {
            "password", "123456", "qwerty", "admin", "letmein",
            "welcome", "monkey", "dragon", "master", "sunshine"
        }
        
        if v.lower() in weak_passwords:
            raise ValueError('Password is too common. Please choose a stronger password')
        
        return v
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        """
        Telefon numarasını doğrula (opsiyonel)
        Format: +[country code][number]
        Örnek: +905551234567
        """
        if v is None:
            return None
        
        import re
        
        v = v.strip()
        
        # +country_code number formatı (10-15 digits)
        pattern = r'^\+\d{10,15}$'
        
        if not re.match(pattern, v):
            raise ValueError(
                'Phone must be in format: +[country_code][number] '
                '(e.g., +905551234567)'
            )
        
        return v


class UserLogin(BaseModel):
    """
    Kullanıcı Giriş (Login) Request Schema
    
    POST /api/v1/auth/login
    İstek gövdesi
    """
    
    email: EmailStr
    """Email adresi"""
    
    password: str
    """Şifre"""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "john@example.com",
                "password": "SecurePass123"
            }
        }
    )


class UserUpdate(BaseModel):
    """
    Kullanıcı Bilgisi Güncelleme
    
    PUT /api/v1/users/{user_id}
    Tüm alanlar opsiyonel (sadece değiştirilecekler gönder)
    """
    
    full_name: Optional[str] = None
    """Yeni tam ad"""
    
    phone: Optional[str] = None
    """Yeni telefon numarası"""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "full_name": "Jane Doe",
                "phone": "+905551234567"
            }
        }
    )
    
    @field_validator('full_name')
    @classmethod
    def validate_full_name(cls, v: Optional[str]) -> Optional[str]:
        """Tam adını doğrula (opsiyonel)"""
        if v is None:
            return None
        
        v = v.strip()
        
        if len(v) < 2:
            raise ValueError('Full name must be at least 2 characters')
        
        if len(v) > 100:
            raise ValueError('Full name must be less than 100 characters')
        
        return v


# ==================== FCM TOKEN ====================

class FcmTokenRequest(BaseModel):
    """
    Firebase FCM Token kaydetme isteği
    
    POST /api/v1/users/fcm-token
    """
    token: str
    """Cihazın FCM Token'ı"""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "token": "dck_..._asdf"
            }
        }
    )

# ==================== RESPONSE SCHEMAS ====================

class UserResponse(BaseModel):
    """
    Kullanıcı Response Schema (Public)
    
    GET, POST, PUT endpoint'lerinin response'ı
    ⚠️ Hashed password YAPMAZ included!
    """
    
    id: str
    """MongoDB ObjectId (string olarak)"""
    
    full_name: str
    """Tam ad"""
    
    email: str
    """Email adresi"""
    
    phone: Optional[str] = None
    """Telefon numarası (opsiyonel)"""
    
    is_active: bool
    """Hesap aktif mi?"""
    
    is_admin: bool
    """Admin mi?"""
    
    is_verified: bool
    """Email doğrulandı mı?"""
    
    created_at: datetime
    """Oluşturulma tarihi"""
    
    updated_at: Optional[datetime] = None
    """Son güncellenme tarihi"""
    
    model_config = ConfigDict(
        from_attributes=True,  # DB model'den otomatik dönüştür
        json_schema_extra={
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "full_name": "John Doe",
                "email": "john@example.com",
                "phone": "+905551234567",
                "is_active": True,
                "is_admin": False,
                "is_verified": False,
                "created_at": "2026-03-18T10:30:00",
                "updated_at": "2026-03-18T10:30:00"
            }
        }
    )


class UserListResponse(BaseModel):
    """
    Kullanıcı Listesi Response (Multiple Users)
    
    GET /api/v1/users
    """
    
    items: list[UserResponse]
    """Kullanıcı listesi"""
    
    total: int
    """Toplam kullanıcı sayısı"""
    
    skip: int
    """Atlanan kayıt sayısı"""
    
    limit: int
    """Maksimum kayıt sayısı"""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "id": "507f1f77bcf86cd799439011",
                        "full_name": "John Doe",
                        "email": "john@example.com",
                        "phone": "+905551234567",
                        "is_active": True,
                        "is_admin": False,
                        "created_at": "2026-03-18T10:30:00",
                        "updated_at": None
                    }
                ],
                "total": 1,
                "skip": 0,
                "limit": 100
            }
        }
    )


# ==================== TOKEN SCHEMAS ====================

class TokenResponse(BaseModel):
    """
    JWT Token Response Schema
    
    POST /api/v1/auth/login → TokenResponse
    """
    
    access_token: str
    """JWT access token"""
    
    token_type: str = "bearer"
    """Token tipi (daima 'bearer')"""
    
    expires_in: int
    """Token geçerlilik süresi (saniye cinsinden)"""
    
    user: UserResponse
    """Giriş yapan kullanıcı bilgileri"""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 1800,
                "user": {
                    "id": "507f1f77bcf86cd799439011",
                    "full_name": "John Doe",
                    "email": "john@example.com",
                    "phone": "+905551234567",
                    "is_active": True,
                    "is_admin": False,
                    "created_at": "2026-03-18T10:30:00",
                    "updated_at": None
                }
            }
        }
    )


class TokenPayload(BaseModel):
    """
    JWT Token Payload (Internal)
    
    JWT token'ın içinde encode edilen veriler
    Dışarıya expose edilmez, iç kullanım
    """
    
    sub: str
    """Subject - User ID (MongoDB ObjectId as string)"""
    
    email: str
    """User email"""
    
    exp: datetime
    """Expiration time"""
    
    iat: datetime
    """Issued at time"""
    
    is_admin: bool
    """Is user admin?"""


# ==================== ERROR SCHEMAS ====================

class ErrorResponse(BaseModel):
    """
    Error Response Schema
    
    Exception handler'lar bu format'ta response döner
    """
    
    error: str
    """Hata tipi (e.g., 'validation_error', 'unauthorized')"""
    
    detail: str
    """Hata detayı"""
    
    status_code: int
    """HTTP status code"""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": "validation_error",
                "detail": "Email is already registered",
                "status_code": 409
            }
        }
    )


# ==================== UTILITY SCHEMAS ====================

class MessageResponse(BaseModel):
    """
    Basit mesaj response'ı
    
    Silme, logout gibi işlemler için
    """
    
    message: str
    """Başarı/bilgi mesajı"""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "User deleted successfully"
            }
        }
    )


# ==================== EMBEDDED SCHEMAS ====================

class UserInRegistration(BaseModel):
    """
    Registration response'ında gösterilecek minimal user info
    
    Tam UserResponse yerine daha hafif response
    """
    
    id: str
    """User ID"""
    
    email: str
    """Email"""
    
    full_name: str
    """Tam ad"""
    
    created_at: datetime
    """Oluşturulma tarihi"""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "email": "john@example.com",
                "full_name": "John Doe",
                "created_at": "2026-03-18T10:30:00"
            }
        }
    )
