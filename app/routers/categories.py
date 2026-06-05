"""
Categories Router - Kategori API endpoint'leri
==============================================

POST /categories   → Admin only, yeni kategori
GET /categories    → Public, aktif kategoriler
GET /categories/{id} → Public, kategori detay
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.exceptions import DuplicateDocumentException
from app.dependencies.admin import get_admin_user
from app.dependencies.services import get_required_database
from app.schemas.category import CategoryCreate, CategoryResponse, CategoryListResponse
from app.services.category_service import CategoryService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/categories",
    tags=["Categories"],
    responses={
        404: {"description": "Category not found"},
        409: {"description": "Name or slug already exists"},
    },
)


def get_category_service(db=Depends(get_required_database)) -> CategoryService:
    """CategoryService dependency."""
    return CategoryService(db)


# ==================== POST /categories (Admin) ====================

@router.post(
    "",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Yeni kategori oluştur",
    description="Sadece admin. name veya slug benzersiz olmalı.",
    responses={
        201: {
            "description": "Kategori oluşturuldu",
            "content": {
                "application/json": {
                    "example": {
                        "id": "674a1b2c3d4e5f6a7b8c9d0e",
                        "name": "Yemek & İçecek",
                        "slug": "yemek-icecek",
                        "description": "Restoran siparişleri",
                        "image_url": None,
                        "is_active": True,
                        "created_at": "2026-03-20T12:00:00",
                        "updated_at": "2026-03-20T12:00:00",
                    }
                }
            },
        },
        409: {
            "description": "Name veya slug zaten kullanımda",
            "content": {
                "application/json": {
                    "example": {"detail": "Category with name 'Yemek' already exists"}
                }
            },
        },
    },
)
async def create_category(
    data: CategoryCreate,
    _admin=Depends(get_admin_user),
    service: CategoryService = Depends(get_category_service),
) -> CategoryResponse:
    """
    **Admin only.** Yeni kategori oluşturur.

    Request:
    ```json
    {
      "name": "Yemek & İçecek",
      "slug": "yemek-icecek",
      "description": "Restoran ve kafe siparişleri",
      "is_active": true
    }
    ```
    """
    try:
        return await service.create(data)
    except DuplicateDocumentException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.message)


# ==================== GET /categories (Public) ====================

@router.get(
    "",
    response_model=CategoryListResponse,
    summary="Aktif kategorileri listele",
    description="Herkes erişebilir. Sadece is_active=true kategoriler.",
    responses={
        200: {
            "description": "Kategori listesi",
            "content": {
                "application/json": {
                    "example": {
                        "items": [
                            {
                                "id": "674a1b2c3d4e5f6a7b8c9d0e",
                                "name": "Yemek & İçecek",
                                "slug": "yemek-icecek",
                                "description": "Restoran siparişleri",
                                "image_url": None,
                                "is_active": True,
                                "created_at": "2026-03-20T12:00:00",
                                "updated_at": "2026-03-20T12:00:00",
                            }
                        ],
                        "total": 1,
                        "skip": 0,
                        "limit": 50,
                    }
                }
            },
        },
    },
)
async def list_categories(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    service: CategoryService = Depends(get_category_service),
) -> CategoryListResponse:
    """
    Aktif kategorileri listeler. Auth gerekmez.

    Query: ?skip=0&limit=50
    """
    return await service.list_active(skip=skip, limit=limit)


# ==================== GET /categories/{category_id} (Public) ====================

@router.get(
    "/{category_id}",
    response_model=CategoryResponse,
    summary="Kategori detayı",
    description="ID ile kategori getirir.",
    responses={
        200: {
            "description": "Kategori bulundu",
        },
        404: {
            "description": "Kategori bulunamadı",
            "content": {
                "application/json": {
                    "example": {"detail": "Category not found"}
                }
            },
        },
    },
)
async def get_category(
    category_id: str,
    service: CategoryService = Depends(get_category_service),
) -> CategoryResponse:
    """
    Kategori detayını getirir. Auth gerekmez.
    """
    category = await service.get_by_id(category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )
    return category


# ==================== ÖRNEKLER ====================
#
# POST /categories (Admin, Bearer token gerekli):
#   curl -X POST http://localhost:8000/api/v1/categories \
#     -H "Authorization: Bearer <ADMIN_TOKEN>" \
#     -H "Content-Type: application/json" \
#     -d '{"name":"Yemek","slug":"yemek","description":"Restoran","is_active":true}'
#
# GET /categories (Public):
#   curl http://localhost:8000/api/v1/categories?skip=0&limit=50
#
# GET /categories/{id} (Public):
#   curl http://localhost:8000/api/v1/categories/674a1b2c3d4e5f6a7b8c9d0e
