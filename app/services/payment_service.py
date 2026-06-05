"""
Payment Service - Mock Ödeme İşlemleri
=======================================
Okul projesi simülasyonu için Luhn algoritması ile kart doğrulaması yapan ve
sipariş durumunu güncelleyen mock ödeme servisi.
"""

import logging
import uuid
from datetime import datetime
from bson import ObjectId

from app.models.order import Order, OrderStatus
from app.schemas.payment import CreditCardPaymentRequest, PaymentResponse
from app.schemas.order import OrderStatusUpdate
from app.services.order_service import OrderService

logger = logging.getLogger(__name__)


class MockPaymentService:
    """Mock (Sahte) Ödeme İşlemleri Servisi."""

    def __init__(self, db):
        if db is None:
            raise ValueError("Database connection is required")
        self.db = db
        self.orders = db[Order.COLLECTION]
        self.order_service = OrderService(db)

    @staticmethod
    def _luhn_check(card_number: str) -> bool:
        """
        Luhn Algoritması: Kredi kartı numarasının matematiksel geçerliliğini test eder.
        https://en.wikipedia.org/wiki/Luhn_algorithm
        """
        digits = [int(x) for x in str(card_number)]
        if len(digits) < 13:
            return False

        # Son rakamdan başlayıp sola doğru git
        checksum = 0
        is_second = False
        
        for d in reversed(digits):
            if is_second:
                d = d * 2
                if d > 9:
                    d -= 9
            checksum += d
            is_second = not is_second
            
        return checksum % 10 == 0

    @staticmethod
    def _is_card_expired(exp_month: int, exp_year: int) -> bool:
        """Kartın son kullanma tarihinin geçip geçmediğini kontrol eder."""
        now = datetime.now()
        current_year = now.year
        current_month = now.month

        if exp_year < current_year:
            return True
        if exp_year == current_year and exp_month < current_month:
            return True
        return False

    async def process_payment(self, user_id: str, order_id: str, payment_data: CreditCardPaymentRequest) -> PaymentResponse:
        """Ödeme işlemini simüle eder ve başarılı olursa sipariş durumunu PREPARING yapar."""
        
        # 1. Siparişi bul ve kontrol et
        try:
            oid = ObjectId(order_id)
            uid = ObjectId(user_id)
        except Exception:
            raise ValueError("Invalid ID format")

        order = await self.orders.find_one({"_id": oid, "user_id": uid})
        if not order:
            raise ValueError("Order not found or does not belong to you")

        if order.get("status") != OrderStatus.PENDING.value:
            raise ValueError(f"Order cannot be paid. Current status: {order.get('status')}")

        amount = float(order.get("total_price", 0.0))
        if amount <= 0:
            raise ValueError("Invalid order amount")

        # 2. Luhn Algoritması ile kart numarası kontrolü
        if not self._luhn_check(payment_data.card_number):
            raise ValueError("Invalid credit card number (Failed Luhn check)")

        # 3. Son kullanma tarihi kontrolü
        if self._is_card_expired(payment_data.exp_month, payment_data.exp_year):
            raise ValueError("Credit card is expired")

        # 4. Mock Ödeme İşlemi Başarılı
        transaction_id = f"TXN-{uuid.uuid4().hex[:12].upper()}"
        logger.info(f"Payment successful for order {order_id}. Amount: {amount}, TXN: {transaction_id}")

        # 5. Sipariş durumunu güncelle (PREPARING - Hazırlanıyor)
        # Önce siparişin payment_method'unu da güncelleyelim.
        await self.orders.update_one(
            {"_id": oid},
            {
                "$set": {
                    "status": OrderStatus.PREPARING.value,
                    "payment_method": "CREDIT_CARD",
                    "updated_at": datetime.utcnow()
                }
            }
        )

        return PaymentResponse(
            success=True,
            transaction_id=transaction_id,
            message="Payment completed successfully.",
            paid_amount=amount,
            payment_time=datetime.utcnow().isoformat()
        )
