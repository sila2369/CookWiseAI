"""
Order Model - MongoDB Document Schema
======================================

Siparişler için doküman yapısı.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from bson import ObjectId

def _normalize_user_id(user_id: str):
    try:
        return ObjectId(user_id)
    except Exception:
        return user_id


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    PREPARING = "PREPARING"
    ON_THE_WAY = "ON_THE_WAY"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class Order:
    """
    Order Model - MongoDB Orders Collection

    Alanlar:
    - _id (ObjectId): Primary key
    - user_id (ObjectId): Siparişi veren kullanıcı
    - status (str): Sipariş durumu (OrderStatus enum değerleri)
    - items (List[dict]): Sipariş anındaki ürünler (product_id, name, price, quantity, subtotal)
    - total_price (float): Toplam sipariş tutarı
    - delivery_address (str): Teslimat adresi (şimdilik metin formatında)
    - payment_method (str): Ödeme yöntemi
    - created_at, updated_at
    """

    COLLECTION = "orders"

    @staticmethod
    def create_document(
        user_id: str,
        items: List[Dict[str, Any]],
        total_price: float,
        delivery_address: str,
        payment_method: str = "CASH_ON_DELIVERY",
        contact_phone: Optional[str] = None,
        delivery_slot: Optional[str] = None,
        delivery_note: Optional[str] = None,
    ) -> dict:
        """Yeni bir sipariş dokümanı oluşturur."""
        now = datetime.utcnow()
        uid = _normalize_user_id(user_id)

        return {
            "user_id": uid,
            "status": OrderStatus.PENDING.value,
            "items": items,  # Fiyatlar kilitlenmiş haliyle
            "total_price": round(float(total_price), 2),
            "delivery_address": delivery_address.strip(),
            "payment_method": payment_method.strip(),
            "contact_phone": (contact_phone or "").strip() or None,
            "delivery_slot": (delivery_slot or "").strip() or None,
            "delivery_note": (delivery_note or "").strip() or None,
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
        
        # Convert item product_ids if they are ObjectIds
        for item in d.get("items", []):
            if "product_id" in item and isinstance(item["product_id"], ObjectId):
                item["product_id"] = str(item["product_id"])
                
        return d

    @staticmethod
    def dict_to_response(doc: dict) -> Optional[dict]:
        """Response için güvenli dict (datetime, ObjectId → string)."""
        d = Order.mongo_to_dict(doc)
        if not d:
            return None
        for key in ("created_at", "updated_at"):
            if isinstance(d.get(key), datetime):
                d[key] = d[key].isoformat()
        return d
