"""
Cart Model - MongoDB Document Schema
=====================================

MongoDB'de carts collection'ı için doküman yapısı.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from bson import ObjectId

def _normalize_user_id(user_id: str):
    try:
        return ObjectId(user_id)
    except Exception:
        return user_id


class Cart:
    """
    Cart Model - MongoDB Carts Collection

    Alanlar:
    - _id (ObjectId): Primary key
    - user_id (ObjectId): Kullanıcının ID'si
    - items (List[dict]): Sepetteki ürünler (product_id, quantity)
    - created_at, updated_at
    """

    COLLECTION = "carts"

    class Fields:
        ID = "_id"
        USER_ID = "user_id"
        ITEMS = "items"
        CREATED_AT = "created_at"
        UPDATED_AT = "updated_at"

    @staticmethod
    def create_document(user_id: str) -> dict:
        """Yeni bir sepet dokümanı oluşturur."""
        now = datetime.utcnow()
        uid = _normalize_user_id(user_id)

        return {
            "user_id": uid,
            "items": [],
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
        if "user_id" in d and isinstance(d["user_id"], ObjectId):
            d["user_id"] = str(d["user_id"])
        
        # Convert item product_ids
        for item in d.get("items", []):
            if "product_id" in item and isinstance(item["product_id"], ObjectId):
                item["product_id"] = str(item["product_id"])
                
        return d

    @staticmethod
    def dict_to_response(doc: dict) -> Optional[dict]:
        """Response için güvenli dict (datetime, ObjectId → string)."""
        d = Cart.mongo_to_dict(doc)
        if not d:
            return None
        for key in ("created_at", "updated_at"):
            if isinstance(d.get(key), datetime):
                d[key] = d[key].isoformat()
        return d

    @staticmethod
    def get_by_user_id_query(user_id: str) -> dict:
        """Kullanıcı ID'si ile arama query."""
        return {"user_id": _normalize_user_id(user_id)}
