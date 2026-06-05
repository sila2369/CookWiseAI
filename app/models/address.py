"""
Address Model - MongoDB Document Schema
========================================

Kullanıcı adresleri için doküman yapısı.
"""

from datetime import datetime
from typing import Optional
from bson import ObjectId


class Address:
    """
    Address Model - MongoDB Addresses Collection

    Alanlar:
    - _id (ObjectId): Primary key
    - user_id (ObjectId): Adresin sahibi
    - title (str): Adres başlığı (Ev, İş vb.)
    - city (str): Şehir
    - district (str): İlçe
    - full_address (str): Açık adres detayları
    - is_default (bool): Varsayılan adres mi?
    - created_at, updated_at
    """

    COLLECTION = "addresses"

    @staticmethod
    def create_document(
        user_id: str,
        title: str,
        city: str,
        district: str,
        full_address: str,
        is_default: bool = False
    ) -> dict:
        """Yeni bir adres dokümanı oluşturur."""
        now = datetime.utcnow()
        try:
            uid = ObjectId(user_id)
        except Exception:
            raise ValueError(f"Invalid user_id: {user_id}")

        return {
            "user_id": uid,
            "title": title.strip(),
            "city": city.strip(),
            "district": district.strip(),
            "full_address": full_address.strip(),
            "is_default": is_default,
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
                
        return d

    @staticmethod
    def dict_to_response(doc: dict) -> Optional[dict]:
        """Response için güvenli dict (datetime, ObjectId → string)."""
        d = Address.mongo_to_dict(doc)
        if not d:
            return None
        for key in ("created_at", "updated_at"):
            if isinstance(d.get(key), datetime):
                d[key] = d[key].isoformat()
        return d
