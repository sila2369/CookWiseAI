"""
Address Schemas - Pydantic Request/Response Models
===================================================
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


# ==================== REQUEST ====================

class AddressCreate(BaseModel):
    """Yeni adres oluşturma isteği."""
    title: str = Field(..., min_length=2, max_length=50, description="Adres başlığı (Örn: Ev, İş)")
    city: str = Field(..., min_length=2, max_length=50, description="Şehir")
    district: str = Field(..., min_length=2, max_length=50, description="İlçe")
    full_address: str = Field(..., min_length=10, max_length=500, description="Açık adres")
    is_default: bool = Field(False, description="Varsayılan adres yapılsın mı?")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Ev",
                "city": "İstanbul",
                "district": "Kadıköy",
                "full_address": "Örnek Mah. 123 Sok. No:4 D:5",
                "is_default": True
            }
        }
    )


class AddressUpdate(BaseModel):
    """Mevcut adresi güncelleme isteği (tüm alanlar opsiyonel)."""
    title: Optional[str] = Field(None, min_length=2, max_length=50)
    city: Optional[str] = Field(None, min_length=2, max_length=50)
    district: Optional[str] = Field(None, min_length=2, max_length=50)
    full_address: Optional[str] = Field(None, min_length=10, max_length=500)
    is_default: Optional[bool] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "full_address": "Örnek Mah. 123 Sok. No:4 D:6",
                "is_default": True
            }
        }
    )


# ==================== RESPONSE ====================

class AddressResponse(BaseModel):
    """Adres API response modeli."""
    id: str
    user_id: str
    title: str
    city: str
    district: str
    full_address: str
    is_default: bool
    created_at: datetime | str
    updated_at: datetime | str

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "674a1b2c3d4e5f6a7b8c9d0f",
                "user_id": "507f1f77bcf86cd799439011",
                "title": "Ev",
                "city": "İstanbul",
                "district": "Kadıköy",
                "full_address": "Örnek Mah. 123 Sok. No:4 D:5",
                "is_default": True,
                "created_at": "2026-03-20T12:00:00",
                "updated_at": "2026-03-20T12:00:00"
            }
        }
    )


class AddressListResponse(BaseModel):
    """Kullanıcının adres listesi yanıtı."""
    items: List[AddressResponse]
    total: int
