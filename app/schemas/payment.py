"""
Payment Schemas - Pydantic Request/Response Models
===================================================
"""

from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator


class CreditCardPaymentRequest(BaseModel):
    """Kredi kartı ile ödeme isteği modeli."""
    card_number: str = Field(..., min_length=13, max_length=19, description="Kredi kartı numarası (boşluksuz)")
    holder_name: str = Field(..., min_length=3, max_length=100, description="Kart üzerindeki isim")
    exp_month: int = Field(..., ge=1, le=12, description="Son kullanma ayı (1-12)")
    exp_year: int = Field(..., ge=2024, le=2100, description="Son kullanma yılı (örn: 2026)")
    cvv: str = Field(..., min_length=3, max_length=4, description="Güvenlik kodu (CVV/CVC)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "card_number": "4111111111111111",
                "holder_name": "Sila E.",
                "exp_month": 12,
                "exp_year": 2028,
                "cvv": "123"
            }
        }
    )

    @field_validator("card_number")
    @classmethod
    def validate_card_number(cls, v: str) -> str:
        # Sadece rakamlardan oluştuğunu doğrula
        v = v.replace(" ", "").replace("-", "")
        if not v.isdigit():
            raise ValueError("Card number must contain only digits")
        return v

    @field_validator("cvv")
    @classmethod
    def validate_cvv(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("CVV must contain only digits")
        return v


class PaymentResponse(BaseModel):
    """Ödeme işlemi sonucunu dönen model."""
    success: bool
    transaction_id: str
    message: str
    paid_amount: float
    payment_time: datetime | str

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "success": True,
                "transaction_id": "TXN-987654321",
                "message": "Payment successful",
                "paid_amount": 150.50,
                "payment_time": "2026-05-03T12:00:00"
            }
        }
    )
