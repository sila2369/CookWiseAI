"""
Product Model - MongoDB Document Schema
========================================

MongoDB'de products collection'ı için doküman yapısı.
category_id ObjectId referansı ile categories ile ilişkilidir.
"""

from datetime import datetime
from typing import Optional
import re

from bson import ObjectId

from app.models.category import generate_slug


class Product:
    """
    Product Model - MongoDB Products Collection

    Alanlar:
    - _id (ObjectId): Primary key
    - name, slug, description, price, stock
    - image_url, category_id (ObjectId), brand, unit
    - is_active, created_at, updated_at
    """

    COLLECTION = "products"

    class Fields:
        ID = "_id"
        NAME = "name"
        SLUG = "slug"
        DESCRIPTION = "description"
        PRICE = "price"
        STOCK = "stock"
        IMAGE_URL = "image_url"
        CATEGORY_ID = "category_id"
        BRAND = "brand"
        UNIT = "unit"
        IS_ACTIVE = "is_active"
        CREATED_AT = "created_at"
        UPDATED_AT = "updated_at"

    @staticmethod
    def _normalize_slug(slug: Optional[str], name: str) -> str:
        """Slug üretir veya normalize eder."""
        if slug and slug.strip():
            s = slug.strip().lower()
            s = re.sub(r"[^a-z0-9-]", "", s)
            return s or generate_slug(name)
        return generate_slug(name)

    @staticmethod
    def create_document(
        name: str,
        description: str,
        price: float,
        stock: int,
        category_id: str,
        slug: Optional[str] = None,
        image_url: Optional[str] = None,
        brand: Optional[str] = None,
        unit: Optional[str] = None,
        is_active: bool = True,
        is_promoted: bool = False,
        promotion_type: Optional[str] = None,
        promotion_label: Optional[str] = None,
        discounted_price: Optional[float] = None,
        promotion_buy_quantity: Optional[int] = None,
        promotion_pay_quantity: Optional[int] = None,
    ) -> dict:
        """MongoDB insert_one için doküman oluşturur."""
        now = datetime.utcnow()
        try:
            cat_oid = ObjectId(category_id)
        except Exception:
            raise ValueError(f"Invalid category_id: {category_id}")

        return {
            "name": name.strip(),
            "slug": Product._normalize_slug(slug, name),
            "description": description.strip() if description else "",
            "price": round(float(price), 2),
            "stock": max(0, int(stock)),
            "image_url": image_url.strip() if image_url else None,
            "category_id": cat_oid,
            "brand": brand.strip() if brand else None,
            "unit": unit.strip() if unit else None,
            "is_active": is_active,
            "is_promoted": bool(is_promoted),
            "promotion_type": promotion_type.strip() if promotion_type else None,
            "promotion_label": promotion_label.strip() if promotion_label else None,
            "discounted_price": round(float(discounted_price), 2) if discounted_price is not None else None,
            "promotion_buy_quantity": int(promotion_buy_quantity) if promotion_buy_quantity else None,
            "promotion_pay_quantity": int(promotion_pay_quantity) if promotion_pay_quantity else None,
            "created_at": now,
            "updated_at": now,
        }

    @staticmethod
    def mongo_to_dict(mongo_doc: Optional[dict]) -> Optional[dict]:
        """MongoDB dokümanını API dict'ine dönüştürür."""
        if not mongo_doc:
            return None
        d = mongo_doc.copy()
        if "_id" in d:
            d["id"] = str(d.pop("_id"))
        if "category_id" in d and isinstance(d["category_id"], ObjectId):
            d["category_id"] = str(d["category_id"])
        return d

    @staticmethod
    def dict_to_response(doc: dict) -> dict:
        """Response için güvenli dict (datetime, ObjectId → string)."""
        d = Product.mongo_to_dict(doc)
        if not d:
            return None
        for key in ("created_at", "updated_at"):
            if isinstance(d.get(key), datetime):
                d[key] = d[key].isoformat()
        return d

    @staticmethod
    def get_by_id_query(product_id: str) -> dict:
        """ID ile arama query."""
        try:
            return {"_id": ObjectId(product_id)}
        except Exception:
            return {"_id": None}

    @staticmethod
    def get_by_slug_query(slug: str) -> dict:
        """Slug ile arama query."""
        return {"slug": slug.lower().strip()}

    @staticmethod
    def get_by_category_query(category_id: str) -> dict:
        """Kategoriye göre arama query."""
        try:
            return {"category_id": ObjectId(category_id)}
        except Exception:
            return {"category_id": None}

    @staticmethod
    def build_update_dict(**kwargs) -> dict:
        """$set için update dict (None olmayan alanlar, updated_at otomatik)."""
        result = {k: v for k, v in kwargs.items() if v is not None}
        if "category_id" in result and isinstance(result["category_id"], str):
            try:
                result["category_id"] = ObjectId(result["category_id"])
            except Exception:
                del result["category_id"]
        if "price" in result:
            result["price"] = round(float(result["price"]), 2)
        if "stock" in result:
            result["stock"] = max(0, int(result["stock"]))
        if "discounted_price" in result and result["discounted_price"] is not None:
            result["discounted_price"] = round(float(result["discounted_price"]), 2)
        if "promotion_buy_quantity" in result and result["promotion_buy_quantity"] is not None:
            result["promotion_buy_quantity"] = max(1, int(result["promotion_buy_quantity"]))
        if "promotion_pay_quantity" in result and result["promotion_pay_quantity"] is not None:
            result["promotion_pay_quantity"] = max(1, int(result["promotion_pay_quantity"]))
        result["updated_at"] = datetime.utcnow()
        return result
