"""
Favorite Service - Favori iş mantığı
=====================================
Kullanıcı favorilerine ürün ekleme, çıkarma ve canlı listeleme.
"""

import logging
from datetime import datetime
from bson import ObjectId

from app.models.favorite import Favorite
from app.models.product import Product
from app.schemas.favorite import FavoriteResponse, FavoriteItemSchema

logger = logging.getLogger(__name__)

def _normalize_user_id(user_id: str):
    try:
        return ObjectId(user_id)
    except Exception:
        return user_id


class FavoriteService:
    """Favoriler işlemleri."""

    def __init__(self, db):
        if db is None:
            raise ValueError("Database connection is required")
        self.db = db
        self.favorites = db[Favorite.COLLECTION]
        self.products = db[Product.COLLECTION]

    async def get_favorites(self, user_id: str) -> FavoriteResponse:
        """Kullanıcının favorilerini ürün detaylarıyla (canlı olarak) getirir."""
        uid = _normalize_user_id(user_id)

        doc = await self.favorites.find_one({"user_id": uid})
        if not doc:
            return FavoriteResponse(user_id=user_id, items=[], total_count=0)

        product_ids = doc.get("product_ids", [])
        if not product_ids:
            return FavoriteResponse(user_id=user_id, items=[], total_count=0)

        # Ürünlerin güncel detaylarını DB'den çek
        cursor = self.products.find({"_id": {"$in": product_ids}})
        items = []
        async for p_doc in cursor:
            items.append(FavoriteItemSchema(
                id=str(p_doc["_id"]),
                name=p_doc.get("name", "Unknown"),
                price=float(p_doc.get("price", 0.0)),
                image_url=p_doc.get("image_url"),
                is_active=p_doc.get("is_active", True)
            ))

        return FavoriteResponse(
            user_id=user_id,
            items=items,
            total_count=len(items)
        )

    async def add_favorite(self, user_id: str, product_id: str) -> FavoriteResponse:
        """Kullanıcının favorilerine yeni bir ürün ekler."""
        try:
            uid = _normalize_user_id(user_id)
            pid = ObjectId(product_id)
        except Exception:
            raise ValueError("Invalid user_id or product_id")

        # Ürünün gerçekten var olup olmadığını kontrol et
        product = await self.products.find_one({"_id": pid})
        if not product:
            raise ValueError("Product not found")

        doc = await self.favorites.find_one({"user_id": uid})
        
        if not doc:
            # Yeni doküman oluştur
            new_doc = Favorite.create_document(user_id)
            new_doc["product_ids"].append(pid)
            await self.favorites.insert_one(new_doc)
        else:
            # Varsa güncelle
            if pid not in doc.get("product_ids", []):
                await self.favorites.update_one(
                    {"user_id": uid},
                    {
                        "$push": {"product_ids": pid},
                        "$set": {"updated_at": datetime.utcnow()}
                    }
                )

        return await self.get_favorites(user_id)

    async def remove_favorite(self, user_id: str, product_id: str) -> FavoriteResponse:
        """Kullanıcının favorilerinden ürünü çıkarır."""
        try:
            uid = _normalize_user_id(user_id)
            pid = ObjectId(product_id)
        except Exception:
            raise ValueError("Invalid user_id or product_id")

        await self.favorites.update_one(
            {"user_id": uid},
            {
                "$pull": {"product_ids": pid},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )

        return await self.get_favorites(user_id)
