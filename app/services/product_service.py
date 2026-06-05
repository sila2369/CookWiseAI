"""
Product Service - Ürün iş mantığı
==================================

Ürün CRUD işlemleri. category_id geçerliliği ve slug benzersizliği kontrol edilir.
"""

import logging
import re
from datetime import datetime
from typing import Optional

from app.core.exceptions import DuplicateDocumentException
from app.utils.mongo_helpers import ensure_category_exists, to_object_id
from app.models.product import Product
from app.models.category import Category
from app.schemas.product import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductListResponse,
)

logger = logging.getLogger(__name__)


class ProductService:
    """Ürün işlemleri."""

    def __init__(self, db):
        if db is None:
            raise ValueError("Database connection is required")
        self.db = db
        self.collection = db[Product.COLLECTION]
        self.categories = db[Category.COLLECTION]

    async def create(self, data: ProductCreate) -> ProductResponse:
        """
        Yeni ürün oluşturur.
        category_id geçerli olmalı, slug benzersiz olmalı.
        """
        slug_val = (
            Product._normalize_slug(data.slug, data.name)
            if data.slug
            else Product.create_document(
                name=data.name,
                description="",
                price=0,
                stock=0,
                category_id=data.category_id,
            )["slug"]
        )

        await ensure_category_exists(self.categories, data.category_id)

        # slug zaten var mı?
        existing = await self.collection.find_one({"slug": slug_val})
        if existing:
            raise DuplicateDocumentException(
                collection="products",
                field="slug",
                value=slug_val,
                message=f"Product slug '{slug_val}' is already in use",
            )

        doc = Product.create_document(
            name=data.name,
            description=data.description,
            price=data.price,
            stock=data.stock,
            category_id=data.category_id,
            slug=data.slug,
            image_url=data.image_url,
            brand=data.brand,
            unit=data.unit,
            is_active=data.is_active,
            is_promoted=data.is_promoted,
            promotion_type=data.promotion_type,
            promotion_label=data.promotion_label,
            discounted_price=data.discounted_price,
            promotion_buy_quantity=data.promotion_buy_quantity,
            promotion_pay_quantity=data.promotion_pay_quantity,
        )
        result = await self.collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        if doc.get("is_promoted"):
            try:
                from app.services.notification_service import NotificationService

                notifier = NotificationService(self.db)
                await notifier.create_campaign_notification(
                    product_id=doc["_id"],
                    product_name=doc.get("name", "Urun"),
                    promotion_label=doc.get("promotion_label"),
                )
            except Exception as e:
                logger.error(f"Error creating campaign notification: {e}")
        return ProductResponse(**Product.dict_to_response(doc))

    def _build_list_query(
        self,
        category_id: Optional[str] = None,
        search: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
    ) -> dict:
        """Filtreler için MongoDB query oluşturur."""
        query = {"is_active": True}

        if category_id:
            try:
                query["category_id"] = to_object_id(category_id, "category_id")
            except ValueError:
                pass

        if search and search.strip():
            term = re.escape(search.strip())
            query["$or"] = [
                {"name": {"$regex": term, "$options": "i"}},
                {"description": {"$regex": term, "$options": "i"}},
            ]

        if min_price is not None or max_price is not None:
            price_cond = {}
            if min_price is not None:
                price_cond["$gte"] = float(min_price)
            if max_price is not None:
                price_cond["$lte"] = float(max_price)
            query["price"] = price_cond

        return query

    async def list_active(
        self,
        skip: int = 0,
        limit: int = 50,
        category_id: Optional[str] = None,
        search: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
    ) -> ProductListResponse:
        """Aktif ürünleri filtrelerle listeler."""
        query = self._build_list_query(
            category_id=category_id,
            search=search,
            min_price=min_price,
            max_price=max_price,
        )
        cursor = (
            self.collection.find(query)
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )
        items = []
        async for doc in cursor:
            items.append(ProductResponse(**Product.dict_to_response(doc)))

        total = await self.collection.count_documents(query)
        return ProductListResponse(items=items, total=total, skip=skip, limit=limit)

    async def get_by_id(self, product_id: str) -> Optional[ProductResponse]:
        """ID ile ürün getirir. Bulunamazsa veya pasifse None."""
        doc = await self.collection.find_one(Product.get_by_id_query(product_id))
        if not doc or not doc.get("is_active", True):
            return None
        return ProductResponse(**Product.dict_to_response(doc))

    async def _get_doc(self, product_id: str):
        """ID ile ham doküman (admin işlemleri için, is_active fark etmez)."""
        return await self.collection.find_one(Product.get_by_id_query(product_id))

    async def update(
        self, product_id: str, data: ProductUpdate
    ) -> Optional[ProductResponse]:
        """
        Ürün günceller.
        category_id değişirse geçerlilik, slug değişirse çakışma kontrolü.
        """
        doc = await self._get_doc(product_id)
        if not doc:
            return None

        update_data = data.model_dump(exclude_none=True)

        if not update_data:
            return ProductResponse(**Product.dict_to_response(doc))

        if "category_id" in update_data:
            await ensure_category_exists(self.categories, update_data["category_id"])

        if "slug" in update_data:
            slug_val = Product._normalize_slug(
                update_data["slug"], update_data.get("name") or doc["name"]
            )
            existing = await self.collection.find_one(
                {"slug": slug_val, "_id": {"$ne": doc["_id"]}}
            )
            if existing:
                raise DuplicateDocumentException(
                    collection="products",
                    field="slug",
                    value=slug_val,
                    message=f"Product slug '{slug_val}' is already in use",
                )
            update_data["slug"] = slug_val

        set_data = Product.build_update_dict(**update_data)
        await self.collection.update_one(
            {"_id": doc["_id"]}, {"$set": set_data}
        )
        updated = await self.collection.find_one({"_id": doc["_id"]})

        promotion_started = update_data.get("is_promoted") is True and not bool(doc.get("is_promoted"))
        promotion_changed = any(
            key in update_data
            for key in (
                "promotion_type",
                "promotion_label",
                "discounted_price",
                "promotion_buy_quantity",
                "promotion_pay_quantity",
            )
        )
        if updated and updated.get("is_promoted") and (promotion_started or promotion_changed):
            try:
                from app.services.notification_service import NotificationService

                notifier = NotificationService(self.db)
                await notifier.create_campaign_notification(
                    product_id=updated["_id"],
                    product_name=updated.get("name", "Urun"),
                    promotion_label=updated.get("promotion_label"),
                )
            except Exception as e:
                logger.error(f"Error creating campaign notification: {e}")

        # Fiyat indirimi kontrolü ve Push Notification tetiklemesi
        if "price" in update_data and float(update_data["price"]) < float(doc.get("price", 0.0)):
            try:
                import asyncio
                from app.services.notification_service import NotificationService
                from app.models.favorite import Favorite
                
                # Bu ürünü favorileyenleri bul
                fav_cursor = self.db[Favorite.COLLECTION].find({"product_ids": doc["_id"]}, {"user_id": 1})
                fav_user_ids = []
                async for f in fav_cursor:
                    if "user_id" in f:
                        fav_user_ids.append(f["user_id"])
                        
                if fav_user_ids:
                    notifier = NotificationService(self.db)
                    asyncio.create_task(
                        notifier.send_discount_notification(
                            product_name=doc.get("name", "Ürün"),
                            old_price=float(doc.get("price", 0.0)),
                            new_price=float(update_data["price"]),
                            user_ids=fav_user_ids
                        )
                    )
                    logger.info(f"Discount notification triggered for product {product_id} to {len(fav_user_ids)} users.")
            except Exception as e:
                logger.error(f"Error triggering discount notification: {e}")

        return ProductResponse(**Product.dict_to_response(updated))

    async def soft_delete(self, product_id: str) -> Optional[ProductResponse]:
        """Soft delete: is_active=False yapar."""
        doc = await self._get_doc(product_id)
        if not doc:
            return None
        await self.collection.update_one(
            {"_id": doc["_id"]},
            {"$set": {"is_active": False, "updated_at": datetime.utcnow()}},
        )
        updated = await self.collection.find_one({"_id": doc["_id"]})
        return ProductResponse(**Product.dict_to_response(updated))
