"""
Products Router - Ürün API endpoint'leri
=========================================

POST   /products       → Admin only, yeni ürün
GET    /products       → Public, aktif ürünler
GET    /products/{id}  → Public, ürün detayı
PUT    /products/{id}  → Admin only, ürün güncelle
DELETE /products/{id}  → Admin only, soft delete (is_active=False)
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.exceptions import DuplicateDocumentException
from app.dependencies.admin import get_admin_user
from app.dependencies.services import get_required_database
from app.schemas.product import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductListResponse,
)
from app.services.product_service import ProductService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/products",
    tags=["Products"],
    responses={
        404: {"description": "Category not found"},
        409: {"description": "Slug already exists"},
    },
)


def get_product_service(db=Depends(get_required_database)) -> ProductService:
    """ProductService dependency."""
    return ProductService(db)


# ==================== POST /products (Admin) ====================

@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Yeni ürün oluştur",
    description="Sadece admin. category_id geçerli olmalı, slug benzersiz olmalı.",
    responses={
        201: {
            "description": "Ürün oluşturuldu",
            "content": {
                "application/json": {
                    "example": {
                        "id": "674a1b2c3d4e5f6a7b8c9d0f",
                        "name": "Süt 1 Litre",
                        "slug": "sut-1-litre",
                        "description": "Günlük süt, 1 litre",
                        "price": 25.99,
                        "stock": 100,
                        "image_url": "https://example.com/sut.jpg",
                        "category_id": "674a1b2c3d4e5f6a7b8c9d0e",
                        "brand": "Pınar",
                        "unit": "litre",
                        "is_active": True,
                        "created_at": "2026-03-20T12:00:00",
                        "updated_at": "2026-03-20T12:00:00",
                    }
                }
            },
        },
        404: {
            "description": "category_id geçersiz",
            "content": {
                "application/json": {
                    "example": {"detail": "Category with id '...' not found"}
                }
            },
        },
        409: {
            "description": "Slug zaten kullanımda",
            "content": {
                "application/json": {
                    "example": {"detail": "Product slug 'sut-1-litre' is already in use"}
                }
            },
        },
    },
)
async def create_product(
    data: ProductCreate,
    _admin=Depends(get_admin_user),
    service: ProductService = Depends(get_product_service),
) -> ProductResponse:
    """
    **Admin only.** Yeni ürün oluşturur.

    Request:
    ```json
    {
      "name": "Süt 1 Litre",
      "slug": "sut-1-litre",
      "description": "Günlük süt",
      "price": 25.99,
      "stock": 100,
      "category_id": "674a1b2c3d4e5f6a7b8c9d0e",
      "brand": "Pınar",
      "unit": "litre",
      "is_active": true
    }
    ```
    """
    try:
        return await service.create(data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DuplicateDocumentException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.message)


# ==================== GET /products (Public) ====================

@router.get(
    "",
    response_model=ProductListResponse,
    summary="Aktif ürünleri listele",
    description="Herkes erişebilir. Sadece is_active=true ürünler.",
    responses={
        200: {
            "description": "Ürün listesi",
            "content": {
                "application/json": {
                    "example": {
                        "items": [
                            {
                                "id": "674a1b2c3d4e5f6a7b8c9d0f",
                                "name": "Süt 1 Litre",
                                "slug": "sut-1-litre",
                                "description": "Günlük süt",
                                "price": 25.99,
                                "stock": 100,
                                "image_url": None,
                                "category_id": "674a1b2c3d4e5f6a7b8c9d0e",
                                "brand": "Pınar",
                                "unit": "litre",
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
async def list_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    category_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    service: ProductService = Depends(get_product_service),
) -> ProductListResponse:
    """
    Aktif ürünleri listeler. Auth gerekmez.

    Filtreler:
    - category_id: Kategoriye göre
    - search: name veya description'da arama
    - min_price, max_price: Fiyat aralığı
    """
    return await service.list_active(
        skip=skip,
        limit=limit,
        category_id=category_id,
        search=search,
        min_price=min_price,
        max_price=max_price,
    )


# ==================== GET /products/{product_id} (Public) ====================

@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Ürün detayı",
    description="ID ile ürün getirir. Aktif olmayan ürün 404 döner.",
    responses={
        200: {
            "description": "Ürün bulundu",
        },
        404: {
            "description": "Ürün bulunamadı",
            "content": {
                "application/json": {
                    "example": {"detail": "Product not found"}
                }
            },
        },
    },
)
async def get_product(
    product_id: str,
    service: ProductService = Depends(get_product_service),
) -> ProductResponse:
    """
    Ürün detayını getirir. Auth gerekmez.
    """
    product = await service.get_by_id(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    return product


# ==================== PUT /products/{product_id} (Admin) ====================

@router.put(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Ürün güncelle",
    description="Sadece admin. category_id ve slug çakışması kontrol edilir.",
    responses={
        200: {
            "description": "Ürün güncellendi",
        },
        404: {
            "description": "Ürün bulunamadı veya category_id geçersiz",
            "content": {
                "application/json": {
                    "example": {"detail": "Product not found"}
                }
            },
        },
        409: {
            "description": "Slug zaten kullanımda",
            "content": {
                "application/json": {
                    "example": {"detail": "Product slug 'sut-1-litre' is already in use"}
                }
            },
        },
    },
)
async def update_product(
    product_id: str,
    data: ProductUpdate,
    _admin=Depends(get_admin_user),
    service: ProductService = Depends(get_product_service),
) -> ProductResponse:
    """
    **Admin only.** Ürün alanlarını günceller.

    Request (tüm alanlar opsiyonel):
    ```json
    {
      "name": "Süt 1 Litre",
      "price": 26.50,
      "stock": 50,
      "category_id": "674a1b2c3d4e5f6a7b8c9d0e",
      "is_active": true
    }
    ```
    """
    try:
        product = await service.update(product_id, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DuplicateDocumentException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.message)

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    return product


# ==================== DELETE /products/{product_id} (Admin) ====================

@router.delete(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Ürünü sil (soft delete)",
    description="Sadece admin. is_active=False yapar, veri silinmez.",
    responses={
        200: {
            "description": "Ürün soft delete edildi",
        },
        404: {
            "description": "Ürün bulunamadı",
            "content": {
                "application/json": {
                    "example": {"detail": "Product not found"}
                }
            },
        },
    },
)
async def delete_product(
    product_id: str,
    _admin=Depends(get_admin_user),
    service: ProductService = Depends(get_product_service),
) -> ProductResponse:
    """
    **Admin only.** Ürünü soft delete eder (is_active=False).
    """
    product = await service.soft_delete(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    return product


# ==================== ÖRNEKLER ====================
#
# POST /products (Admin, Bearer token gerekli):
#   curl -X POST http://localhost:8000/api/v1/products \
#     -H "Authorization: Bearer <ADMIN_TOKEN>" \
#     -H "Content-Type: application/json" \
#     -d '{"name":"Süt 1L","slug":"sut-1l","description":"Günlük süt","price":25.99,"stock":100,"category_id":"674a1b2c3d4e5f6a7b8c9d0e"}'
#
# GET /products (Public):
#   curl "http://localhost:8000/api/v1/products?skip=0&limit=50"
#
# GET /products?category_id=... (Kategoriye göre filtre):
#   curl "http://localhost:8000/api/v1/products?category_id=674a1b2c3d4e5f6a7b8c9d0e"
#
# GET /products?search=süt (name/description arama):
#   curl "http://localhost:8000/api/v1/products?search=süt"
#
# GET /products?min_price=10&max_price=50 (Fiyat aralığı):
#   curl "http://localhost:8000/api/v1/products?min_price=10&max_price=50"
#
# GET /products/{id} (Ürün detayı):
#   curl "http://localhost:8000/api/v1/products/674a1b2c3d4e5f6a7b8c9d0f"
#
# PUT /products/{id} (Admin, güncelle):
#   curl -X PUT http://localhost:8000/api/v1/products/674a1b2c3d4e5f6a7b8c9d0f \
#     -H "Authorization: Bearer <ADMIN_TOKEN>" \
#     -H "Content-Type: application/json" \
#     -d '{"price":26.50,"stock":50}'
#
# DELETE /products/{id} (Admin, soft delete):
#   curl -X DELETE http://localhost:8000/api/v1/products/674a1b2c3d4e5f6a7b8c9d0f \
#     -H "Authorization: Bearer <ADMIN_TOKEN>"
