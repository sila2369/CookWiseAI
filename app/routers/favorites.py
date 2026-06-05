"""
Favorites Router - Favoriler API endpoint'leri
===============================================

GET    /favorites               → Favorilerimi listele
POST   /favorites/{product_id}  → Ürünü favorilere ekle
DELETE /favorites/{product_id}  → Ürünü favorilerden çıkar
"""

import logging
from fastapi import APIRouter, Depends, HTTPException

from app.dependencies.auth import get_active_user
from app.dependencies.services import get_required_database
from app.schemas.favorite import FavoriteResponse
from app.services.favorite_service import FavoriteService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/favorites",
    tags=["Favorites"],
    responses={
        401: {"description": "Unauthorized"},
        404: {"description": "Not Found"},
    },
)


def get_favorite_service(db=Depends(get_required_database)) -> FavoriteService:
    """FavoriteService dependency."""
    return FavoriteService(db)


@router.get(
    "",
    response_model=FavoriteResponse,
    summary="Favorilerimi listele",
    description="Giriş yapmış kullanıcının favori ürünlerini canlı detaylarıyla getirir."
)
async def get_my_favorites(
    current_user=Depends(get_active_user),
    service: FavoriteService = Depends(get_favorite_service),
) -> FavoriteResponse:
    user_id = current_user.get("id")
    try:
        return await service.get_favorites(user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/{product_id}",
    response_model=FavoriteResponse,
    summary="Favorilere ürün ekle",
    description="Belirtilen ürünü kullanıcının favoriler listesine ekler."
)
async def add_to_favorites(
    product_id: str,
    current_user=Depends(get_active_user),
    service: FavoriteService = Depends(get_favorite_service),
) -> FavoriteResponse:
    user_id = current_user.get("id")
    try:
        return await service.add_favorite(user_id, product_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete(
    "/{product_id}",
    response_model=FavoriteResponse,
    summary="Favorilerden ürün çıkar",
    description="Belirtilen ürünü kullanıcının favoriler listesinden çıkarır."
)
async def remove_from_favorites(
    product_id: str,
    current_user=Depends(get_active_user),
    service: FavoriteService = Depends(get_favorite_service),
) -> FavoriteResponse:
    user_id = current_user.get("id")
    try:
        return await service.remove_favorite(user_id, product_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
