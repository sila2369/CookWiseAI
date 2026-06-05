"""
Favorite Model - MongoDB Document Schema
========================================

Kullanıcı favorileri için doküman yapısı.
"""

from datetime import datetime
from typing import Optional, List
from bson import ObjectId

def _normalize_user_id(user_id: str):
    try:
        return ObjectId(user_id)
    except Exception:
        return user_id


class Favorite:
    """
    Favorite Model - MongoDB Favorites Collection

    Alanlar:
    - _id (ObjectId): Primary key
    - user_id (ObjectId): Favorilerin sahibi
    - product_ids (List[ObjectId]): Favoriye alınan ürünlerin referansları
    - updated_at: Son güncelleme tarihi
    """

    COLLECTION = "favorites"

    @staticmethod
    def create_document(user_id: str) -> dict:
        """Kullanıcı için boş bir favori dokümanı oluşturur."""
        now = datetime.utcnow()
        uid = _normalize_user_id(user_id)

        return {
            "user_id": uid,
            "product_ids": [],
            "updated_at": now
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
            
        # product_ids ObjectId'lerini string yap
        if "product_ids" in d:
            d["product_ids"] = [str(pid) for pid in d["product_ids"]]
                
        return d
