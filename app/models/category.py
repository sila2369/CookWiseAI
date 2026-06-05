"""
Category Model - MongoDB Document Schema
=========================================

MongoDB'de categories collection'ı için doküman yapısı.
slug alanı benzersiz (unique index), URL ve filtreleme için kullanılır.
"""

from datetime import datetime
from typing import Optional
import re

from bson import ObjectId


def generate_slug(text: str) -> str:
    """
    Metinden URL-safe slug üretir.
    - Küçük harf, tire, rakam
    - Türkçe karakterler ASCII'ye dönüştürülür
    """
    tr_map = {
        "ı": "i", "ğ": "g", "ü": "u", "ş": "s", "ö": "o", "ç": "c",
        "İ": "i", "Ğ": "g", "Ü": "u", "Ş": "s", "Ö": "o", "Ç": "c",
    }
    s = text.lower().strip()
    for tr, ascii_char in tr_map.items():
        s = s.replace(tr, ascii_char)
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[-\s]+", "-", s).strip("-")
    return s or "category"


class Category:
    """
    Category Model - MongoDB Categories Collection

    Alanlar:
    - _id (ObjectId): MongoDB primary key
    - name (str): Kategori adı
    - slug (str): URL-safe benzersiz tanımlayıcı
    - description (str, optional): Açıklama
    - image_url (str, optional): Görsel URL
    - is_active (bool): Aktif mi (default: True)
    - created_at (datetime): Oluşturulma
    - updated_at (datetime): Son güncelleme

    Index: slug unique=True
    """

    COLLECTION = "categories"

    class Fields:
        ID = "_id"
        NAME = "name"
        SLUG = "slug"
        DESCRIPTION = "description"
        IMAGE_URL = "image_url"
        IS_ACTIVE = "is_active"
        CREATED_AT = "created_at"
        UPDATED_AT = "updated_at"

    @staticmethod
    def create_document(
        name: str,
        slug: Optional[str] = None,
        description: Optional[str] = None,
        image_url: Optional[str] = None,
        is_active: bool = True,
    ) -> dict:
        """MongoDB insert_one için doküman oluşturur."""
        now = datetime.utcnow()
        slug_val = slug.strip().lower() if slug else generate_slug(name)
        slug_val = re.sub(r"[^a-z0-9-]", "", slug_val) or generate_slug(name)

        return {
            "name": name.strip(),
            "slug": slug_val,
            "description": description.strip() if description else None,
            "image_url": image_url.strip() if image_url else None,
            "is_active": is_active,
            "created_at": now,
            "updated_at": now,
        }

    @staticmethod
    def mongo_to_dict(mongo_doc: Optional[dict]) -> Optional[dict]:
        """MongoDB dokümanını API dict'ine dönüştürür (_id → id)."""
        if not mongo_doc:
            return None
        d = mongo_doc.copy()
        if "_id" in d:
            d["id"] = str(d.pop("_id"))
        return d

    @staticmethod
    def dict_to_response(doc: dict) -> dict:
        """Response için güvenli dict (datetime → ISO string)."""
        d = Category.mongo_to_dict(doc)
        if not d:
            return None
        for key in ("created_at", "updated_at"):
            if isinstance(d.get(key), datetime):
                d[key] = d[key].isoformat()
        return d

    @staticmethod
    def get_by_id_query(category_id: str) -> dict:
        """ID ile arama query."""
        try:
            return {"_id": ObjectId(category_id)}
        except Exception:
            return {"_id": None}

    @staticmethod
    def get_by_slug_query(slug: str) -> dict:
        """Slug ile arama query."""
        return {"slug": slug.lower().strip()}

    @staticmethod
    def build_update_dict(**kwargs) -> dict:
        """$set için update dict (updated_at otomatik)."""
        kwargs["updated_at"] = datetime.utcnow()
        return {k: v for k, v in kwargs.items() if v is not None}
