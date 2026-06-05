"""
Auth Router - Kimlik doğrulama API endpoint'leri
=================================================

Tüm authentication endpoint'leri:
- POST /auth/register → Yeni kullanıcı kaydı
- POST /auth/login → Kullanıcı girişi (JWT token)

Teknoloji:
- FastAPI APIRouter: URL prefix ve tag'ler ile organize
- Dependency Injection: Database ve AuthService otomatik inject
- Pydantic: Request/Response validation
- HTTP Status Codes: Doğru durum kodları (201, 200, 400, 409, 500)

Türkçe Error Messages:
- 400: Bad Request (validation hatası)
- 409: Conflict (email zaten kayıtlı)
- 500: Internal Server Error (database hatası)

Örnek Kullanım:
---------------
# Request
POST /auth/register
Content-Type: application/json

{
    "full_name": "John Doe",
    "email": "john@example.com",
    "password": "SecurePass123",
    "phone": "+905551234567"
}

# Response (201 Created)
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
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.database import get_database
from app.core.exceptions import (
    InvalidCredentialsException,
    DatabaseConnectionException,
    DuplicateDocumentException,
    UnverifiedEmailException
)
from app.services.auth_service import AuthService
from app.schemas.user import UserCreate, UserResponse, UserLogin, TokenResponse

logger = logging.getLogger(__name__)


# ==================== ROUTER SETUP ====================
router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
    responses={
        400: {"description": "Validation error"},
        409: {"description": "Email already registered"},
        500: {"description": "Server error"},
    }
)


class FirebaseLoginRequest(BaseModel):
    id_token: str = Field(..., min_length=10)


class VerifyEmailRequest(BaseModel):
    email: str
    code: str


# ==================== DEPENDENCY INJECTION ====================
async def get_auth_service(db=Depends(get_database)) -> AuthService:
    """
    AuthService dependency injection.
    Firebase kullanılsa bile bazı akışlar (örn. firebase-login upsert)
    MongoDB kullanıcı koleksiyonuna ihtiyaç duyar.
    """
    return AuthService(db)


# ==================== ENDPOINTS ====================

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Yeni kullanıcı kaydı",
    description="Yeni bir kullanıcı hesabı oluşturur",
    responses={
        201: {
            "description": "Kullanıcı başarıyla kayıtlandı",
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
        400: {
            "description": "Validation hatası (email format, şifre gücü, vb.)",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "type": "string_pattern",
                                "loc": ["body", "email"],
                                "msg": "Input should be a valid email [type=string_pattern, input_value='invalid-email', input_type=str]",
                                "input": "invalid-email"
                            }
                        ]
                    }
                }
            }
        },
        409: {
            "description": "Email zaten kayıtlı",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Email 'john@example.com' is already registered"
                    }
                }
            }
        },
        500: {
            "description": "Server hatası (database bağlantısı, vb.)",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An unexpected error occurred"
                    }
                }
            }
        }
    }
)
async def register(
    user_data: UserCreate,
    auth_service: AuthService = Depends(get_auth_service)
) -> UserResponse:
    """
    Yeni kullanıcı hesabı kayıt işlemi
    
    HTTP Method: POST
    Endpoint: /auth/register
    
    İstek Gövdesi (Request Body):
    ----------------------------
    {
        "full_name": "string (2-100 karakter)",
        "email": "string (valid email)",
        "password": "string (min 8 chars, 1 uppercase, 1 digit)",
        "phone": "string (optional, +905551234567 formatı)"
    }
    
    Başarılı Response (HTTP 201):
    ----------------------------
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
    
    Olası Hatalar:
    ---------------
    - 400 Bad Request: Validation hatası
      * Email format hatalı
      * Şifre yeterince güçlü değil
      * Tam ad çok kısa/uzun
      * Telefon formatı hatalı
    
    - 409 Conflict: Email zaten kayıtlı
      * response: {"detail": "Email '...' is already registered"}
    
    - 500 Internal Server Error: Database hatası
      * MongoDB bağlantısı başarısız
    
    İşlem Adımları:
    ---------------
    1. Pydantic otomatik validation:
       - Email format kontrol
       - Şifre gücü kontrolü
       - Tam ad uzunluğu kontrolü
    
    2. AuthService.register() çağrısı:
       - Email tekrarı kontrolü
       - Şifre hashing (bcrypt)
       - MongoDB'ye kayıt
    
    3. Response oluşturma:
       - hashed_password hariç tutma
       - ISO format timestamps
       - Başarı kodu (201) döndürme
    
    Başarı Senaryosu:
    -----------------
    POST /auth/register
    {
        "full_name": "John Doe",
        "email": "john@example.com",
        "password": "SecurePass123",
        "phone": "+905551234567"
    }
    
    ↓ (201 Created)
    
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
    
    Hata Senaryosu (Email zaten kayıtlı):
    ------
    POST /auth/register
    {
        "full_name": "Jane Doe",
        "email": "john@example.com",  # ← Zaten kayıtlı!
        "password": "SecurePass123"
    }
    
    ↓ (409 Conflict)
    
    {
        "detail": "Email 'john@example.com' is already registered"
    }
    
    Hata Senaryosu (Şifre çok zayıf):
    ------
    POST /auth/register
    {
        "full_name": "Jane Doe",
        "email": "jane@example.com",
        "password": "weak"  # ← 8 karakterden az!
    }
    
    ↓ (422 Unprocessable Entity)
    
    {
        "detail": [
            {
                "type": "string_too_short",
                "loc": ["body", "password"],
                "msg": "String should have at least 8 characters"
            }
        ]
    }
    
    Args:
        user_data (UserCreate): Kayıt istek şeması
            - full_name: Tam ad (2-100 chars)
            - email: Email adresi (unique, valid)
            - password: Şifre (min 8 chars, validators)
            - phone: Telefon (opsiyonel)
        
        auth_service (AuthService): Dependency injection ile sağlanan service
    
    Returns:
        UserResponse: Kayıt başarılı, kullanıcı bilgileri (hashed_password hariç)
    
    Raises:
        HTTPException 400: Pydantic validation hatası (otomatik)
        HTTPException 409: Email zaten kayıtlı
        HTTPException 500: Database hatası
    """
    
    try:
        # AuthService'i kullanarak kaydı gerçekleştir
        user_response = await auth_service.register(user_data)
        return user_response
    
    except DuplicateDocumentException as e:
        # Email zaten kayıtlı - 409 Conflict
        logger.warning(f"Registration failed: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message
        )
    
    except DatabaseConnectionException as e:
        # MongoDB bağlantısı hatası - 503 Service Unavailable
        logger.error(f"Database connection error: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service is temporarily unavailable"
        )
    
    except Exception as e:
        # Beklenmeyen hatalar - 500 Internal Server Error
        import traceback
        logger.error(f"Unexpected error during registration: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during registration"
        )


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Kullanıcı girişi",
    description="Kullanıcı email + şifre ile giriş yapır ve JWT token alır",
    responses={
        200: {
            "description": "Giriş başarılı, JWT token döndürüldü",
            "content": {
                "application/json": {
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
                            "updated_at": "2026-03-18T10:30:00"
                        }
                    }
                }
            }
        },
        400: {
            "description": "Validation hatası",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "type": "string_pattern",
                                "loc": ["body", "email"],
                                "msg": "Input should be a valid email"
                            }
                        ]
                    }
                }
            }
        },
        401: {
            "description": "Kimlik doğrulama başarısız (email bulunamadı veya şifre yanlış)",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid email or password"
                    }
                }
            }
        },
        500: {
            "description": "Server hatası",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An unexpected error occurred during login"
                    }
                }
            }
        }
    }
)
async def login(
    user_data: UserLogin,
    auth_service: AuthService = Depends(get_auth_service)
) -> TokenResponse:
    """
    Kullanıcı girişi (login) endpoint'i
    
    HTTP Method: POST
    Endpoint: /auth/login
    
    İstek Gövdesi (Request Body):
    ----------------------------
    {
        "email": "string (valid email)",
        "password": "string"
    }
    
    Başarılı Response (HTTP 200):
    ----------------------------
    {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "token_type": "bearer",
        "expires_in": 1800,
        "user": {
            "id": "507f1f77bcf86cd799439011",
            "full_name": "John Doe",
            "email": "john@example.com",
            "phone": "+905551234567",
            "is_active": true,
            "is_admin": false,
            "created_at": "2026-03-18T10:30:00",
            "updated_at": "2026-03-18T10:30:00"
        }
    }
    
    Olası Hatalar:
    ---------------
    - 400 Bad Request: Validation hatası
      * Email format hatalı
      * Password alanı boş
    
    - 401 Unauthorized: Kimlik doğrulama başarısız
      * Email bulunamadı
      * Şifre yanlış
      * Response: {"detail": "Invalid email or password"}
      
      NOT: Güvenlik sebebiyle "email bulunamadı" ile "şifre yanlış"
           arasında ayırım yapmıyoruz (timing attack önleme)
    
    - 500 Internal Server Error: Database hatası
      * MongoDB bağlantısı başarısız
    
    İşlem Adımları:
    ---------------
    1. Pydantic otomatik validation:
       - Email format kontrol
       - Password alanı dolu mu kontrol
    
    2. AuthService.login() çağrısı:
       - Email ile kullanıcı ara
       - Şifre doğrulaması (bcrypt)
       - Başarılıysa JWT token oluştur
    
    3. Response oluşturma:
       - access_token (JWT)
       - token_type ("bearer")
       - expires_in (30 dakika = 1800 saniye)
       - user (hashed_password hariç)
    
    Başarı Senaryosu:
    -----------------
    POST /auth/login
    {
        "email": "john@example.com",
        "password": "SecurePass123"
    }
    
    ↓ (200 OK)
    
    {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "token_type": "bearer",
        "expires_in": 1800,
        "user": {
            "id": "507f1f77bcf86cd799439011",
            "full_name": "John Doe",
            "email": "john@example.com",
            "phone": "+905551234567",
            "is_active": true,
            "is_admin": false,
            "created_at": "2026-03-18T10:30:00",
            "updated_at": "2026-03-18T10:30:00"
        }
    }
    
    Hata Senaryosu (Email bulunamadı eller şifre yanlış):
    ------
    POST /auth/login
    {
        "email": "wrong@example.com",
        "password": "SecurePass123"
    }
    
    ↓ (401 Unauthorized)
    
    {
        "detail": "Invalid email or password"
    }
    
    Hata Senaryosu (Şifre yanlış):
    ------
    POST /auth/login
    {
        "email": "john@example.com",
        "password": "WrongPassword123"
    }
    
    ↓ (401 Unauthorized)
    
    {
        "detail": "Invalid email or password"
    }
    
    JWT Token Kullanımı:
    -------------------
    Başarılı login sonrası, döndürülen access_token'ı
    sonraki isteklerde Authorization header'ında kullan:
    
    GET /api/v1/users/me
    Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
    
    Args:
        user_data (UserLogin): Giriş istek şeması
            - email: Email adresi
            - password: Şifre
        
        auth_service (AuthService): Dependency injection ile sağlanan service
    
    Returns:
        TokenResponse: Giriş başarılı, JWT token + user info
    
    Raises:
        HTTPException 400: Pydantic validation hatası (otomatik)
        HTTPException 401: Email bulunamadı veya şifre yanlış
        HTTPException 500: Database hatası
    """
    
    try:
        # AuthService'i kullanarak giriş işlemini gerçekleştir
        token_response = await auth_service.login(user_data)
        return token_response
    
    except InvalidCredentialsException as e:
        # Email bulunamadı veya şifre yanlış - 401 Unauthorized
        logger.warning(f"Login failed: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    except UnverifiedEmailException as e:
        # Email doğrulanmamış - 403 Forbidden
        logger.warning(f"Login failed: {e.message}")
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message,
        )
    
    except DatabaseConnectionException as e:
        # MongoDB bağlantısı hatası - 503 Service Unavailable
        logger.error(f"Database connection error: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service is temporarily unavailable"
        )
    
    except Exception as e:
        # Beklenmeyen hatalar - 500 Internal Server Error
        logger.error(f"Unexpected error during login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during login"
        )


@router.post(
    "/firebase-login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Firebase Google OAuth ile giriş",
    description="Frontend'den gelen Firebase ID token doğrulanır ve CookWise JWT döndürülür.",
)
async def firebase_login(
    payload: FirebaseLoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    # Google OAuth popup akışından dönen Firebase ID token backend'de doğrulanır.
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


@router.post(
    "/verify-email",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Email adresi doğrulama",
)
async def verify_email(
    payload: VerifyEmailRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    try:
        return await auth_service.verify_email(payload.email, payload.code)
    except InvalidCredentialsException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )
    except Exception as e:
        logger.error(f"Error during email verification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Doğrulama işlemi sırasında bir hata oluştu"
        )


# ==================== ENDPOINT ÖRNEKLER VE TEST SENARYOLARI ====================
"""
CURL EXAMPLES:
==============

1️⃣ Başarılı Giriş (HTTP 200)
-----
curl -X POST http://localhost:8000/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{
    "email": "john@example.com",
    "password": "SecurePass123"
  }'

Response:
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1MDdmMWY3N2JjZjg2Y2Q3OTk0MzkwMTEiLCJlbWFpbCI6ImpvaG5AZXhhbXBsZS5jb20iLCJ0eXBlIjoiYWNjZXNzIiwic2NvcGUiOiJ1c2VyIiwiZXhwIjoxNjI2Nzg1NTA0LCJpYXQiOjE2MjY3ODM3MDR9.sKl_N7JZvnHbE...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": "507f1f77bcf86cd799439011",
    "full_name": "John Doe",
    "email": "john@example.com",
    "phone": "+905551234567",
    "is_active": true,
    "is_admin": false,
    "created_at": "2026-03-18T10:30:00",
    "updated_at": "2026-03-18T10:30:00"
  }
}


2️⃣ Email Bulunamadı veya Şifre Yanlış (HTTP 401)
-----
curl -X POST http://localhost:8000/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{
    "email": "john@example.com",
    "password": "WrongPassword123"
  }'

Response:
{
  "detail": "Invalid email or password"
}


3️⃣ Invalid Email Format (HTTP 422)
-----
curl -X POST http://localhost:8000/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{
    "email": "not-an-email",
    "password": "SecurePass123"
  }'

Response:
{
  "detail": [
    {
      "type": "string_pattern",
      "loc": ["body", "email"],
      "msg": "Input should be a valid email [type=string_pattern, ...]",
      "input": "not-an-email"
    }
  ]
}


4️⃣ Missing Password (HTTP 422)
-----
curl -X POST http://localhost:8000/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{
    "email": "john@example.com"
  }'

Response:
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "password"],
      "msg": "Field required [type=missing, input_value={...}, input_type=dict]"
    }
  ]
}


PYTHON REQUESTS EXAMPLE:
========================

import requests

# Başarılı giriş
response = requests.post(
    'http://localhost:8000/auth/login',
    json={
        'email': 'john@example.com',
        'password': 'SecurePass123'
    }
)

if response.status_code == 200:
    print("✅ Giriş başarılı!")
    data = response.json()
    access_token = data['access_token']
    print(f"Token: {access_token[:50]}...")
    print(f"User: {data['user']['full_name']}")
    
    # Token'ı sonraki isteklerde kullan
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    # requests.get('/api/v1/users/me', headers=headers)
    
elif response.status_code == 401:
    print("❌ Email bulunamadı veya şifre yanlış!")
    print(response.json()['detail'])
else:
    print(f"❌ Hata: {response.status_code}")
    print(response.json())


JAVASCRIPT/FETCH EXAMPLE:
=========================

(async () => {
    try {
        const response = await fetch('http://localhost:8000/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                email: 'john@example.com',
                password: 'SecurePass123'
            })
        });

        if (response.ok) {
            const data = await response.json();
            console.log('✅ Giriş başarılı!');
            console.log(f'Token: {data.access_token.substring(0, 50)}...');
            console.log(f'User: {data.user.full_name}');
            
            // Token'ı localStorage'ye kaydet
            localStorage.setItem('access_token', data.access_token);
            
            // Token'ı sonraki isteklerde kullan
            // fetch('/api/v1/users/me', {
            //     headers: {
            //         'Authorization': `Bearer ${data.access_token}`
            //     }
            // })
        } else if (response.status === 401) {
            console.log('❌ Email bulunamadı veya şifre yanlış!');
            const error = await response.json();
            console.log(error.detail);
        } else {
            console.log('❌ Hata:', response.status);
        }
    } catch (error) {
        console.error('Fetch hatası:', error);
    }
})();


SWAGGER/OPENAPI:
================

http://localhost:8000/docs

Swagger UI'de endpoint'i test edebilirsiniz:
1. /auth/login endpoint'ini açın
2. "Try it out" tuşuna basın
3. Request body'yi doldurun
4. "Execute" basın
5. Response'u görün


JWT TOKEN DÖKÜMENTASYONu:
======================

Döndürülen token yapısı (JWT):
Header: {
    "alg": "HS256",
    "typ": "JWT"
}

Payload: {
    "sub": "507f1f77bcf86cd799439011",    // User ID
    "email": "john@example.com",           // Email
    "type": "access",                      // Token tipi
    "scope": "user",                       // Admin veya user scope
    "exp": 1626785504,                     // Expiration timestamp (30 dakika sonra)
    "iat": 1626783704                      // Issued at timestamp
}

Token geçerliliği: 30 dakika (1800 saniye)

Token decode örneği (jwt.io'da veya Python'da):
from jose import jwt

token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
decoded = jwt.decode(token, "your-secret-key", algorithms=["HS256"])
print(decoded)
# {
#     "sub": "507f1f77bcf86cd799439011",
#     "email": "john@example.com",
#     "type": "access",
#     "scope": "user",
#     "exp": 1626785504,
#     "iat": 1626783704
# }
"""
"""
CURL EXAMPLES:
==============

1️⃣ Başarılı Kayıt (HTTP 201)
-----
curl -X POST http://localhost:8000/auth/register \\
  -H "Content-Type: application/json" \\
  -d '{
    "full_name": "John Doe",
    "email": "john@example.com",
    "password": "SecurePass123",
    "phone": "+905551234567"
  }'

Response:
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


2️⃣ Email Zaten Kayıtlı (HTTP 409)
-----
curl -X POST http://localhost:8000/auth/register \\
  -H "Content-Type: application/json" \\
  -d '{
    "full_name": "Jane Doe",
    "email": "john@example.com",
    "password": "AnotherPass123"
  }'

Response:
{
  "detail": "Email 'john@example.com' is already registered"
}


3️⃣ Şifre Çok Zayıf (HTTP 422)
-----
curl -X POST http://localhost:8000/auth/register \\
  -H "Content-Type: application/json" \\
  -d '{
    "full_name": "Jane Doe",
    "email": "jane@example.com",
    "password": "weak"
  }'

Response:
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "password"],
      "msg": "String should have at least 8 characters [type=string_too_short, input_value='weak', input_type=str]",
      "input": "weak"
    }
  ]
}


4️⃣ Invalid Email Format (HTTP 422)
-----
curl -X POST http://localhost:8000/auth/register \\
  -H "Content-Type: application/json" \\
  -d '{
    "full_name": "Jane Doe",
    "email": "not-an-email",
    "password": "SecurePass123"
  }'

Response:
{
  "detail": [
    {
      "type": "string_pattern",
      "loc": ["body", "email"],
      "msg": "Input should be a valid email [type=string_pattern, ...]",
      "input": "not-an-email"
    }
  ]
}


PYTHON REQUESTS EXAMPLE:
========================

import requests
import json

# Başarılı kayıt
response = requests.post(
    'http://localhost:8000/auth/register',
    json={
        'full_name': 'John Doe',
        'email': 'john@example.com',
        'password': 'SecurePass123',
        'phone': '+905551234567'
    }
)

if response.status_code == 201:
    print("✅ Kayıt başarılı!")
    user = response.json()
    print(f"User ID: {user['id']}")
    print(f"Email: {user['email']}")
elif response.status_code == 409:
    print("❌ Email zaten kayıtlı!")
    print(response.json()['detail'])
else:
    print(f"❌ Hata: {response.status_code}")
    print(response.json())


SWAGGER/OPENAPI:
================

http://localhost:8000/docs

Swagger UI'de endpoint'i test edebilirsiniz:
1. /auth/register endpoint'ini açın
2. "Try it out" tuşuna basın
3. Request body'yi doldurun
4. "Execute" basın
5. Response'u görün
"""
