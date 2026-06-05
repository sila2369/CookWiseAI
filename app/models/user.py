"""
User Model - MongoDB Document Schema
=====================================

MongoDB'de users collection'ı için doküment yapısı.
PyMongo/Motor ile çalışır (dict-like).

Kullanım:
    user_doc = {
        "full_name": "John Doe",
        "email": "john@example.com",
        "hashed_password": "hash123...",
        "phone": "+905551234567",
        "is_active": True,
        "is_admin": False,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    result = await db["users"].insert_one(user_doc)
    user_id = result.inserted_id  # MongoDB ObjectId
"""

from datetime import datetime
from typing import Optional
from bson import ObjectId


class User:
    """
    User Model - MongoDB Users Collection
    
    Alanlar:
    --------
    - _id (ObjectId): MongoDB primary key (otomatik)
    - full_name (str): Kullanıcı tam adı
    - email (str): Email adresi (unique)
    - hashed_password (str): Bcrypt ile hash'lenmiş şifre
    - phone (str, optional): Telefon numarası
    - is_active (bool): Hesap aktif mi? (default: True)
    - is_admin (bool): Admin mi? (default: False)
    - created_at (datetime): Oluşturulma tarihi
    - updated_at (datetime): Son güncellenme tarihi
    
    Database Index'ler:
    ------------------
    - email: unique=True (tekil email)
    - created_at: sıralama için
    """
    
    # ==================== FIELD DEFINITIONS ====================
    
    # MongoDB'ye döküman örneği
    EXAMPLE_DOCUMENT = {
        "_id": ObjectId("507f1f77bcf86cd799439011"),  # MongoDB auto-generates
        "full_name": "John Doe",
        "email": "john@example.com",
        "hashed_password": "$2b$12$abcdefghijklmnopqrstuvwxyz...",  # bcrypt hash
        "phone": "+905551234567",
        "is_active": True,
        "is_admin": False,
        "created_at": datetime(2026, 3, 18, 10, 30, 0),
        "updated_at": datetime(2026, 3, 18, 10, 30, 0),
    }
    
    # ==================== FACTORY METHODS ====================
    
    @staticmethod
    def create_user_document(
        full_name: str,
        email: str,
        hashed_password: str,
        phone: Optional[str] = None,
        is_active: bool = True,
        is_admin: bool = False,
        is_verified: bool = False,
        verification_code: Optional[str] = None,
        verification_code_expires_at: Optional[datetime] = None,
    ) -> dict:
        """
        Yeni user dokümanı oluştur (insert_one'dan önceki helper)
        
        Args:
            full_name: Tam ad
            email: Email adresi (benzersiz)
            hashed_password: Bcrypt hash'lenmiş şifre
            phone: Telefon (opsiyonel)
            is_active: Hesap aktif mi? (default: True)
            is_admin: Admin mi? (default: False)
        
        Returns:
            dict: MongoDB insert_one() için doküman
        
        Örnek:
            user_doc = User.create_user_document(
                full_name="John Doe",
                email="john@example.com",
                hashed_password="$2b$12$...",
                phone="+905551234567"
            )
            result = await db["users"].insert_one(user_doc)
        """
        now = datetime.utcnow()
        
        return {
            "full_name": full_name,
            "email": email.lower().strip(),  # Normalize email
            "hashed_password": hashed_password,
            "phone": phone,
            "is_active": is_active,
            "is_admin": is_admin,
            "is_verified": is_verified,
            "verification_code": verification_code,
            "verification_code_expires_at": verification_code_expires_at,
            "created_at": now,
            "updated_at": now,
        }
    
    # ==================== CONVERSION METHODS ====================
    
    @staticmethod
    def mongo_to_dict(mongo_doc: dict) -> dict:
        """
        MongoDB dokümanını Python dict'e dönüştür
        
        MongoDB'den çekilen doküman:
            {"_id": ObjectId(...), "full_name": "John", ...}
        
        Python dict'e (ID string'e dönüştürülmüş):
            {"id": "507f1f77bcf86cd799439011", "full_name": "John", ...}
        
        Args:
            mongo_doc: MongoDB dokümanı
        
        Returns:
            dict: Python dict (id string, _id silinmiş)
        
        Örnek:
            user = await db["users"].find_one({"email": "john@example.com"})
            user_dict = User.mongo_to_dict(user)  # _id → id (string)
        """
        if not mongo_doc:
            return None
        
        user_dict = mongo_doc.copy()
        
        # _id'yi string'e dönüştür (id olarak)
        if "_id" in user_dict:
            user_dict["id"] = str(user_dict.pop("_id"))
        
        return user_dict
    
    @staticmethod
    def dict_to_response(user_dict: dict) -> dict:
        """
        Database dokümanını API response'a dönüştür
        
        Yapar:
        - hashed_password'u siler
        - _id'yi id'ye dönüştürür
        - datetime'ları ISO string'e dönüştürür
        
        Args:
            user_dict: Database'den gelen dict
        
        Returns:
            dict: API response için güvenli dict
        
        Örnek:
            user = await db["users"].find_one(...)
            response = User.dict_to_response(user)
            # hashed_password kaldırılmış, datetime ISO string'e dönüştürülmüş
        """
        user_dict = User.mongo_to_dict(user_dict)
        
        if user_dict:
            # Sensitive fields sil
            user_dict.pop("hashed_password", None)
            
            # Datetime'ları ISO format'a dönüştür
            if isinstance(user_dict.get("created_at"), datetime):
                user_dict["created_at"] = user_dict["created_at"].isoformat()
            
            if isinstance(user_dict.get("updated_at"), datetime):
                user_dict["updated_at"] = user_dict["updated_at"].isoformat()
        
        return user_dict
    
    # ==================== VALIDATION METHODS ====================
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """
        Email format'ını doğrula (basit validation)
        
        Daha kapsamlı validation schema'da yapılır (Pydantic EmailStr)
        
        Args:
            email: Email adresi
        
        Returns:
            bool: Geçerli mi?
        """
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validate_phone(phone: str) -> bool:
        """
        Telefon numarasını doğrula (basit validation)
        
        Format: +[country code][number]
        
        Args:
            phone: Telefon numarası
        
        Returns:
            bool: Geçerli mi?
        """
        import re
        # +905551234567 benzeri format
        pattern = r'^\+\d{10,15}$'
        return re.match(pattern, phone) is not None
    
    # ==================== QUERY HELPERS ====================
    
    @staticmethod
    def get_user_by_email_query(email: str) -> dict:
        """
        Email'le kullanıcı aramak için MongoDB query
        
        Örnek:
            query = User.get_user_by_email_query("john@example.com")
            user = await db["users"].find_one(query)
        """
        return {"email": email.lower().strip()}
    
    @staticmethod
    def get_user_by_id_query(user_id: str) -> dict:
        """
        ID'yle kullanıcı aramak için MongoDB query
        
        Örnek:
            query = User.get_user_by_id_query(user_id)
            user = await db["users"].find_one(query)
        """
        try:
            return {"_id": ObjectId(user_id)}
        except:
            return {"_id": None}  # Invalid ID
    
    # ==================== UPDATE HELPERS ====================
    
    @staticmethod
    def get_update_dict(**kwargs) -> dict:
        """
        MongoDB $set operator ile update için dict oluştur
        
        Args:
            **kwargs: Güncellenecek alanlar
        
        Returns:
            dict: MongoDB update filter'ı
        
        Örnek:
            update_dict = User.get_update_dict(
                full_name="Jane Doe",
                phone="+905551234567"
            )
            await db["users"].update_one(
                {"_id": ObjectId(user_id)},
                {"$set": update_dict}
            )
        """
        # updated_at otomatik olarak ekle
        kwargs["updated_at"] = datetime.utcnow()
        
        return kwargs
    
    # ==================== CONSTANTS ====================
    
    class Fields:
        """User model alanları (constants olarak)"""
        ID = "_id"
        FULL_NAME = "full_name"
        EMAIL = "email"
        HASHED_PASSWORD = "hashed_password"
        PHONE = "phone"
        IS_ACTIVE = "is_active"
        IS_ADMIN = "is_admin"
        IS_VERIFIED = "is_verified"
        VERIFICATION_CODE = "verification_code"
        VERIFICATION_CODE_EXPIRES_AT = "verification_code_expires_at"
        CREATED_AT = "created_at"
        UPDATED_AT = "updated_at"
