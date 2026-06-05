"""
Category Schemas - Pydantic Request/Response Models
====================================================

API validation ve Swagger dokümantasyonu.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, ConfigDict

import re


def _slug_validator(v: str) -> str:
    """Slug: sadece lowercase, tire, rakam."""
    v = v.strip().lower()
    if not re.match(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$", v):
        raise ValueError("Slug must be lowercase, alphanumeric and hyphens only (e.g. yemek-icecek)")
    if len(v) < 2:
        raise ValueError("Slug must be at least 2 characters")
    if len(v) > 80:
        raise ValueError("Slug must be at most 80 characters")
    return v


# ==================== REQUEST ====================


class CategoryCreate(BaseModel):
    """Yeni kategori oluşturma isteği."""

    name: str = Field(..., min_length=2, max_length=100)
    slug: Optional[str] = Field(None, min_length=2, max_length=80)
    description: Optional[str] = Field(None, max_length=500)
    image_url: Optional[str] = Field(None, max_length=500)
    is_active: bool = True

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Yemek & İçecek",
                "slug": "yemek-icecek",
                "description": "Restoran ve kafe siparişleri",
                "image_url": "https://example.com/cat.jpg",
                "is_active": True,
            }
        }
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Name must be at least 2 characters")
        return v

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return _slug_validator(v)


class CategoryUpdate(BaseModel):
    """Kategori güncelleme isteği (tüm alanlar opsiyonel)."""

    name: Optional[str] = Field(None, min_length=2, max_length=100)
    slug: Optional[str] = Field(None, min_length=2, max_length=80)
    description: Optional[str] = Field(None, max_length=500)
    image_url: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Yemek & İçecek",
                "description": "Güncellenmiş açıklama",
                "is_active": False,
            }
        }
    )

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return _slug_validator(v)


# ==================== RESPONSE ====================


class CategoryResponse(BaseModel):
    """Kategori API response (güvenli alanlar)."""

    id: str
    name: str
    slug: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    is_active: bool
    created_at: datetime | str
    updated_at: datetime | str

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "674a1b2c3d4e5f6a7b8c9d0e",
                "name": "Yemek & İçecek",
                "slug": "yemek-icecek",
                "description": "Restoran siparişleri",
                "image_url": "https://example.com/cat.jpg",
                "is_active": True,
                "created_at": "2026-03-20T12:00:00",
                "updated_at": "2026-03-20T12:00:00",
            }
        }
    )


class CategoryListResponse(BaseModel):
    """Sayfalanmış kategori listesi response."""

    items: list[CategoryResponse]
    total: int
    skip: int
    limit: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "id": "674a1b2c3d4e5f6a7b8c9d0e",
                        "name": "Yemek & İçecek",
                        "slug": "yemek-icecek",
                        "description": None,
                        "image_url": None,
                        "is_active": True,
                        "created_at": "2026-03-20T12:00:00",
                        "updated_at": "2026-03-20T12:00:00",
                    }
                ],
                "total": 1,
                "skip": 0,
                "limit": 20,
            }
        }
    )
