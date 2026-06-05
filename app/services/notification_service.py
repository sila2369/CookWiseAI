"""
Notification Service - Anlık Bildirim (Push Notification) Yönetimi
===================================================================
Firebase Cloud Messaging (FCM) kullanarak cihazlara bildirim gönderir.
"""

import logging
import asyncio
from datetime import datetime
from typing import List, Optional
from bson import ObjectId

logger = logging.getLogger(__name__)


class NotificationService:
    """Bildirim (Push Notification) işlemleri."""

    def __init__(self, db):
        self.db = db
        self.users = db["users"]
        self.notifications = db["notifications"]

    async def create_campaign_notification(
        self,
        product_id: ObjectId,
        product_name: str,
        promotion_label: Optional[str],
        audience: str = "all",
    ) -> None:
        """Create an in-app notification shown in the user's notification box."""
        now = datetime.utcnow()
        title = "Yeni kampanya var"
        label = promotion_label or "Kampanyali urun"
        body = f"{product_name} icin {label} kampanyasi basladi."
        dedupe_key = f"campaign:{str(product_id)}:{label.lower().strip()}"

        await self.notifications.update_one(
            {"dedupe_key": dedupe_key},
            {
                "$set": {
                    "title": title,
                    "body": body,
                    "type": "campaign",
                    "audience": audience,
                    "product_id": product_id,
                    "product_name": product_name,
                    "promotion_label": label,
                    "is_active": True,
                    "updated_at": now,
                },
                "$setOnInsert": {
                    "dedupe_key": dedupe_key,
                    "created_at": now,
                    "read_by": [],
                },
            },
            upsert=True,
        )

    async def send_discount_notification(self, product_name: str, old_price: float, new_price: float, user_ids: List[ObjectId]) -> None:
        """
        Favorilerinde olan ürüne indirim geldiğinde kullanıcılara bildirim yollar.
        """
        if not user_ids:
            return

        discount_percent = int(((old_price - new_price) / old_price) * 100)
        title = "Favori Ürününde İndirim! 🎉"
        body = f"Kaçırma! Favorilerindeki '{product_name}' ürününde %{discount_percent} indirim yapıldı. Yeni fiyat: {new_price} TL"

        # Kullanıcıların FCM token'larını çek
        cursor = self.users.find(
            {"_id": {"$in": user_ids}, "fcm_tokens": {"$exists": True, "$not": {"$size": 0}}},
            {"fcm_tokens": 1}
        )

        all_tokens = []
        async for user in cursor:
            tokens = user.get("fcm_tokens", [])
            all_tokens.extend(tokens)

        if not all_tokens:
            logger.info("Bildirim gönderilecek aktif FCM token bulunamadı.")
            return

        # Firebase Admin SDK yüklü mü kontrol et (Gevşek kontrol)
        try:
            from firebase_admin import messaging
            import firebase_admin
            
            # App baslatilmis mi?
            if not firebase_admin._apps:
                logger.warning(f"[MOCK PUSH] Firebase başlatılmamış. Bildirim loglandı: {title} -> {len(all_tokens)} cihaza gönderildi.")
                return

            # Bildirim objesini oluştur
            message = messaging.MulticastMessage(
                notification=messaging.Notification(
                    title=title,
                    body=body
                ),
                tokens=all_tokens
            )

            # Asenkron gönderme işlemi (thread içerisinde)
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, messaging.send_multicast, message)
            
            logger.info(f"FCM Bildirimi başarıyla {response.success_count} cihaza iletildi, {response.failure_count} başarısız.")

        except ImportError:
            logger.warning(f"[MOCK PUSH] firebase_admin kütüphanesi yok. Bildirim loglandı: {title} -> {len(all_tokens)} cihaza.")
        except Exception as e:
            logger.error(f"FCM Bildirimi gönderirken hata oluştu: {str(e)}")
