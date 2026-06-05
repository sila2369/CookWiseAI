"""
Orders Router - Sipariş API endpoint'leri
==========================================

POST   /orders                → Sepeti siparişe dönüştür
GET    /orders                → Kendi siparişlerini listele
GET    /orders/{id}           → Sipariş detayı gör
PUT    /orders/{id}/status    → (Admin) Sipariş durumu güncelle
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies.auth import get_active_user
from app.dependencies.admin import get_admin_user
from app.dependencies.services import get_required_database
from app.schemas.order import OrderCreate, OrderStatusUpdate, OrderResponse, OrderListResponse
from app.schemas.payment import CreditCardPaymentRequest, PaymentResponse
from app.services.order_service import OrderService
from app.services.payment_service import MockPaymentService
from app.models.order import OrderStatus

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/orders",
    tags=["Orders"],
    responses={
        401: {"description": "Unauthorized"},
        404: {"description": "Not Found"},
    },
)


def get_order_service(db=Depends(get_required_database)) -> OrderService:
    """OrderService dependency."""
    return OrderService(db)


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Yeni sipariş oluştur",
    description="Aktif sepeti siparişe dönüştürür. Stokları düşer ve sepeti boşaltır."
)
async def create_order(
    data: OrderCreate,
    current_user=Depends(get_active_user),
    service: OrderService = Depends(get_order_service),
) -> OrderResponse:
    user_id = current_user.get("id")
    try:
        return await service.create_order(user_id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "",
    response_model=OrderListResponse,
    summary="Siparişlerimi listele",
    description="Giriş yapmış kullanıcının geçmiş siparişlerini getirir."
)
async def list_my_orders(
    current_user=Depends(get_active_user),
    service: OrderService = Depends(get_order_service),
) -> OrderListResponse:
    user_id = current_user.get("id")
    return await service.get_user_orders(user_id)


@router.get(
    "/admin/all",
    response_model=OrderListResponse,
    summary="Tüm siparişleri listele (Admin)",
    description="Admin yetkisiyle tüm kullanıcıların siparişlerini listeler.",
)
async def list_all_orders(
    _admin=Depends(get_admin_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status_filter: OrderStatus | None = Query(None, alias="status"),
    service: OrderService = Depends(get_order_service),
) -> OrderListResponse:
    return await service.get_all_orders(skip=skip, limit=limit, status=status_filter)


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    summary="Sipariş detayını getir",
    description="Belirtilen siparişi getirir. Kullanıcı sadece kendi siparişini görebilir."
)
async def get_order(
    order_id: str,
    current_user=Depends(get_active_user),
    service: OrderService = Depends(get_order_service),
) -> OrderResponse:
    user_id = current_user.get("id")
    is_admin = current_user.get("is_admin", False)
    
    try:
        order = await service.get_order_by_id(order_id, user_id, is_admin)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    if not order:
        raise HTTPException(status_code=404, detail="Order not found or access denied")
        
    return order


@router.put(
    "/{order_id}/status",
    response_model=OrderResponse,
    summary="Sipariş durumunu güncelle (Admin)",
    description="Admin yetkisi olan kullanıcılar siparişin durumunu güncelleyebilir."
)
async def update_order_status(
    order_id: str,
    new_status: OrderStatusUpdate,
    _admin=Depends(get_admin_user),
    service: OrderService = Depends(get_order_service),
) -> OrderResponse:
    try:
        order = await service.update_order_status(order_id, new_status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    return order


def get_payment_service(db=Depends(get_required_database)) -> MockPaymentService:
    """MockPaymentService dependency."""
    return MockPaymentService(db)


@router.post(
    "/{order_id}/pay",
    response_model=PaymentResponse,
    summary="Sipariş için Kredi Kartı ile Ödeme Yap (Mock)",
    description="Luhn algoritması ile kart doğrulaması yapan simüle edilmiş ödeme noktası. Başarılı olursa sipariş durumu PREPARING olur."
)
async def pay_for_order(
    order_id: str,
    payment_data: CreditCardPaymentRequest,
    current_user=Depends(get_active_user),
    service: MockPaymentService = Depends(get_payment_service),
) -> PaymentResponse:
    user_id = current_user.get("id")
    try:
        return await service.process_payment(user_id, order_id, payment_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
