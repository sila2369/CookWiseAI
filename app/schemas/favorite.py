"""
Favorite Schemas - Pydantic Request/Response Models
====================================================
"""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class FavoriteItemSchema(BaseModel):
    """Favoriler listesinde gösterilecek ürün detayı."""
    id: str
    name: str
    price: float
    image_url: Optional[str] = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class FavoriteResponse(BaseModel):
    """Kullanıcının favori listesinin tam yanıtı."""
    user_id: str
    items: List[FavoriteItemSchema]
    total_count: int

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "user_id": "507f1f77bcf86cd799439011",
                "items": [
                    {
                        "id": "674a1b2c3d4e5f6a7b8c9d0e",
                        "name": "Fıstık Ezmesi",
                        "price": 45.90,
                        "image_url": "https://example.com/fistik.jpg",
                        "is_active": True
                    }
                ],
                "total_count": 1
            }
        }
    )
