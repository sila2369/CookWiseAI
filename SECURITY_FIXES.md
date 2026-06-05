# 🔒 Güvenlik Düzeltmeleri - Security Fixes

Bu dosya CookWise projesinde tespit edilen güvenlik sorunlarının ve çözümlerinin listesidir.

## Kritik Güvenlik Sorunları

### 1. Docker Compose - SECRET_KEY Default Fallback

**Durum**: FIXED ✅
**Orijinal Kod**:
```yaml
# docker-compose.yml ❌ GÜVENSİZ
environment:
  SECRET_KEY: ${SECRET_KEY:-default-secret-key-change-in-production}
```

**Problem**: SECRET_KEY environment değişkeni tanımlanmazsa zayıf default key kullanılır

**Düzeltilmiş Kod**:
```yaml
# docker-compose.yml ✅ GÜVENLİ
environment:
  SECRET_KEY: ${SECRET_KEY}  # Required - error if not set
```

**Ek Adım**: CI/CD pipelinede check ekle
```bash
if [ -z "$SECRET_KEY" ]; then
    echo "ERROR: SECRET_KEY not set"
    exit 1
fi
```

---

### 2. CORS Wildcard Policy

**Durum**: FIXED ✅
**Orijinal Kod**:
```env
# .env.example ❌ (Development'ta okay, Production'ta HAYIR)
CORS_ORIGINS=["*"]
```

**Düzeltilmiş Yapılandırma**:

```python
# app/core/config.py
from typing import List

CORS_ORIGINS_BY_ENV = {
    "development": ["http://localhost:3000", "http://localhost:3001"],
    "staging": ["https://staging.example.com"],
    "production": ["https://app.example.com"],  # Only specific origin
}

class Settings(BaseSettings):
    APP_ENV: str = "development"
    
    @property
    def CORS_ORIGINS(self) -> List[str]:
        """Environment-based CORS origins"""
        return CORS_ORIGINS_BY_ENV.get(self.APP_ENV, ["localhost"])
    
    @property  
    def CORS_ALLOW_CREDENTIALS(self) -> bool:
        """Disable credentials in production"""
        return self.APP_ENV != "production"
```

**Updated .env.example**:
```env
# CORS_ORIGINS otomatik olarak APP_ENV'e göre ayarlanacak
# Development: http://localhost:3000
# Staging: https://staging.example.com
# Production: https://app.example.com

# Production için manuel override (isteğe bağlı)
# CORS_ORIGINS=["https://app.example.com"]
```

---

### 3. Şifre Doğrulama Eksikliği

**Durum**: FIXED ✅
**Orijinal Kod**:
```python
# app/schemas/user_schema.py ❌
class UserCreate(BaseModel):
    email: EmailStr
    password: str  # Validation yok!
```

**Düzeltilmiş Kod**:
```python
# app/schemas/user_schema.py ✅
from pydantic import BaseModel, EmailStr, field_validator, ConfigDict

class PasswordStrengthValidator:
    """Password strength validation rules"""
    MIN_LENGTH = 8
    REQUIRE_UPPERCASE = True
    REQUIRE_DIGIT = True
    REQUIRE_SPECIAL = False

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "password": "SecurePass123",  # Min 8, uppercase, digit
                "full_name": "John Doe"
            }
        }
    )
    
    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """
        Şifre gücünü doğrula
        - Minimum 8 karakter
        - En az 1 büyük harf
        - En az 1 rakam
        - En az 1 özel karakter (opsiyonel)
        """
        from string import ascii_uppercase, digits
        
        if len(v) < PasswordStrengthValidator.MIN_LENGTH:
            raise ValueError(
                f'Password must be at least {PasswordStrengthValidator.MIN_LENGTH} characters'
            )
        
        if PasswordStrengthValidator.REQUIRE_UPPERCASE and not any(c in ascii_uppercase for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        
        if PasswordStrengthValidator.REQUIRE_DIGIT and not any(c in digits for c in v):
            raise ValueError('Password must contain at least one digit')
        
        # Common weak passwords check
        weak_passwords = ["password", "123456", "qwerty"]
        if v.lower() in weak_passwords:
            raise ValueError('Password is too common. Choose a stronger password')
        
        return v

    @field_validator('email')
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        """Onay için email normalize et"""
        return v.lower().strip()
```

---

### 4. Eksik Rate Limiting

**Durum**: NOT FIXED ⚠️ (Eklenecek)
**Çözüm**:

```bash
pip install slowapi
```

```python
# app/core/rate_limit.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# Limitle:
# - Login: 5 attempts / 15 minutes
# - API: 100 requests / minute (authenticated)
# - Public health: 1000 requests / minute
```

```python
# app/main.py
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    return JSONResponse(
        status_code=429,
        content={"error": "Too many requests"}
    )

# Router'larda
@router.post("/login")
@limiter.limit("5/15minutes")
async def login(request: Request, credentials: LoginRequest):
    pass
```

---

## Güvenlik Kontrol Listesi

| Öge | Durum | Dosya |
|-----|-------|-------|
| JWT Secret Key | ✅ FIXED | .env → Required |
| CORS Policy | ✅ FIXED | config.py |
| Password Strength | ✅ FIXED | schemas/user.py |
| Rate Limiting | ⏳ TODO | Main PR |
| API Authentication | ⚠️ WIP | dependencies/auth.py |
| Request Validation | ✅ | Pydantic |
| HTTPS/SSL | ✅ | Production ready |
| MongoDB Auth | ✅ | Atlas/IP Whitelist |
| .env in .gitignore | ✅ | .gitignore |
| Request ID Tracking | ⏳ TODO | Middleware |
| SQL Injection Prevention | ✅ | MongoDB (no SQL) |

---

## Production Dağıtım Kontrol Listesi

Deployment öncesi bunu kontrol et:

```bash
# 1. Environment değişkenleri kontrol
[ -n "$SECRET_KEY" ] || echo "❌ SECRET_KEY not set"
[ "$APP_ENV" = "production" ] || echo "⚠️ APP_ENV not production"
[ "$DEBUG" = "False" ] || echo "⚠️ DEBUG should be False"

# 2. CORS Origins
grep -q "production" app/core/config.py && echo "✅ CORS config ready"

# 3. Password validation
grep -q "validate_password_strength" app/schemas/*.py && echo "✅ Password validation ready"

# 4. Rate limiter
pip show slowapi > /dev/null && echo "✅ Rate limiter installed"

# 5. SSL Certificate
[ -f "$MONGODB_CA_CERT" ] && echo "✅ MongoDB SSL cert present"
```

---

## İlgili Dosyalar

- [.env.example](.env.example) - Environment template
- [docker-compose.yml](docker-compose.yml) - Docker configuration
- [app/core/config.py](app/core/config.py) - Application settings
- [app/core/security.py](app/core/security.py) - Security utilities

---

**Son Güncelleme**: March 2026  
**Güvenlik Seviyesi**: Medium ⚠️ → High ✅ (After fixes)
