"""
Custom Application Exceptions
==============================

Uygulamada kullanılacak custom exception sınıfları.
Bu sayede hataların türünü ayırt edebiliriz ve özel exception handler'lar yazabiliriz.

Örnek:
    from app.core.exceptions import DatabaseException, ValidationException
    
    try:
        user = await db.users.find_one(...)
    except Exception as e:
        raise DatabaseException(f"Failed to fetch user: {str(e)}")
    
    try:
        validate_data(user_input)
    except ValueError:
        raise ValidationException("Invalid user data")
"""

from fastapi import HTTPException, status


class AppException(Exception):
    """Tüm application exception'ların base class'ı"""
    
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


# ==================== DATABASE EXCEPTIONS ====================

class DatabaseException(AppException):
    """Veritabanı operasyonu başarısız"""
    
    def __init__(self, message: str):
        super().__init__(
            message=f"Database error: {message}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class DatabaseConnectionException(DatabaseException):
    """MongoDB'ye bağlanılamadı"""
    
    def __init__(self):
        super().__init__("Could not connect to MongoDB")


class DocumentNotFoundException(DatabaseException):
    """Aranan dokument bulunamadı"""
    
    def __init__(self, collection: str, query: dict):
        super().__init__(f"Document not found in '{collection}' with query: {query}")


class DuplicateDocumentException(AppException):
    """Unique constraint ihlali - dokument zaten var (HTTP 409)"""

    def __init__(self, collection: str, field: str, value: str, message: str = None):
        msg = message or f"Document with {field}='{value}' already exists in '{collection}'"
        super().__init__(message=msg, status_code=status.HTTP_409_CONFLICT)


# ==================== AUTHENTICATION EXCEPTIONS ====================

class AuthenticationException(AppException):
    """Kimlik doğrulama başarısız"""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED
        )


class InvalidCredentialsException(AuthenticationException):
    """Kullanıcı adı/şifre yanlış"""
    
    def __init__(self, message: str = "Invalid username or password"):
        super().__init__(message)


class TokenExpiredException(AuthenticationException):
    """JWT token süresi dolmuş"""
    
    def __init__(self):
        super().__init__("Token has expired")


class InvalidTokenException(AuthenticationException):
    """JWT token geçersiz"""
    
    def __init__(self, reason: str = "Invalid token"):
        super().__init__(reason)


class UserNotAuthenticatedException(AuthenticationException):
    """Kullanıcı oturum açmamış"""
    
    def __init__(self):
        super().__init__("User not authenticated")


class UnverifiedEmailException(AuthenticationException):
    """Email adresi doğrulanmamış"""
    
    def __init__(self, message: str = "Email adresi henüz doğrulanmadı"):
        super().__init__(message)
        self.status_code = status.HTTP_403_FORBIDDEN


# ==================== VALIDATION EXCEPTIONS ====================

class ValidationException(AppException):
    """Input doğrulama başarısız"""
    
    def __init__(self, message: str, field: str = None):
        if field:
            message = f"Validation error in '{field}': {message}"
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )


class PasswordValidationException(ValidationException):
    """Şifre zayıf"""
    
    def __init__(self, reason: str):
        super().__init__(
            message=f"Password validation failed: {reason}",
            field="password"
        )


class EmailValidationException(ValidationException):
    """Email format'ı hatalı"""
    
    def __init__(self):
        super().__init__(
            message="Invalid email format",
            field="email"
        )


# ==================== AUTHORIZATION EXCEPTIONS ====================

class AuthorizationException(AppException):
    """Kullanıcı yeterli izne sahip değil"""
    
    def __init__(self, message: str = "Permission denied"):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN
        )


class InsufficientPermissionsException(AuthorizationException):
    """Kullanıcı bu işlemi yapaması"""
    
    def __init__(self, action: str):
        super().__init__(f"Insufficient permissions to perform '{action}'")


class AdminOnlyException(AuthorizationException):
    """Sadece admin bu işlemi yapabilir"""
    
    def __init__(self):
        super().__init__("This action is restricted to administrators only")


# ==================== BUSINESS LOGIC EXCEPTIONS ====================

class BusinessLogicException(AppException):
    """İş mantığı kuralı ihlali"""
    
    def __init__(self, message: str):
        super().__init__(
            message=f"Business logic error: {message}",
            status_code=status.HTTP_400_BAD_REQUEST
        )


class InsufficientFundsException(BusinessLogicException):
    """Yetersiz bakiye"""
    
    def __init__(self, balance: float, required: float):
        super().__init__(
            f"Insufficient funds: have {balance}, need {required}"
        )


class OutOfStockException(BusinessLogicException):
    """Ürün stokta yok"""
    
    def __init__(self, product_id: str, quantity: int):
        super().__init__(
            f"Product {product_id} is out of stock (requested: {quantity})"
        )


class InvalidOrderStateException(BusinessLogicException):
    """Sipariş durumu değişikliği geçersiz"""
    
    def __init__(self, current_state: str, requested_state: str):
        super().__init__(
            f"Cannot transition from '{current_state}' to '{requested_state}'"
        )


# ==================== EXTERNAL SERVICE EXCEPTIONS ====================

class ExternalServiceException(AppException):
    """Harici servis hatası"""
    
    def __init__(self, service: str, message: str):
        super().__init__(
            message=f"External service error ({service}): {message}",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )


class PaymentServiceException(ExternalServiceException):
    """Ödeme servisi hatası"""
    
    def __init__(self, message: str):
        super().__init__("payment_service", message)


class SMSServiceException(ExternalServiceException):
    """SMS servisi hatası"""
    
    def __init__(self, message: str):
        super().__init__("sms_service", message)


# ==================== UTILITY FUNCTIONS ====================

def get_http_exception_from_app_exception(exc: AppException) -> HTTPException:
    """
    AppException'ı HTTPException'a dönüştür
    
    Kullanım (main.py'de):
        @app.exception_handler(AppException)
        async def app_exception_handler(request, exc):
            http_exc = get_http_exception_from_app_exception(exc)
            return JSONResponse(
                status_code=http_exc.status_code,
                content={"error": http_exc.detail}
            )
    """
    return HTTPException(
        status_code=exc.status_code,
        detail=exc.message
    )
