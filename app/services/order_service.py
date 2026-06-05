"""
Order Service - Sipariş iş mantığı
===================================
Sepetten sipariş oluşturma, stok düşme ve durum güncelleme.
"""

import logging
from datetime import datetime
from typing import Optional, List
from bson import ObjectId

from app.models.cart import Cart
from app.models.order import Order, OrderStatus
from app.models.product import Product
from app.schemas.order import OrderCreate, OrderStatusUpdate, OrderResponse, OrderListResponse
from app.services.cart_service import CartService

logger = logging.getLogger(__name__)

def _normalize_user_id(user_id: str):
    try:
        return ObjectId(user_id)
    except Exception:
        return user_id


class OrderService:
    """Sipariş işlemleri."""

    def __init__(self, db):
        if db is None:
            raise ValueError("Database connection is required")
        self.db = db
        self.orders = db[Order.COLLECTION]
        self.products = db[Product.COLLECTION]
        self.carts = db[Cart.COLLECTION]
        self.cart_service = CartService(db)

    async def create_order(self, user_id: str, data: OrderCreate) -> OrderResponse:
        """Kullanıcının sepetini kullanarak sipariş oluşturur."""
        # 1. Sepeti ve güncel hesaplanmış fiyatları getir
        cart_response = await self.cart_service.get_cart(user_id)
        
        if not cart_response.items:
            raise ValueError("Cart is empty. Cannot create order.")

        # 2. Ürün stoklarını kontrol et ve kilitlenecek öğeleri (items) hazırla
        order_items = []
        product_updates = []  # Stok düşümü için
        
        for cart_item in cart_response.items:
            # Sepet servisimiz stok kontrolü yapsa da eşzamanlı istekler için DB'den son duruma bakalım
            product = await self.products.find_one({"_id": ObjectId(cart_item.product_id), "is_active": True})
            if not product:
                raise ValueError(f"Product '{cart_item.name}' is no longer available.")
            
            if product.get("stock", 0) < cart_item.quantity:
                raise ValueError(f"Not enough stock for product '{cart_item.name}'. Available: {product.get('stock', 0)}")
            
            # Siparişteki ürün fiyatları sipariş anında kilitlenir
            order_items.append({
                "product_id": ObjectId(cart_item.product_id),
                "name": cart_item.name,
                "price": cart_item.price,
                "quantity": cart_item.quantity,
                "subtotal": cart_item.subtotal
            })
            
            # Stok düşürmek için eylemleri hazırla
            new_stock = product.get("stock", 0) - cart_item.quantity
            product_updates.append((ObjectId(cart_item.product_id), new_stock))

        # 3. Sipariş dokümanını oluştur ve kaydet
        doc = Order.create_document(
            user_id=user_id,
            items=order_items,
            total_price=cart_response.total_price,
            delivery_address=data.delivery_address,
            payment_method=data.payment_method,
            contact_phone=data.contact_phone,
            delivery_slot=data.delivery_slot,
            delivery_note=data.delivery_note,
        )
        
        result = await self.orders.insert_one(doc)
        doc["_id"] = result.inserted_id

        # 4. Ürün stoklarını güncelle
        for pid, new_stock in product_updates:
            await self.products.update_one(
                {"_id": pid},
                {"$set": {"stock": new_stock, "updated_at": datetime.utcnow()}}
            )

        # 5. Sepeti temizle
        await self.cart_service.clear_cart(user_id)

        # 6. Yanıt dön
        return OrderResponse(**Order.dict_to_response(doc))

    async def get_user_orders(self, user_id: str) -> OrderListResponse:
        """Kullanıcının kendi siparişlerini getirir."""
        uid = _normalize_user_id(user_id)

        cursor = self.orders.find({"user_id": uid}).sort("created_at", -1)
        
        items = []
        async for doc in cursor:
            items.append(OrderResponse(**Order.dict_to_response(doc)))
            
        return OrderListResponse(items=items, total=len(items))

    async def get_all_orders(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[OrderStatus] = None,
    ) -> OrderListResponse:
        """Admin için tüm siparişleri listeler."""
        query = {}
        if status is not None:
            query["status"] = status.value

        cursor = self.orders.find(query).sort("created_at", -1).skip(skip).limit(limit)

        items = []
        async for doc in cursor:
            items.append(OrderResponse(**Order.dict_to_response(doc)))

        total = await self.orders.count_documents(query)
        return OrderListResponse(items=items, total=total)

    async def get_order_by_id(self, order_id: str, user_id: Optional[str] = None, is_admin: bool = False) -> Optional[OrderResponse]:
        """Siparişi ID'ye göre getirir. Kullanıcı sadece kendi siparişini, admin herkesinkini görebilir."""
        try:
            oid = ObjectId(order_id)
        except Exception:
            raise ValueError(f"Invalid order_id: {order_id}")

        query = {"_id": oid}
        if not is_admin and user_id:
            query["user_id"] = _normalize_user_id(user_id)

        doc = await self.orders.find_one(query)
        if not doc:
            return None
            
        return OrderResponse(**Order.dict_to_response(doc))

    async def update_order_status(self, order_id: str, new_status: OrderStatusUpdate) -> Optional[OrderResponse]:
        """Siparişin durumunu günceller (Sadece admin yetkisi varsayımıyla kullanılır)."""
        try:
            oid = ObjectId(order_id)
        except Exception:
            raise ValueError(f"Invalid order_id: {order_id}")

        doc = await self.orders.find_one({"_id": oid})
        if not doc:
            return None

        # Eğer iptal ediliyorsa ve önceki durum iptal değilse, stokları geri iade edebiliriz
        if new_status.status == OrderStatus.CANCELLED and doc.get("status") != OrderStatus.CANCELLED.value:
            for item in doc.get("items", []):
                pid = item.get("product_id")
                qty = item.get("quantity")
                if pid and qty:
                    # Stoku geri ekle
                    await self.products.update_one(
                        {"_id": ObjectId(pid)},
                        {"$inc": {"stock": qty}, "$set": {"updated_at": datetime.utcnow()}}
                    )

        await self.orders.update_one(
            {"_id": oid},
            {"$set": {"status": new_status.status.value, "updated_at": datetime.utcnow()}}
        )

        updated_doc = await self.orders.find_one({"_id": oid})
        try:
            from app.services.notification_service import NotificationService

            notifier = NotificationService(self.db)
            user_id = str(updated_doc.get("user_id") or doc.get("user_id") or "")
            await notifier.notifications.insert_one(
                {
                    "title": "Siparis durumu guncellendi",
                    "body": f"Siparisinizin yeni durumu: {new_status.status.value}.",
                    "type": "order",
                    "audience": "user",
                    "user_id": user_id,
                    "order_id": str(oid),
                    "is_active": True,
                    "read_by": [],
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                }
            )
        except Exception as e:
            logger.error(f"Error creating order status notification: {e}")
        return OrderResponse(**Order.dict_to_response(updated_doc))
