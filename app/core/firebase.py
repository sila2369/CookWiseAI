"""
Firebase Başlatma
=================

Firebase Admin SDK ile Auth ve Firestore bağlantısı.
Kullanıcılar Firebase'de tutulacaksa bu modül initialize edilir.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Firebase app instance (lazy init)
_firebase_app = None


def get_firebase_app():
    """Firebase Admin app instance'ını döner. Henüz init edilmediyse None."""
    return _firebase_app


def init_firebase(credentials_path: str, project_id: Optional[str] = None) -> bool:
    """
    Firebase Admin SDK'yı başlatır.
    
    Args:
        credentials_path: Service Account JSON dosya yolu
        project_id: Firebase proje ID (opsiyonel, JSON'da varsa gerekmez)
    
    Returns:
        bool: Başarılıysa True
    """
    global _firebase_app
    
    try:
        import firebase_admin
        from firebase_admin import credentials
        
        # Zaten init edilmiş mi?
        if _firebase_app is not None:
            logger.debug("Firebase zaten baslatilmis")
            return True
        
        cred = credentials.Certificate(credentials_path)
        options = {}
        if project_id:
            options["project_id"] = project_id
        
        _firebase_app = firebase_admin.initialize_app(cred, options)
        logger.info("Firebase Admin SDK basariyla baslatildi")
        return True
        
    except FileNotFoundError as e:
        logger.error(f"Firebase credentials dosyasi bulunamadi: {credentials_path} - {e}")
        return False
    except Exception as e:
        logger.error(f"Firebase init hatasi: {e}")
        return False


def is_firebase_enabled() -> bool:
    """Firebase kullanıcı yönetimi için etkin mi?"""
    from app.core.config import settings
    return bool(
        settings.USE_FIREBASE_AUTH
        and settings.FIREBASE_CREDENTIALS_PATH
    )
