"""Order request/response schemas."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.order import OrderStatus


class OrderCreate(BaseModel):
    """Create an order from the active cart."""

    delivery_address: str = Field(..., min_length=10, max_length=500, description="Delivery address")
    payment_method: str = Field("CASH_ON_DELIVERY", description="Payment method")
    contact_phone: Optional[str] = Field(None, min_length=10, max_length=30, description="Delivery contact phone")
    delivery_slot: Optional[str] = Field(None, max_length=120, description="Delivery time slot")
    delivery_note: Optional[str] = Field(None, max_length=300, description="Courier note")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "delivery_address": "Ornek Mah. 123 Sok. No:4 D:5 Kadikoy/Istanbul",
                "payment_method": "CASH_ON_DELIVERY",
                "contact_phone": "+905551112233",
                "delivery_slot": "Bugun 19:00-21:00",
                "delivery_note": "Zile basmayin.",
            }
        }
    )


class OrderStatusUpdate(BaseModel):
    """Admin order status update request."""

    status: OrderStatus = Field(..., description="New order status")

    model_config = ConfigDict(json_schema_extra={"example": {"status": "PREPARING"}})


class OrderItemSchema(BaseModel):
    """Locked product snapshot inside an order."""

    product_id: str
    name: str
    price: float
    quantity: int
    subtotal: float

    model_config = ConfigDict(from_attributes=True)


class OrderResponse(BaseModel):
    """Order API response."""

    id: str
    user_id: str
    status: OrderStatus
    items: List[OrderItemSchema]
    total_price: float
    delivery_address: str
    payment_method: str
    contact_phone: Optional[str] = None
    delivery_slot: Optional[str] = None
    delivery_note: Optional[str] = None
    created_at: datetime | str
    updated_at: datetime | str

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "674a1b2c3d4e5f6a7b8c9d0f",
                "user_id": "507f1f77bcf86cd799439011",
                "status": "PENDING",
                "items": [
                    {
                        "product_id": "674a1b2c3d4e5f6a7b8c9d0e",
                        "name": "Sut 1 Litre",
                        "price": 25.99,
                        "quantity": 2,
                        "subtotal": 51.98,
                    }
                ],
                "total_price": 51.98,
                "delivery_address": "Ornek Mah. 123 Sok. No:4 Kadikoy/Istanbul",
                "payment_method": "CASH_ON_DELIVERY",
                "contact_phone": "+905551112233",
                "delivery_slot": "Bugun 19:00-21:00",
                "delivery_note": "Zile basmayin.",
                "created_at": "2026-03-20T12:00:00",
                "updated_at": "2026-03-20T12:00:00",
            }
        },
    )


class OrderListResponse(BaseModel):
    """Order list response."""

    items: List[OrderResponse]
    total: int
