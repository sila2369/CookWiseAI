"""
Cart Router - Sepet API endpoint'leri
======================================

GET    /cart                  → Mevcut sepeti getir
POST   /cart/items            → Sepete ürün ekle
PUT    /cart/items/{id}       → Sepetteki ürünü güncelle
DELETE /cart/items/{id}       → Sepetten ürünü sil
DELETE /cart                  → Sepeti boşalt
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies.auth import get_active_user
from app.dependencies.services import get_required_database
from app.schemas.cart import CartItemAdd, CartItemUpdate, CartResponse
from app.services.cart_service import CartService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/cart",
    tags=["Cart"],
    responses={
        401: {"description": "Unauthorized"},
        404: {"description": "Not Found"},
    },
)


def get_cart_service(db=Depends(get_required_database)) -> CartService:
    """CartService dependency."""
    return CartService(db)


@router.get(
    "",
    response_model=CartResponse,
    summary="Mevcut kullanıcının sepetini getir",
    description="Giriş yapmış kullanıcının aktif sepetini ve canlı fiyat hesaplamasını döner."
)
async def get_cart(
    current_user=Depends(get_active_user),
    service: CartService = Depends(get_cart_service),
) -> CartResponse:
    user_id = current_user.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID missing in token")
    return await service.get_cart(user_id)


@router.post(
    "/items",
    response_model=CartResponse,
    summary="Sepete ürün ekle",
    description="Sepete yeni bir ürün ekler veya varsa miktarını artırır."
)
async def add_item_to_cart(
    item: CartItemAdd,
    current_user=Depends(get_active_user),
    service: CartService = Depends(get_cart_service),
) -> CartResponse:
    user_id = current_user.get("id")
    try:
        return await service.add_item(user_id, item)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put(
    "/items/{product_id}",
    response_model=CartResponse,
    summary="Sepetteki ürün miktarını güncelle",
    description="Mevcut bir ürünün miktarını günceller. Miktar 0 verilirse ürün silinir."
)
async def update_cart_item(
    product_id: str,
    update_data: CartItemUpdate,
    current_user=Depends(get_active_user),
    service: CartService = Depends(get_cart_service),
) -> CartResponse:
    user_id = current_user.get("id")
    try:
        return await service.update_item(user_id, product_id, update_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete(
    "/items/{product_id}",
    response_model=CartResponse,
    summary="Ürünü sepetten çıkar",
    description="Belirtilen ürünü sepetten tamamen siler."
)
async def remove_cart_item(
    product_id: str,
    current_user=Depends(get_active_user),
    service: CartService = Depends(get_cart_service),
) -> CartResponse:
    user_id = current_user.get("id")
    try:
        return await service.remove_item(user_id, product_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete(
    "",
    response_model=CartResponse,
    summary="Sepeti boşalt",
    description="Kullanıcının sepetindeki tüm ürünleri siler."
)
async def clear_cart(
    current_user=Depends(get_active_user),
    service: CartService = Depends(get_cart_service),
) -> CartResponse:
    user_id = current_user.get("id")
    return await service.clear_cart(user_id)
