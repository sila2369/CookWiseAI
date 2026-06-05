"""
Security Layer - Authentication & Password Management
=======================================================

Güvenlik katmanı:
- Password hashing (bcrypt ile)
- JWT token yönetimi
- Token validation ve payload extraction

Teknolojiler:
- passlib[bcrypt]: Güvenli password hashing
- python-jose: JWT token handling

Config'ten alınan:
- SECRET_KEY: JWT imzalamak için (settings.py'de 32+ karakter)
- ALGORITHM: JWT algoritması (default: HS256)
- ACCESS_TOKEN_EXPIRE_MINUTES: Token geçerlilik süresi (default: 30)

Kullanım örneği:
    # Register'da
    hashed_pwd = hash_password(user.password)
    
    # Login'de
    token = create_access_token({"sub": user_id})
    
    # Route protection'da
    payload = verify_token(token)
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status

from .config import settings

logger = logging.getLogger(__name__)


# ==================== PASSWORD HASHING CONFIGURATION ====================

# Bcrypt context - password hashing ayarları
pwd_context = CryptContext(
    schemes=["bcrypt"],  # Bcrypt algoritması (en güvenli)
    deprecated="auto",   # Eski algoritmalar otomatik upgrade edilir
    bcrypt__rounds=12    # İşleme süresi (12-13 önerilen, daha yüksek = daha güvenli ama yavaş)
)

logger.info("✓ Password hashing context initialized (bcrypt)")


# ==================== PASSWORD HASHING FUNCTIONS ====================

def hash_password(password: str) -> str:
    """
    Şifreyi bcrypt ile hash'le
    
    ⚠️ ASLA plain password kaydet! Bu fonksiyon DAIMA kullan.
    
    Hash özellikleri:
    - One-way (geri döndürülemez)
    - Slow (brute-force attack'e karşı)
    - Salt included (rainbow table'a karşı)
    - Deterministic (aynı password = different hash)
    
    Parametreler:
        password (str): Plain text şifre
    
    Döndürür:
        str: Bcrypt hash (60 karakter, $2b$ prefix)
    
    Örnek:
        password = "SecurePass123"
        hashed = hash_password(password)
        # $2b$12$R9h/cIPz0gi.URNNXZA2IOUS3xfVrnBXqVlVUwjVb5Sw4wCqd5UKe
    
    Raises:
        ValueError: Şifre encoding hatası (nadiren)
    """
    try:
        return pwd_context.hash(password)
    except Exception as e:
        logger.error(f"Password hashing error: {e}")
        raise ValueError("Failed to hash password")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Plain şifre ile hash'i karşılaştır
    
    BENZERLİK ALGORITMASINA DAYANIYOR!
    - Hızlı değil (brute-force'a karşı)
    - İki kez aynı plain password iki farklı hash oluşturur
    
    Parametreler:
        plain_password (str): Kullanıcı tarafından girilen şifre
        hashed_password (str): Veritabanında saklanan hash
    
    Döndürür:
        bool: Şifreler eşleşiyorsa True
    
    Örnek:
        stored_hash = "$2b$12$R9h/cIPz0gi.URNNXZA2IOUS3xfVrnBXqVlVUwjVb5Sw4wCqd5UKe"
        is_valid = verify_password("SecurePass123", stored_hash)
        # True
        
        is_valid = verify_password("WrongPassword", stored_hash)
        # False
    
    Not:
        - Timing attack'e karşı safe (constant-time comparison)
        - logging credentials'ı log etme!
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        # Hashing error değil, sadece match yok
        logger.debug(f"Password verification error: {type(e).__name__}")
        return False


def validate_password_strength(password: str) -> tuple[bool, Optional[str]]:
    """
    Şifre gücünü kontrol et (opsiyonel validator)
    
    Kontrollüyor:
    - Minimum 8 karakter
    - En az 1 büyük harf (A-Z)
    - En az 1 rakam (0-9)
    - En az 1 özel karakter (recommended)
    
    Parametreler:
        password (str): Denetlenecek şifre
    
    Döndürür:
        tuple[bool, Optional[str]]:
        - (True, None) → Güçlü şifre
        - (False, "reason") → Zayıf şifre ve neden
    
    Örnek:
        is_valid, reason = validate_password_strength("12345678")
        # (False, "Must contain uppercase letter")
        
        is_valid, reason = validate_password_strength("SecurePass123")
        # (True, None)
    
    Not:
        Schema validation'da Pydantic kullanılıyor.
        Bu fonksiyon opsiyonel extra check için.
    """
    from string import ascii_uppercase, digits, punctuation
    
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    
    if not any(c in ascii_uppercase for c in password):
        return False, "Must contain at least one uppercase letter"
    
    if not any(c in digits for c in password):
        return False, "Must contain at least one digit"
    
    # Special character optional but recommended
    if not any(c in punctuation for c in password):
        logger.debug("Password without special character (not required)")
    
    return True, None


# ==================== JWT TOKEN FUNCTIONS ====================

class TokenConstants:
    """JWT token claim constants"""
    SUBJECT = "sub"          # Subject (user_id)
    EXPIRATION = "exp"       # Expiration time (unix timestamp)
    ISSUED_AT = "iat"        # Issued at time
    NOT_BEFORE = "nbf"       # Not valid before
    TOKEN_TYPE = "type"      # Token type (access/refresh)
    SCOPE = "scope"          # Permissions scope


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    JWT Access Token oluştur
    
    Token'a exp (expiration) ve iat (issued-at) claim'leri otomatik eklenir.
    
    Parametreler:
        data (Dict[str, Any]): Token'a eklenecek veriler
            Örnek: {"sub": "507f1f77bcf86cd799439011", "email": "user@example.com"}
            
        expires_delta (Optional[timedelta]): Geçerlilik süresi
            - None: config'den alınır (30 dakika default)
            - timedelta(hours=24): 24 saatlik token
    
    Döndürür:
        str: Encoded JWT token (useable in Authorization header)
    
    Örnek:
        # Login'de
        token = create_access_token(
            data={"sub": str(user_id)},
            expires_delta=timedelta(hours=24)
        )
        # "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1MDdmMWY3NyIsImV4cCI6MTcxODA3NDAwMH0..."
    
    HTTP Header'da:
        headers = {"Authorization": f"Bearer {token}"}
    
    Token decode (verify_token'da):
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload["sub"]
    
    İç yapı (decoded):
        {
            "sub": "507f1f77bcf86cd799439011",      # User ID
            "email": "user@example.com",             # User email
            "exp": 1640995200000,                    # Expiration (unix timestamp)
            "iat": 1640991600000,                    # Issued at (создан zamanı)
        }
    
    Security Notes:
        - Token stateless (server'da saklanmaz)
        - Browser'da store edilmemeli (XSS vulnerability)
        - HTTPS kullan (token sniffing'e karşı)
        - Token'ı HTTP-only cookie'ye koy (XSS protection)
    """
    # Token payload'ının bir kopyası (orijinalini değiştirme)
    to_encode = data.copy()
    
    # Expiration time hesapla
    if expires_delta:
        # Custom expiration süresi
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # Config'den alınan default süre (dakika)
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    # Token'a exp ve iat claim'lerini ekle
    to_encode.update({
        "exp": expire,                           # Expiration time (datetime → unix timestamp'a otomatik dönüştürülür)
        "iat": datetime.now(timezone.utc),       # Issued at (şu anki zaman)
    })
    
    # Token'u encode et (hash'le ve sign'la)
    try:
        encoded_jwt = jwt.encode(
            to_encode,
            settings.SECRET_KEY,  # ⚠️ 32+ karakter olmalı (config'de kontrol edilir)
            algorithm=settings.ALGORITHM  # HS256 (HMAC SHA256)
        )
        
        logger.debug(f"Token created for: {data.get('sub', 'unknown')}")
        return encoded_jwt
        
    except Exception as e:
        logger.error(f"Token creation error: {e}")
        raise RuntimeError("Failed to create access token")


def create_refresh_token(
    user_id: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Refresh Token oluştur (optional - uzun süreli token)
    
    Access token'ı refresh etmek için.
    Typically:
    - Access token: 15-30 dakika
    - Refresh token: 7-30 gün
    
    Parametreler:
        user_id (str): Kullanıcı ID'si
        expires_delta (Optional[timedelta]): Geçerlilik süresi (default: 7 gün)
    
    Döndürür:
        str: Encoded refresh token
    
    Örnek:
        refresh_token = create_refresh_token(
            user_id=str(user_id),
            expires_delta=timedelta(days=7)
        )
    """
    if expires_delta is None:
        expires_delta = timedelta(days=7)  # Default: 7 gün
    
    return create_access_token(
        data={"sub": user_id, "type": "refresh"},
        expires_delta=expires_delta
    )


# ==================== TOKEN VALIDATION FUNCTIONS ====================

def verify_token(token: str) -> Dict[str, Any]:
    """
    JWT Token'ı doğrula ve payload'ı döndür
    
    Steps:
    1. Token imzasını kontrol et (SECRET_KEY ile)
    2. Token'ın süresi dolmadığını kontrol et
    3. Payload'ı decode et ve döndür
    
    Parametreler:
        token (str): JWT token (Authorization header'dan gelir)
            Örnek: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    
    Döndürür:
        Dict[str, Any]: Decoded payload
            Örnek: {"sub": "507f1f77bcf86cd799439011", "exp": 1640995200}
    
    Raises:
        HTTPException:
        - 401: Token geçersiz veya süresi dolmuş
    
    Örnek (route'da):
        @router.get("/me")
        async def get_me(
            authorization: str = Header(None)
        ):
            try:
                token = authorization.replace("Bearer ", "")
                payload = verify_token(token)
                user_id = payload["sub"]
            except HTTPException as e:
                return JSONResponse(
                    status_code=e.status_code,
                    content={"detail": e.detail}
                )
    
    Exception Types:
    - ExpiredSignatureError: exp claim'i geçmiş zaman
    - JWTError: Geçersiz imza, malformed token
    
    Security Notes:
    - Token'ı decode etmek = imzayı kontrol etmek
    - Sadece trusted tokens accept et
    - Header'daki "alg" alanını override etme
    """
    try:
        # Token'ı decode et
        payload = jwt.decode(
            token,                              # Encoded token
            settings.SECRET_KEY,                # İmza kontrol için secret
            algorithms=[settings.ALGORITHM]     # Sadece HS256 accept et (algorithm confusion attack'e karşı)
        )
        
        # sub (user_id) claim'ı var mı?
        user_id = payload.get("sub")
        if not user_id:
            logger.warning("Token missing 'sub' claim")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user_id"
            )
        
        logger.debug(f"Token verified for user: {user_id}")
        return payload
        
    except jwt.ExpiredSignatureError:
        # Token'ın geçerlilik süresi dolmuş
        logger.warning("Token expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please login again."
        )
    
    except JWTError as e:
        # Token geçersiz (imza hatası, malformed, vb.)
        logger.warning(f"Invalid token: {type(e).__name__}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token. Could not validate credentials."
        )
    
    except Exception as e:
        # Unexpected error
        logger.error(f"Token verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to verify token"
        )


def get_user_id_from_token(token: str) -> str:
    """
    Token'dan user_id'yi çıkar
    
    Parametreler:
        token (str): JWT token
    
    Döndürür:
        str: User ID (MongoDB ObjectId as string)
    
    Raises:
        HTTPException: Token geçersiz/süresi dolmuş
    
    Örnek:
        user_id = get_user_id_from_token(token)
    """
    payload = verify_token(token)
    return payload.get("sub")


# ==================== HELPER FUNCTIONS ====================

def decode_token_without_verification(token: str) -> Optional[Dict[str, Any]]:
    """
    ⚠️ Token'ı doğrulamadan decode et (debugging için sadece!)
    
    ÜRETIM'DE KULLANMA!
    
    Parametreler:
        token (str): JWT token
    
    Döndürür:
        Dict: Decoded payload (doğrulanmaz)
    
    Not:
        - İmza kontrol edilmez
        - Süresi dolmuş token'lar da okunur
        - Debugging/logging için sadece
    """
    try:
        # options={"verify_signature": False} = imzayı kontrol et
        payload = jwt.decode(
            token,
            options={"verify_signature": False}
        )
        return payload
    except:
        return None
