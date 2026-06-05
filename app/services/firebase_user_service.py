"""
Firebase User Service - Kullanıcı yönetimi (Auth + Firestore)
==============================================================

Firebase Authentication: Kayıt, giriş
Firestore: Kullanıcı profilleri (full_name, phone, is_admin, is_active)
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from app.core.exceptions import DatabaseConnectionException, DuplicateDocumentException, InvalidCredentialsException

logger = logging.getLogger(__name__)

# Firestore koleksiyon adı
USERS_COLLECTION = "users"


def _get_firebase_auth():
    """Firebase Auth instance."""
    from firebase_admin import auth
    return auth


def _get_firestore():
    """Firestore client."""
    from firebase_admin import firestore
    return firestore.client()


def _ensure_firebase_init():
    """Firebase init edilmiş mi kontrol et."""
    from app.core.firebase import get_firebase_app
    if get_firebase_app() is None:
        from app.core.firebase import init_firebase
        from app.core.config import settings
        if not init_firebase(
            settings.FIREBASE_CREDENTIALS_PATH,
            settings.FIREBASE_PROJECT_ID,
        ):
            raise RuntimeError("Firebase baslatilamadi")


def _doc_to_user_dict(doc) -> Optional[Dict[str, Any]]:
    """Firestore doc -> API user dict."""
    if not doc or not doc.exists:
        return None
    data = doc.to_dict().copy()
    legacy_field_map = {
        "Email": "email",
        "Full_Name": "full_name",
        "FullName": "full_name",
        "Phone": "phone",
        "is_Active": "is_active",
        "is_Admin": "is_admin",
        "Is_Admin": "is_admin",
        "is_Verified": "is_verified",
    }
    for legacy_key, normalized_key in legacy_field_map.items():
        if normalized_key not in data and legacy_key in data:
            data[normalized_key] = data[legacy_key]
    data["id"] = doc.id
    # Eski kayitlarda alan eksik olabilir; API schema ile uyumlu varsayilanlar.
    if "email" in data and isinstance(data["email"], str):
        data["email"] = data["email"].strip().lower()
    if "full_name" not in data and data.get("email"):
        data["full_name"] = str(data["email"]).split("@")[0]
    data.setdefault("is_active", True)
    data.setdefault("is_admin", False)
    data.setdefault("is_verified", False)
    now_iso = datetime.utcnow().isoformat()
    data.setdefault("created_at", now_iso)
    data.setdefault("updated_at", data["created_at"])
    # Timestamp/datetime -> ISO string
    for key in ("created_at", "updated_at", "verification_code_expires_at"):
        if key not in data:
            continue
        val = data[key]
        if hasattr(val, "isoformat") and callable(getattr(val, "isoformat", None)):
            data[key] = val.isoformat()
        elif hasattr(val, "timestamp"):
            data[key] = datetime.utcfromtimestamp(val.timestamp()).isoformat()
    return data


class FirebaseUserService:
    """Firebase ile kullanıcı işlemleri."""

    async def create_user(
        self,
        email: str,
        password: str,
        full_name: str,
        phone: Optional[str] = None,
        is_admin: bool = False,
    ) -> Dict[str, Any]:
        """
        Yeni kullanıcı oluştur (Firebase Auth + Firestore profil).
        """
        _ensure_firebase_init()
        
        def _create():
            auth = _get_firebase_auth()
            db = _get_firestore()
            
            # Email zaten kayıtlı mı?
            try:
                auth.get_user_by_email(email.lower())
                raise DuplicateDocumentException(
                    collection="users",
                    field="email",
                    value=email,
                    message=f"Email '{email}' is already registered",
                )
            except DuplicateDocumentException:
                raise
            except Exception:
                # User not found (UserNotFoundError, ValueError, vb.) = OK
                pass
            
            # Firebase Auth'da kullanıcı oluştur
            user_record = auth.create_user(
                email=email.lower(),
                password=password,
                display_name=full_name,
            )
            uid = user_record.uid
            
            # Firestore'da profil
            now = datetime.utcnow()
            profile = {
                "full_name": full_name.strip(),
                "email": email.lower(),
                "phone": phone or None,
                "is_active": True,
                "is_admin": is_admin,
                "is_verified": False,
                "verification_code": None,
                "verification_code_expires_at": None,
                "created_at": now,
                "updated_at": now,
            }
            db.collection(USERS_COLLECTION).document(uid).set(profile)
            
            return {
                "id": uid,
                **profile,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }
        
        return await asyncio.to_thread(_create)

    async def sign_in(self, email: str, password: str) -> Dict[str, Any]:
        """
        Email/şifre ile giriş. Firebase REST API kullanır.
        Döner: {"uid": ..., "id_token": ..., "user": {...}}
        """
        from app.core.config import settings
        import httpx
        
        if not settings.FIREBASE_API_KEY:
            raise RuntimeError("FIREBASE_API_KEY .env'de tanimli olmali (Firebase Console -> Project Settings)")
        
        url = (
            f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
            f"?key={settings.FIREBASE_API_KEY}"
        )
        payload = {
            "email": email.lower(),
            "password": password,
            "returnSecureToken": True,
        }
        
        try:
            async with httpx.AsyncClient() as client:
                r = await client.post(url, json=payload)
                data = r.json()
        except httpx.RequestError as exc:
            logger.error(f"Firebase login connection failed: {exc}")
            raise DatabaseConnectionException()
        
        if "error" in data:
            logger.warning(f"Firebase login failed: {data['error'].get('message')}")
            raise InvalidCredentialsException()
        
        uid = data.get("localId")
        id_token = data.get("idToken")
        
        # Firestore'dan profil al
        user = await self.get_user_by_uid(uid)
        if not user:
            raise InvalidCredentialsException()
        
        return {"uid": uid, "id_token": id_token, "user": user}

    async def get_user_by_uid(self, uid: str) -> Optional[Dict[str, Any]]:
        """UID ile kullanıcı getir."""
        _ensure_firebase_init()
        
        def _get():
            db = _get_firestore()
            doc = db.collection(USERS_COLLECTION).document(uid).get()
            return _doc_to_user_dict(doc)
        
        return await asyncio.to_thread(_get)

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Email ile kullanıcı getir."""
        _ensure_firebase_init()
        
        def _get():
            db = _get_firestore()
            ref = db.collection(USERS_COLLECTION).where("email", "==", email.lower()).limit(1)
            docs = ref.stream()
            for doc in docs:
                return _doc_to_user_dict(doc)
            return None
        
        return await asyncio.to_thread(_get)

    async def update_user(self, uid: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Kullanıcı profilini güncelle."""
        _ensure_firebase_init()
        
        def _update():
            db = _get_firestore()
            ref = db.collection(USERS_COLLECTION).document(uid)
            doc = ref.get()
            if not doc.exists:
                return None
            
            # Sadece izin verilen alanlar
            allowed = {
                "full_name",
                "phone",
                "is_active",
                "is_admin",
                "is_verified",
                "verification_code",
                "verification_code_expires_at",
            }
            updates = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
            if not updates:
                return _doc_to_user_dict(ref.get())
            
            updates["updated_at"] = datetime.utcnow()
            ref.update(updates)
            return _doc_to_user_dict(ref.get())
        
        return await asyncio.to_thread(_update)

    async def upsert_oauth_user(
        self,
        uid: str,
        email: str,
        full_name: Optional[str] = None,
        phone: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Google/Firebase OAuth ile gelen kullanıcıyı oluşturur veya günceller."""
        _ensure_firebase_init()

        def _upsert():
            db = _get_firestore()
            ref = db.collection(USERS_COLLECTION).document(uid)
            doc = ref.get()
            now = datetime.utcnow()

            if doc.exists:
                current = doc.to_dict() or {}
                updates = {
                    "email": email.lower(),
                    "full_name": full_name or current.get("full_name") or email.split("@")[0],
                    "updated_at": now,
                }
                if phone:
                    updates["phone"] = phone
                ref.update(updates)
                return _doc_to_user_dict(ref.get())

            payload = {
                "full_name": full_name or email.split("@")[0],
                "email": email.lower(),
                "phone": phone or None,
                "is_active": True,
                "is_admin": False,
                "is_verified": True,
                "created_at": now,
                "updated_at": now,
            }
            ref.set(payload)
            return _doc_to_user_dict(ref.get())

        return await asyncio.to_thread(_upsert)


def get_firebase_user_service() -> FirebaseUserService:
    """FirebaseUserService instance."""
    return FirebaseUserService()
