"""
MongoDB Yardımcı Fonksiyonları
==============================

Ortak kullanılan MongoDB işlemleri.
"""

from typing import Optional

from bson import ObjectId


def to_object_id(value: str, field_name: str = "id") -> ObjectId:
    """
    String'i ObjectId'ye çevirir. Geçersizse ValueError.
    """
    try:
        return ObjectId(value)
    except Exception:
        raise ValueError(f"Invalid {field_name}: '{value}'")


async def ensure_category_exists(categories_collection, category_id: str) -> None:
    """
    Kategori var mı kontrol eder. Yoksa ValueError.
    """
    oid = to_object_id(category_id, "category_id")
    doc = await categories_collection.find_one({"_id": oid})
    if not doc:
        raise ValueError(f"Category with id '{category_id}' not found")
