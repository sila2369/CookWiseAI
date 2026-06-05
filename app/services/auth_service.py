"""
Auth Service - Kimlik doğrulama ve yetkilendirme işlemleri
============================================================

Backend: MongoDB veya Firebase (USE_FIREBASE_AUTH=True ise)
"""

import logging
import random
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from app.core.database import Database
from app.core.config import settings
from app.core.firebase import init_firebase
from app.core.security import hash_password, verify_password, create_access_token
from app.core.exceptions import (
    DuplicateDocumentException,
    InvalidCredentialsException,
    DatabaseConnectionException,
    UnverifiedEmailException
)
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, TokenResponse, UserLogin
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)


def is_config_admin_email(email: Optional[str]) -> bool:
    """Return True when email is listed as an app-level admin."""
    normalized = (email or "").strip().lower()
    return bool(normalized and normalized in {item.strip().lower() for item in settings.ADMIN_EMAILS})


def _is_firebase_auth():
    """Firebase kullanıcı yönetimi aktif mi?"""
    from app.core.firebase import is_firebase_enabled
    return is_firebase_enabled()


class AuthService:
    """
    Kimlik doğrulama ve yetkilendirme işlemleri
    
    Attributes:
    -----------
    db : Database
        MongoDB veritabanı bağlantısı
    
    Methods:
    --------
    register() : Yeni kullanıcı kaydı
    login() : Kullanıcı girişi
    """
    
    def __init__(self, db: Optional[Database] = None):
        """
        AuthService'i initialize et.
        Firebase kullanılıyorsa db None olabilir.
        """
        self.db = db
        self.users_collection = db["users"] if db is not None else None
        self._firebase_auth_mode = _is_firebase_auth()
        self._firebase_svc = None

        # Firebase user-store modu aktifse (tam Firebase auth) her zaman service'i hazırla.
        # Değilse bile, Google OAuth (id_token) login için credentials varsa service'i hazırla.
        can_enable_oauth = bool(getattr(settings, "FIREBASE_CREDENTIALS_PATH", None))
        if self._firebase_auth_mode or can_enable_oauth:
            init_firebase(
                settings.FIREBASE_CREDENTIALS_PATH,
                settings.FIREBASE_PROJECT_ID,
            )
            from app.services.firebase_user_service import get_firebase_user_service
            self._firebase_svc = get_firebase_user_service()
    
    
    async def register(self, user_data: UserCreate) -> UserResponse:
        """
        Yeni kullanıcı kaydı
        
        Adımlar:
        1. Email'in daha önce kayıtlı olup olmadığını kontrol et
        2. Email tekrarlandıysa DuplicateDocumentException fırlat
        3. Şifreyi hash'le (bcrypt)
        4. Kullanıcı dokümentini oluştur
        5. MongoDB'ye insert et
        6. Başarılı response döndür
        
        Args:
            user_data (UserCreate): Kayıt request şeması
                {
                    "full_name": "John Doe",
                    "email": "john@example.com",
                    "password": "SecurePass123",
                    "phone": "+905551234567" (optional)
                }
        
        Returns:
            UserResponse: Kayıt başarılı, kullanıcı bilgileri (şifre hariç)
                {
                    "id": "507f1f77bcf86cd799439011",
                    "full_name": "John Doe",
                    "email": "john@example.com",
                    "phone": "+905551234567",
                    "is_active": true,
                    "is_admin": false,
                    "created_at": "2026-03-18T10:30:00Z",
                    "updated_at": "2026-03-18T10:30:00Z"
                }
        
        Raises:
            DuplicateDocumentException: Email zaten kayıtlı ise (HTTP 409)
            DatabaseConnectionException: MongoDB bağlantısı hatası (HTTP 503)
            Exception: Beklenmeyen hatalar
        
        Örnek Kullanım:
        ---------------
        try:
            user = await auth_service.register(UserCreate(
                full_name="John Doe",
                email="john@example.com",
                password="SecurePass123",
                phone="+905551234567"
            ))
            # Başarılı kayıt
            print(user)  # UserResponse(id=..., full_name="John Doe", ...)
        
        except DuplicateDocumentException:
            # Email zaten kayıtlı
            return JSONResponse(
                status_code=409,
                content={"detail": "Email already registered"}
            )
        
        except DatabaseConnectionException:
            # Database bağlantısı hatası
            return JSONResponse(
                status_code=503,
                content={"detail": "Database connection error"}
            )
        """
        
        logger.info(f"User registration started for email: {user_data.email}")
        
        # ==================== FIREBASE BACKEND ====================
        if self._firebase_auth_mode and self._firebase_svc:
            return await self._register_firebase(user_data)
        
        try:
            # ==================== MONGODB BACKEND ====================
            # ==================== ADIM 1: EMAIL KONTROLÜ ====================
            # Email'in daha önce kaydedilip kaydedilmediğini kontrol et
            query = User.get_user_by_email_query(user_data.email)
            existing_user = await self.users_collection.find_one(query)
            
            if existing_user:
                logger.warning(f"Registration failed: Email already exists: {user_data.email}")
                raise DuplicateDocumentException(
                    collection="users",
                    field="email",
                    value=user_data.email,
                    message=f"Email '{user_data.email}' is already registered",
                )
            
            
            # ==================== ADIM 2: ŞİFRE HASHING ====================
            # Şifreyi bcrypt ile hash'le
            hashed_password = hash_password(user_data.password)
            logger.debug(f"Password hashed successfully for email: {user_data.email}")
            
            
            # ==================== ADIM 3: DOKÜMENT OLUŞTUR ====================
            import random
            verification_code = str(random.randint(100000, 999999))
            expires_at = datetime.utcnow() + timedelta(minutes=10)

            # MongoDB'ye kaydedilecek doküment
            user_document = {
                "full_name": user_data.full_name.strip(),
                "email": user_data.email.lower(),  # Email'i lowercase saklıyoruz
                "hashed_password": hashed_password,
                "phone": user_data.phone if user_data.phone else None,
                "is_active": True,  # Varsayılan olarak aktif
                "is_admin": False,  # Varsayılan olarak admin değil
                "is_verified": False,
                "verification_code": verification_code,
                "verification_code_expires_at": expires_at,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
            
            
            # ==================== ADIM 4: DATABASE'YE KAYDET ====================
            # insert_one MongoDB'ye doküment ekler
            result = await self.users_collection.insert_one(user_document)
            inserted_id = result.inserted_id
            
            logger.info(f"User registered successfully. User ID: {inserted_id}, Email: {user_data.email}")
            
            
            # ==================== ADIM 5: RESPONSE DÖNDÜR ====================
            # Kaydedilen dokümentten response oluştur
            # (şifre hariç, dönecek olan UserResponse şemasına uygun)
            response_data = {
                "id": str(inserted_id),
                "full_name": user_document["full_name"],
                "email": user_document["email"],
                "phone": user_document["phone"],
                "is_active": user_document["is_active"],
                "is_admin": user_document["is_admin"],
                "is_verified": user_document["is_verified"],
                "created_at": user_document["created_at"],
                "updated_at": user_document["updated_at"],
            }
            
            # Send Email Asynchronously
            EmailService.send_verification_email(user_document["email"], verification_code)

            return UserResponse(**response_data)
        
        
        except DuplicateDocumentException:
            # Email zaten kayıtlı - bu hata endpoint'de 409 olarak dönecek
            raise
        
        except DatabaseConnectionException:
            # MongoDB bağlantısı hatası
            logger.error(f"Database connection error during registration for email: {user_data.email}")
            raise
        
        except Exception as e:
            # Beklenmeyen hatalar
            logger.error(f"Unexpected error during registration for email: {user_data.email}. Error: {str(e)}")
            raise
    
    async def _register_firebase(self, user_data: UserCreate) -> UserResponse:
        """Firebase ile kayıt."""
        user_dict = await self._firebase_svc.create_user(
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name,
            phone=user_data.phone,
        )
        verification_code = str(random.randint(100000, 999999))
        expires_at = datetime.utcnow() + timedelta(minutes=10)
        await self._firebase_svc.update_user(
            user_dict["id"],
            is_verified=False,
            verification_code=verification_code,
            verification_code_expires_at=expires_at,
        )
        EmailService.send_verification_email(user_dict["email"], verification_code)
        return UserResponse(**user_dict)
    
    async def _login_firebase(self, user_data: UserLogin) -> TokenResponse:
        """Firebase ile giriş."""
        result = await self._firebase_svc.sign_in(user_data.email, user_data.password)
        user_dict = result["user"]
        uid = result["uid"]
        is_admin = bool(user_dict.get("is_admin") or is_config_admin_email(user_dict.get("email")))
        user_dict["is_admin"] = is_admin
        if not user_dict.get("is_verified", False) and not is_admin:
            raise UnverifiedEmailException()
        
        token_data = {
            "sub": uid,
            "email": user_dict["email"],
            "type": "access",
            "scope": "admin" if is_admin else "user",
        }
        access_token = create_access_token(token_data)
        expires_in = 30 * 60
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=expires_in,
            user=UserResponse(**user_dict),
        )
    
    async def login(self, user_data: UserLogin) -> TokenResponse:
        """
        Kullanıcı girişi (login)
        
        Adımlar:
        1. Email ile kullanıcıyı bul
        2. Kullanıcı bulunamazsa InvalidCredentialsException fırlat
        3. Şifreyi doğrula
        4. Şifre yanlışsa InvalidCredentialsException fırlat
        5. JWT access token oluştur
        6. Token+user info ile TokenResponse döndür
        
        Args:
            user_data (UserLogin): Login istek şeması
                {
                    "email": "john@example.com",
                    "password": "SecurePass123"
                }
        
        Returns:
            TokenResponse: Bearer token + kullanıcı bilgileri
                {
                    "access_token": "eyJhbGc...",
                    "token_type": "bearer",
                    "expires_in": 1800,
                    "user": {...}
                }
        
        Raises:
            InvalidCredentialsException: Email bulunamadı veya şifre yanlış (HTTP 401)
            DatabaseConnectionException: MongoDB bağlantısı hatası (HTTP 503)
            Exception: Beklenmeyen hatalar
        
        Örnek Kullanım:
        ---------------
        try:
            token_response = await auth_service.login(UserLogin(
                email="john@example.com",
                password="SecurePass123"
            ))
            # Başarılı giriş
            print(token_response.access_token)  # JWT token
        
        except InvalidCredentialsException:
            # Email bulunamadı veya şifre yanlış
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid email or password"}
            )
        
        except DatabaseConnectionException:
            # Database bağlantısı hatası
            return JSONResponse(
                status_code=503,
                content={"detail": "Database connection error"}
            )
        """
        
        logger.info(f"User login attempt for email: {user_data.email}")
        
        # ==================== FIREBASE BACKEND ====================
        if self._firebase_auth_mode and self._firebase_svc:
            return await self._login_firebase(user_data)
        
        try:
            # ==================== MONGODB BACKEND ====================
            # ==================== ADIM 1: KULLANICIYI BULA ====================
            # Email ile kullanıcıyı bul
            query = User.get_user_by_email_query(user_data.email)
            user_doc = await self.users_collection.find_one(query)
            
            if not user_doc:
                logger.warning(f"Login failed: User not found for email: {user_data.email}")
                raise InvalidCredentialsException()
            
            is_admin = bool(user_doc.get("is_admin") or is_config_admin_email(user_doc.get("email")))
            if not user_doc.get("is_verified", False) and not is_admin:
                logger.warning(f"Login failed: Email not verified: {user_data.email}")
                raise UnverifiedEmailException()
            
            
            # ==================== ADIM 2: ŞİFRE DOĞRULA ====================
            # Şifreyi verify et (bcrypt constant-time comparison)
            hashed_password = user_doc.get("hashed_password", "")
            is_password_valid = verify_password(user_data.password, hashed_password)
            
            if not is_password_valid:
                logger.warning(f"Login failed: Invalid password for email: {user_data.email}")
                raise InvalidCredentialsException()
            
            
            # ==================== ADIM 3: TOKEN OLUŞTUR ====================
            # JWT access token oluştur
            token_data = {
                "sub": str(user_doc["_id"]),  # Token'da user_id sakla
                "email": user_doc["email"],
                "type": "access",
                "scope": "admin" if is_admin else "user"
            }
            access_token = create_access_token(token_data)
            logger.debug(f"Access token created for user: {user_data.email}")
            
            
            # ==================== ADIM 4: RESPONSE OLUŞTUR ====================
            # TokenResponse şemasına uygun response
            expires_in = 30 * 60  # 30 dakika (saniye cinsinden)
            
            user_response_data = {
                "id": str(user_doc["_id"]),
                "full_name": user_doc["full_name"],
                "email": user_doc["email"],
                "phone": user_doc.get("phone"),
                "is_active": user_doc["is_active"],
                "is_admin": is_admin,
                "is_verified": user_doc.get("is_verified", False),
                "created_at": user_doc["created_at"],
                "updated_at": user_doc["updated_at"],
            }
            user_response = UserResponse(**user_response_data)
            
            token_response = TokenResponse(
                access_token=access_token,
                token_type="bearer",
                expires_in=expires_in,
                user=user_response
            )
            
            logger.info(f"User logged in successfully. Email: {user_data.email}, User ID: {user_doc['_id']}")
            
            return token_response
        
        
        except InvalidCredentialsException:
            # Email bulunamadı veya şifre yanlış
            raise
        
        except UnverifiedEmailException:
            # Email onaylı değil
            raise
        
        except DatabaseConnectionException:
            # MongoDB bağlantısı hatası
            logger.error(f"Database connection error during login for email: {user_data.email}")
            raise
        
        except Exception as e:
            # Beklenmeyen hatalar
            logger.error(f"Unexpected error during login for email: {user_data.email}. Error: {str(e)}")
            raise

    async def verify_email(self, email: str, code: str) -> TokenResponse:
        """
        Verify email with 6-digit OTP code and return token on success.
        """
        if self._firebase_auth_mode and self._firebase_svc:
            user_doc = await self._firebase_svc.get_user_by_email(email)
            if not user_doc:
                raise InvalidCredentialsException("Kullanıcı bulunamadı")

            if user_doc.get("is_verified"):
                token_data = {
                    "sub": str(user_doc["id"]),
                    "email": user_doc["email"],
                    "type": "access",
                    "scope": "admin" if user_doc.get("is_admin") else "user",
                }
                access_token = create_access_token(token_data)
                return TokenResponse(
                    access_token=access_token,
                    token_type="bearer",
                    expires_in=30 * 60,
                    user=UserResponse(**user_doc),
                )

            if str(user_doc.get("verification_code") or "") != str(code):
                raise InvalidCredentialsException("Geçersiz doğrulama kodu")

            expires_raw = user_doc.get("verification_code_expires_at")
            expires_at = None
            if isinstance(expires_raw, datetime):
                expires_at = expires_raw
            elif isinstance(expires_raw, str):
                try:
                    expires_at = datetime.fromisoformat(expires_raw.replace("Z", "+00:00"))
                except Exception:
                    expires_at = None
            if not expires_at or datetime.utcnow() > expires_at.replace(tzinfo=None):
                raise InvalidCredentialsException("Doğrulama kodunun süresi dolmuş")

            updated = await self._firebase_svc.update_user(
                str(user_doc["id"]),
                is_verified=True,
                verification_code=None,
                verification_code_expires_at=None,
            )
            token_data = {
                "sub": str(user_doc["id"]),
                "email": user_doc["email"],
                "type": "access",
                "scope": "admin" if user_doc.get("is_admin") else "user",
            }
            access_token = create_access_token(token_data)
            return TokenResponse(
                access_token=access_token,
                token_type="bearer",
                expires_in=30 * 60,
                user=UserResponse(**(updated or user_doc)),
            )

        query = User.get_user_by_email_query(email)
        user_doc = await self.users_collection.find_one(query)
        
        if not user_doc:
            raise InvalidCredentialsException("Kullanıcı bulunamadı")
        
        if user_doc.get("is_verified"):
            # Already verified, just log them in
            token_data = {
                "sub": str(user_doc["_id"]),
                "email": user_doc["email"],
                "type": "access",
                "scope": "admin" if user_doc.get("is_admin") else "user"
            }
            access_token = create_access_token(token_data)
            
            user_response_data = {
                "id": str(user_doc["_id"]),
                "full_name": user_doc["full_name"],
                "email": user_doc["email"],
                "phone": user_doc.get("phone"),
                "is_active": user_doc["is_active"],
                "is_admin": user_doc["is_admin"],
                "is_verified": True,
                "created_at": user_doc["created_at"],
                "updated_at": user_doc["updated_at"],
            }
            return TokenResponse(
                access_token=access_token,
                token_type="bearer",
                expires_in=30 * 60,
                user=UserResponse(**user_response_data)
            )

        # Check code
        if user_doc.get("verification_code") != code:
            raise InvalidCredentialsException("Geçersiz doğrulama kodu")
        
        # Check expiry
        expires_at = user_doc.get("verification_code_expires_at")
        if not expires_at or datetime.utcnow() > expires_at:
            raise InvalidCredentialsException("Doğrulama kodunun süresi dolmuş")
        
        # Update user
        await self.users_collection.update_one(
            {"_id": user_doc["_id"]},
            {"$set": {
                "is_verified": True,
                "verification_code": None,
                "verification_code_expires_at": None,
                "updated_at": datetime.utcnow()
            }}
        )
        
        # Return login token
        token_data = {
            "sub": str(user_doc["_id"]),
            "email": user_doc["email"],
            "type": "access",
            "scope": "admin" if user_doc.get("is_admin") else "user"
        }
        access_token = create_access_token(token_data)
        
        user_response_data = {
            "id": str(user_doc["_id"]),
            "full_name": user_doc["full_name"],
            "email": user_doc["email"],
            "phone": user_doc.get("phone"),
            "is_active": user_doc["is_active"],
            "is_admin": user_doc["is_admin"],
            "is_verified": True,
            "created_at": user_doc["created_at"],
            "updated_at": datetime.utcnow(),
        }
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=30 * 60,
            user=UserResponse(**user_response_data)
        )

    async def login_with_firebase_id_token(self, id_token: str) -> TokenResponse:
        """
        Firebase Google OAuth ile gelen ID token'ı doğrula ve CookWise access token üret.
        """
        try:
            from firebase_admin import auth as firebase_auth
        except Exception as exc:
            logger.error(f"Firebase Admin import hatasi: {exc}")
            raise InvalidCredentialsException("Firebase service is not available")

        from app.core.firebase import get_firebase_app, init_firebase
        from app.core.config import settings
        
        if get_firebase_app() is None:
            if not init_firebase(settings.FIREBASE_CREDENTIALS_PATH, settings.FIREBASE_PROJECT_ID):
                raise InvalidCredentialsException("Firebase baslatilamadi")

        try:
            decoded = firebase_auth.verify_id_token(id_token)
            uid = decoded.get("uid")
            email = decoded.get("email")
            if not uid or not email:
                raise InvalidCredentialsException("Invalid Firebase token payload")

            # Bazı durumlarda service DB'siz oluşturulmuş olabilir; koleksiyonu güvenli şekilde yeniden al.
            if self.users_collection is None:
                db = self.db or Database.get_database()
                if db is None:
                    raise DatabaseConnectionException(
                        operation="firebase_login",
                        message="MongoDB baglantisi bulunamadi"
                    )
                self.db = db
                self.users_collection = db["users"]

            full_name = decoded.get("name") or email.split("@")[0]
            phone = decoded.get("phone_number")

            # MongoDB'de kullanıcıyı bul veya oluştur
            query = User.get_user_by_email_query(email)
            user_doc = await self.users_collection.find_one(query)

            if not user_doc:
                new_user = {
                    "email": email.lower(),
                    "full_name": full_name,
                    "hashed_password": "", # OAuth user
                    "phone": phone,
                    "is_active": True,
                    "is_admin": False,
                    "is_verified": True, # Google email is considered verified
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
                result = await self.users_collection.insert_one(new_user)
                user_doc = await self.users_collection.find_one({"_id": result.inserted_id})
            elif not user_doc.get("is_verified"):
                # Mark as verified since they logged in with Google
                await self.users_collection.update_one(
                    {"_id": user_doc["_id"]},
                    {"$set": {"is_verified": True, "updated_at": datetime.utcnow()}}
                )
                user_doc["is_verified"] = True

            token_data = {
                "sub": str(user_doc["_id"]),
                "email": user_doc["email"],
                "type": "access",
                "scope": "admin" if user_doc.get("is_admin") else "user",
            }
            access_token = create_access_token(token_data)
            
            user_response_data = {
                "id": str(user_doc["_id"]),
                "full_name": user_doc["full_name"],
                "email": user_doc["email"],
                "phone": user_doc.get("phone"),
                "is_active": user_doc.get("is_active", True),
                "is_admin": user_doc.get("is_admin", False),
                "is_verified": user_doc.get("is_verified", True),
                "created_at": user_doc.get("created_at", datetime.utcnow()),
                "updated_at": user_doc.get("updated_at", datetime.utcnow()),
            }

            return TokenResponse(
                access_token=access_token,
                token_type="bearer",
                expires_in=30 * 60,
                user=UserResponse(**user_response_data),
            )
        except DatabaseConnectionException:
            raise
        except InvalidCredentialsException:
            raise
        except Exception as exc:
            logger.warning(f"Firebase OAuth login basarisiz: {exc}")
            raise InvalidCredentialsException(f"Firebase Hata Detayı: {str(exc)}")


# ==================== SINGLETON PATERN ÖRNEK ====================
# Service'i router'da kullanırken:
#
# from fastapi import APIRouter, Depends
# from app.core.database import get_db
# from app.services.auth_service import AuthService
#
# router = APIRouter()
#
# async def get_auth_service(db = Depends(get_db)) -> AuthService:
#     """Dependency injection ile AuthService'i sağla"""
#     return AuthService(db)
#
# @router.post("/register")
# async def register(
#     user_data: UserCreate,
#     auth_service = Depends(get_auth_service)
# ):
#     return await auth_service.register(user_data)
