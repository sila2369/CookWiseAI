"""
Address Service - Adres iş mantığı
===================================
Kullanıcı adreslerini oluşturma, listeleme, güncelleme ve silme.
Varsayılan adres mantığını yönetme.
"""

import logging
from datetime import datetime
from typing import Optional
from bson import ObjectId

from app.models.address import Address
from app.schemas.address import AddressCreate, AddressUpdate, AddressResponse, AddressListResponse

logger = logging.getLogger(__name__)


class AddressService:
    """Adres işlemleri."""

    def __init__(self, db):
        if db is None:
            raise ValueError("Database connection is required")
        self.db = db
        self.addresses = db[Address.COLLECTION]

    async def _handle_default_status(self, user_id: ObjectId, is_default: bool, exclude_id: Optional[ObjectId] = None):
        """Eğer yeni adres varsayılan (default) olarak işaretlendiyse, önceki varsayılan adreslerin işaretini kaldırır."""
        if not is_default:
            return

        query = {"user_id": user_id, "is_default": True}
        if exclude_id:
            query["_id"] = {"$ne": exclude_id}

        await self.addresses.update_many(
            query,
            {"$set": {"is_default": False, "updated_at": datetime.utcnow()}}
        )

    async def create_address(self, user_id: str, data: AddressCreate) -> AddressResponse:
        """Yeni bir adres ekler."""
        try:
            uid = ObjectId(user_id)
        except Exception:
            raise ValueError(f"Invalid user_id: {user_id}")

        # Eğer ilk adresi ise otomatik olarak varsayılan yap
        if not data.is_default:
            count = await self.addresses.count_documents({"user_id": uid})
            if count == 0:
                data.is_default = True

        doc = Address.create_document(
            user_id=user_id,
            title=data.title,
            city=data.city,
            district=data.district,
            full_address=data.full_address,
            is_default=data.is_default
        )
        
        result = await self.addresses.insert_one(doc)
        doc["_id"] = result.inserted_id

        # Diğer varsayılanları sıfırla
        await self._handle_default_status(uid, data.is_default, exclude_id=doc["_id"])

        return AddressResponse(**Address.dict_to_response(doc))

    async def get_user_addresses(self, user_id: str) -> AddressListResponse:
        """Kullanıcının adreslerini getirir."""
        try:
            uid = ObjectId(user_id)
        except Exception:
            raise ValueError(f"Invalid user_id: {user_id}")

        cursor = self.addresses.find({"user_id": uid}).sort([("is_default", -1), ("created_at", -1)])
        
        items = []
        async for doc in cursor:
            items.append(AddressResponse(**Address.dict_to_response(doc)))
            
        return AddressListResponse(items=items, total=len(items))

    async def get_address(self, address_id: str, user_id: str) -> Optional[AddressResponse]:
        """Adresi getirir. (Sadece o kullanıcıya aitse)"""
        try:
            aid = ObjectId(address_id)
            uid = ObjectId(user_id)
        except Exception:
            raise ValueError("Invalid ID format")

        doc = await self.addresses.find_one({"_id": aid, "user_id": uid})
        if not doc:
            return None
            
        return AddressResponse(**Address.dict_to_response(doc))

    async def update_address(self, address_id: str, user_id: str, data: AddressUpdate) -> Optional[AddressResponse]:
        """Adresi günceller."""
        try:
            aid = ObjectId(address_id)
            uid = ObjectId(user_id)
        except Exception:
            raise ValueError("Invalid ID format")

        doc = await self.addresses.find_one({"_id": aid, "user_id": uid})
        if not doc:
            return None

        update_data = data.model_dump(exclude_none=True)
        if not update_data:
            return AddressResponse(**Address.dict_to_response(doc))

        update_data["updated_at"] = datetime.utcnow()

        await self.addresses.update_one(
            {"_id": aid},
            {"$set": update_data}
        )

        # Varsayılan durumu değiştiyse yönet
        is_default_now = update_data.get("is_default", doc.get("is_default"))
        if "is_default" in update_data and is_default_now:
            await self._handle_default_status(uid, True, exclude_id=aid)

        updated_doc = await self.addresses.find_one({"_id": aid})
        return AddressResponse(**Address.dict_to_response(updated_doc))

    async def delete_address(self, address_id: str, user_id: str) -> bool:
        """Adresi siler."""
        try:
            aid = ObjectId(address_id)
            uid = ObjectId(user_id)
        except Exception:
            raise ValueError("Invalid ID format")

        result = await self.addresses.delete_one({"_id": aid, "user_id": uid})
        return result.deleted_count > 0
