"""
Cart Schemas - Pydantic Request/Response Models
================================================

Sepet işlemleri için request ve response modelleri.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict


# ==================== REQUEST ====================

class CartItemAdd(BaseModel):
    """Sepete yeni ürün ekleme isteği."""
    
    product_id: str = Field(..., min_length=24, max_length=24, description="Eklenecek ürünün ID'si")
    quantity: int = Field(1, ge=1, description="Eklenecek adet (>= 1)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "product_id": "674a1b2c3d4e5f6a7b8c9d0f",
                "quantity": 2
            }
        }
    )

    @field_validator("product_id")
    @classmethod
    def validate_product_id(cls, v: str) -> str:
        v = v.strip()
        if len(v) != 24 or not all(c in "0123456789abcdefABCDEF" for c in v):
            raise ValueError("product_id must be a valid 24-character hex ObjectId")
        return v.lower()


class CartItemUpdate(BaseModel):
    """Sepetteki ürünün miktarını güncelleme isteği."""
    
    quantity: int = Field(..., ge=0, description="Yeni adet (0 ise ürün sepetten silinir)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "quantity": 5
            }
        }
    )


# ==================== RESPONSE ====================

class CartItemResponse(BaseModel):
    """Sepetteki tek bir ürünün detayı (canlı fiyatlı)."""
    
    product_id: str
    name: str
    price: float
    image_url: Optional[str] = None
    quantity: int
    subtotal: float
    original_price: Optional[float] = None
    promotion_label: Optional[str] = None

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "product_id": "674a1b2c3d4e5f6a7b8c9d0f",
                "name": "Süt 1 Litre",
                "price": 25.99,
                "image_url": "https://example.com/sut.jpg",
                "quantity": 2,
                "subtotal": 51.98
            }
        }
    )


class CartResponse(BaseModel):
    """Sepetin tamamının yanıt modeli."""
    
    id: str
    user_id: str
    items: List[CartItemResponse]
    total_price: float
    updated_at: datetime | str

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "674a1b2c3d4e5f6a7b8c9d0e",
                "user_id": "507f1f77bcf86cd799439011",
                "items": [
                    {
                        "product_id": "674a1b2c3d4e5f6a7b8c9d0f",
                        "name": "Süt 1 Litre",
                        "price": 25.99,
                        "image_url": "https://example.com/sut.jpg",
                        "quantity": 2,
                        "subtotal": 51.98
                    }
                ],
                "total_price": 51.98,
                "updated_at": "2026-03-20T12:00:00"
            }
        }
    )
