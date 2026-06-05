"""
Category Service - Kategori iş mantığı
======================================

Kategori CRUD işlemleri. MongoDB ile çalışır.
"""

import logging
import re
from typing import Optional

from app.core.exceptions import DuplicateDocumentException
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryResponse, CategoryListResponse

logger = logging.getLogger(__name__)


class CategoryService:
    """Kategori işlemleri."""

    def __init__(self, db):
        if db is None:
            raise ValueError("Database connection is required")
        self.db = db
        self.collection = db[Category.COLLECTION]

    async def create(self, data: CategoryCreate) -> CategoryResponse:
        """
        Yeni kategori oluşturur.
        name veya slug benzersiz olmalı.
        """
        slug_val = (
            data.slug.strip().lower() if data.slug
            else Category.create_document(name=data.name)["slug"]
        )

        # name veya slug zaten var mı?
        name_escaped = re.escape(data.name.strip())
        existing = await self.collection.find_one({
            "$or": [
                {"name": {"$regex": f"^{name_escaped}$", "$options": "i"}},
                {"slug": slug_val},
            ]
        })
        if existing:
            if existing.get("slug") == slug_val:
                raise DuplicateDocumentException(
                    collection="categories",
                    field="slug",
                    value=slug_val,
                    message=f"Slug '{slug_val}' is already in use",
                )
            raise DuplicateDocumentException(
                collection="categories",
                field="name",
                value=data.name,
                message=f"Category with name '{data.name}' already exists",
            )

        doc = Category.create_document(
            name=data.name,
            slug=data.slug,
            description=data.description,
            image_url=data.image_url,
            is_active=data.is_active,
        )
        result = await self.collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        return CategoryResponse(**Category.dict_to_response(doc))

    async def list_active(self, skip: int = 0, limit: int = 50) -> CategoryListResponse:
        """Aktif kategorileri listeler."""
        cursor = self.collection.find({"is_active": True}).sort("name", 1).skip(skip).limit(limit)
        items = []
        async for doc in cursor:
            items.append(CategoryResponse(**Category.dict_to_response(doc)))

        total = await self.collection.count_documents({"is_active": True})
        return CategoryListResponse(items=items, total=total, skip=skip, limit=limit)

    async def get_by_id(self, category_id: str) -> Optional[CategoryResponse]:
        """ID ile kategori getirir. Bulunamazsa None."""
        doc = await self.collection.find_one(Category.get_by_id_query(category_id))
        if not doc:
            return None
        return CategoryResponse(**Category.dict_to_response(doc))
