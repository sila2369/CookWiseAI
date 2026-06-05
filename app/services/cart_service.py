"""
Cart Service - Sepet iş mantığı
================================

Sepet oluşturma, ürün ekleme, çıkarma ve canlı fiyat hesaplama.
"""

import logging
from datetime import datetime
from typing import Optional, List
from bson import ObjectId

from app.core.exceptions import DatabaseConnectionException
from app.models.cart import Cart
from app.models.product import Product
from app.schemas.cart import CartItemAdd, CartItemUpdate, CartResponse, CartItemResponse

logger = logging.getLogger(__name__)

def _normalize_user_id(user_id: str):
    try:
        return ObjectId(user_id)
    except Exception:
        return user_id


class CartService:
    """Sepet işlemleri ve hesaplamaları."""

    def __init__(self, db):
        if db is None:
            raise ValueError("Database connection is required")
        self.db = db
        self.carts = db[Cart.COLLECTION]
        self.products = db[Product.COLLECTION]

    async def _get_or_create_cart(self, user_id: str) -> dict:
        """Kullanıcının sepetini getirir, yoksa oluşturur (MongoDB objesi)."""
        uid = _normalize_user_id(user_id)
        cart = await self.carts.find_one({"user_id": uid})
        if not cart:
            cart = Cart.create_document(user_id)
            result = await self.carts.insert_one(cart)
            cart["_id"] = result.inserted_id
        return cart

    async def _build_cart_response(self, cart: dict) -> CartResponse:
        """MongoDB cart objesini alır, ürünlerin güncel fiyatlarıyla hesaplayıp CartResponse döner."""
        items = cart.get("items", [])
        
        # Product ID'lerini topla
        product_ids = [item["product_id"] for item in items]
        
        # Ürünleri MongoDB'den tek sorguda çek
        # Sadece aktif ve stokta olan ürünleri sepette tut.
        products_cursor = self.products.find(
            {
                "_id": {"$in": product_ids},
                "is_active": True,
                "stock": {"$gt": 0},
                "image_url": {"$nin": [None, ""]},
            }
        )
        products_map = {str(p["_id"]): p async for p in products_cursor}

        response_items: List[CartItemResponse] = []
        total_price = 0.0
        normalized_items = []

        def campaign_price(product_data: dict, quantity: int) -> tuple[float, float, str | None]:
            base_price = float(product_data.get("price", 0.0))
            if not product_data.get("is_promoted"):
                return base_price, base_price * quantity, None

            label = product_data.get("promotion_label")
            if product_data.get("promotion_type") == "discount_price" and product_data.get("discounted_price") is not None:
                unit_price = float(product_data.get("discounted_price") or base_price)
                return unit_price, unit_price * quantity, label

            if product_data.get("promotion_type") == "buy_x_pay_y":
                buy_qty = int(product_data.get("promotion_buy_quantity") or 0)
                pay_qty = int(product_data.get("promotion_pay_quantity") or 0)
                if buy_qty > 0 and pay_qty > 0 and pay_qty <= buy_qty:
                    groups = quantity // buy_qty
                    remainder = quantity % buy_qty
                    charged_quantity = groups * pay_qty + remainder
                    return base_price, base_price * charged_quantity, label

            return base_price, base_price * quantity, label
        
        # Sadece hala aktif/var olan ürünleri yanıta ekle (fiyat güncel)
        for item in items:
            p_id_str = str(item["product_id"])
            if p_id_str in products_map:
                product_data = products_map[p_id_str]
                image_url = product_data.get("image_url")
                if not image_url:
                    continue
                qty = item["quantity"]
                price, subtotal, promotion_label = campaign_price(product_data, qty)
                total_price += subtotal
                normalized_items.append(
                    {
                        "product_id": item["product_id"],
                        "quantity": qty,
                    }
                )
                
                response_items.append(CartItemResponse(
                    product_id=p_id_str,
                    name=product_data.get("name", "Bilinmeyen Ürün"),
                    price=price,
                    image_url=image_url,
                    quantity=qty,
                    subtotal=round(subtotal, 2),
                    original_price=float(product_data.get("price", 0.0)),
                    promotion_label=promotion_label,
                ))

        # Stokta olmayan/aktif olmayan ürünler sepetten otomatik temizlensin.
        if len(normalized_items) != len(items):
            await self.carts.update_one(
                {"_id": cart["_id"]},
                {"$set": {"items": normalized_items, "updated_at": datetime.utcnow()}},
            )

        d = Cart.mongo_to_dict(cart)
        return CartResponse(
            id=d["id"],
            user_id=d["user_id"],
            items=response_items,
            total_price=round(total_price, 2),
            updated_at=d["updated_at"]
        )

    async def get_cart(self, user_id: str) -> CartResponse:
        """Kullanıcının sepetini getirir (canlı hesaplama)."""
        cart = await self._get_or_create_cart(user_id)
        return await self._build_cart_response(cart)

    async def add_item(self, user_id: str, item_data: CartItemAdd) -> CartResponse:
        """Sepete ürün ekler. Varsa miktarını artırır."""
        cart = await self._get_or_create_cart(user_id)
        
        try:
            pid = ObjectId(item_data.product_id)
        except Exception:
            raise ValueError(f"Invalid product_id: {item_data.product_id}")
            
        # Ürün geçerli mi ve aktif mi kontrol et
        product = await self.products.find_one({"_id": pid, "is_active": True})
        if not product:
            raise ValueError("Product not found or inactive")
        if not product.get("image_url"):
            raise ValueError("Product image is missing. This item cannot be added to cart.")
            
        # Stok kontrolü (opsiyonel, genelde sipariş anında kesin yapılır ama burada da uyarılabilir)
        if product.get("stock", 0) < item_data.quantity:
            raise ValueError(f"Not enough stock. Available: {product.get('stock', 0)}")

        items = cart.get("items", [])
        found = False
        
        for item in items:
            if item["product_id"] == pid:
                # Sepette zaten var, miktarı artır
                yeni_miktar = item["quantity"] + item_data.quantity
                if product.get("stock", 0) < yeni_miktar:
                    raise ValueError(f"Not enough stock for total quantity {yeni_miktar}.")
                item["quantity"] = yeni_miktar
                found = True
                break
                
        if not found:
            # Sepette yok, yeni ekle
            items.append({
                "product_id": pid,
                "quantity": item_data.quantity
            })

        await self.carts.update_one(
            {"_id": cart["_id"]},
            {"$set": {"items": items, "updated_at": datetime.utcnow()}}
        )
        
        # Güncel halini çek ve dön
        updated_cart = await self.carts.find_one({"_id": cart["_id"]})
        return await self._build_cart_response(updated_cart)

    async def update_item(self, user_id: str, product_id: str, update_data: CartItemUpdate) -> CartResponse:
        """Sepetteki ürünün miktarını günceller. Miktar 0 ise ürünü siler."""
        cart = await self._get_or_create_cart(user_id)
        
        try:
            pid = ObjectId(product_id)
        except Exception:
            raise ValueError(f"Invalid product_id: {product_id}")

        items = cart.get("items", [])
        new_items = []
        found = False

        for item in items:
            if item["product_id"] == pid:
                found = True
                if update_data.quantity > 0:
                    # Stok kontrolü
                    product = await self.products.find_one({"_id": pid, "is_active": True})
                    if product and product.get("stock", 0) < update_data.quantity:
                        raise ValueError(f"Not enough stock. Available: {product.get('stock', 0)}")
                    new_items.append({"product_id": pid, "quantity": update_data.quantity})
                # quantity == 0 ise new_items'a eklemeyiz, yani silinmiş olur.
            else:
                new_items.append(item)

        if not found and update_data.quantity > 0:
            raise ValueError("Item not found in cart")

        await self.carts.update_one(
            {"_id": cart["_id"]},
            {"$set": {"items": new_items, "updated_at": datetime.utcnow()}}
        )

        updated_cart = await self.carts.find_one({"_id": cart["_id"]})
        return await self._build_cart_response(updated_cart)

    async def remove_item(self, user_id: str, product_id: str) -> CartResponse:
        """Ürünü sepetten tamamen siler."""
        cart = await self._get_or_create_cart(user_id)
        
        try:
            pid = ObjectId(product_id)
        except Exception:
            raise ValueError(f"Invalid product_id: {product_id}")

        items = cart.get("items", [])
        new_items = [item for item in items if item["product_id"] != pid]

        await self.carts.update_one(
            {"_id": cart["_id"]},
            {"$set": {"items": new_items, "updated_at": datetime.utcnow()}}
        )

        updated_cart = await self.carts.find_one({"_id": cart["_id"]})
        return await self._build_cart_response(updated_cart)

    async def clear_cart(self, user_id: str) -> CartResponse:
        """Sepeti tamamen boşaltır."""
        cart = await self._get_or_create_cart(user_id)
        
        await self.carts.update_one(
            {"_id": cart["_id"]},
            {"$set": {"items": [], "updated_at": datetime.utcnow()}}
        )

        updated_cart = await self.carts.find_one({"_id": cart["_id"]})
        return await self._build_cart_response(updated_cart)
