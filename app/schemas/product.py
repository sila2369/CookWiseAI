"""
Product Schemas - Pydantic Request/Response Models
===================================================

API validation: price >= 0, stock >= 0, slug formatı.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, ConfigDict

import re

# Ortak slug validator (category ile tutarlı)
def _slug_validator(v: str) -> str:
    v = v.strip().lower()
    if not re.match(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$", v):
        raise ValueError("Slug must be lowercase, alphanumeric and hyphens only")
    if len(v) < 2:
        raise ValueError("Slug must be at least 2 characters")
    if len(v) > 120:
        raise ValueError("Slug must be at most 120 characters")
    return v


# ==================== REQUEST ====================


class ProductCreate(BaseModel):
    """Yeni ürün oluşturma isteği."""

    name: str = Field(..., min_length=2, max_length=200)
    slug: Optional[str] = Field(None, min_length=2, max_length=120)
    description: str = Field(..., max_length=2000)
    price: float = Field(..., ge=0, description="Fiyat (>= 0)")
    stock: int = Field(..., ge=0, description="Stok adedi (>= 0)")
    category_id: str = Field(..., min_length=24, max_length=24)
    image_url: Optional[str] = Field(None, max_length=500)
    brand: Optional[str] = Field(None, max_length=100)
    unit: Optional[str] = Field(None, max_length=20)
    is_active: bool = True
    is_promoted: bool = False
    promotion_type: Optional[str] = Field(None, max_length=40)
    promotion_label: Optional[str] = Field(None, max_length=120)
    discounted_price: Optional[float] = Field(None, ge=0)
    promotion_buy_quantity: Optional[int] = Field(None, ge=1)
    promotion_pay_quantity: Optional[int] = Field(None, ge=1)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Süt 1 Litre",
                "slug": "sut-1-litre",
                "description": "Günlük süt, 1 litre",
                "price": 25.99,
                "stock": 100,
                "category_id": "674a1b2c3d4e5f6a7b8c9d0e",
                "image_url": "https://example.com/sut.jpg",
                "brand": "Pınar",
                "unit": "litre",
                "is_active": True,
            }
        }
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        return v.strip() or ""

    @field_validator("category_id")
    @classmethod
    def validate_category_id(cls, v: str) -> str:
        v = v.strip()
        if len(v) != 24 or not all(c in "0123456789abcdefABCDEF" for c in v):
            raise ValueError("category_id must be a valid 24-character hex ObjectId")
        return v.lower()

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return _slug_validator(v)


class ProductUpdate(BaseModel):
    """Ürün güncelleme isteği (tüm alanlar opsiyonel)."""

    name: Optional[str] = Field(None, min_length=2, max_length=200)
    slug: Optional[str] = Field(None, min_length=2, max_length=120)
    description: Optional[str] = Field(None, max_length=2000)
    price: Optional[float] = Field(None, ge=0)
    stock: Optional[int] = Field(None, ge=0)
    category_id: Optional[str] = Field(None, min_length=24, max_length=24)
    image_url: Optional[str] = Field(None, max_length=500)
    brand: Optional[str] = Field(None, max_length=100)
    unit: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = None
    is_promoted: Optional[bool] = None
    promotion_type: Optional[str] = Field(None, max_length=40)
    promotion_label: Optional[str] = Field(None, max_length=120)
    discounted_price: Optional[float] = Field(None, ge=0)
    promotion_buy_quantity: Optional[int] = Field(None, ge=1)
    promotion_pay_quantity: Optional[int] = Field(None, ge=1)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Süt 1 Litre",
                "price": 26.50,
                "stock": 50,
                "is_active": False,
            }
        }
    )

    @field_validator("category_id")
    @classmethod
    def validate_category_id(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if len(v) != 24 or not all(c in "0123456789abcdefABCDEF" for c in v):
            raise ValueError("category_id must be a valid 24-character hex ObjectId")
        return v.lower()

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return _slug_validator(v)


# ==================== RESPONSE ====================


class ProductResponse(BaseModel):
    """Ürün API response (güvenli alanlar)."""

    id: str
    name: str
    slug: str
    description: str
    price: float
    stock: int
    image_url: Optional[str] = None
    category_id: str
    brand: Optional[str] = None
    unit: Optional[str] = None
    is_active: bool
    is_promoted: bool = False
    promotion_type: Optional[str] = None
    promotion_label: Optional[str] = None
    discounted_price: Optional[float] = None
    promotion_buy_quantity: Optional[int] = None
    promotion_pay_quantity: Optional[int] = None
    created_at: datetime | str
    updated_at: datetime | str

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "674a1b2c3d4e5f6a7b8c9d0f",
                "name": "Süt 1 Litre",
                "slug": "sut-1-litre",
                "description": "Günlük süt",
                "price": 25.99,
                "stock": 100,
                "image_url": "https://example.com/sut.jpg",
                "category_id": "674a1b2c3d4e5f6a7b8c9d0e",
                "brand": "Pınar",
                "unit": "litre",
                "is_active": True,
                "created_at": "2026-03-20T12:00:00",
                "updated_at": "2026-03-20T12:00:00",
            }
        }
    )


class ProductListResponse(BaseModel):
    """Sayfalanmış ürün listesi response."""

    items: list[ProductResponse]
    total: int
    skip: int
    limit: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [],
                "total": 0,
                "skip": 0,
                "limit": 20,
            }
        }
    )
