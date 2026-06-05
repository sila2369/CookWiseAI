"""
Addresses Router - Adres API endpoint'leri
===========================================

POST   /addresses           → Yeni adres ekle
GET    /addresses           → Kullanıcının adreslerini listele
GET    /addresses/{id}      → Adres detayını getir
PUT    /addresses/{id}      → Adresi güncelle
DELETE /addresses/{id}      → Adresi sil
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from app.dependencies.auth import get_active_user
from app.dependencies.services import get_required_database
from app.schemas.address import AddressCreate, AddressUpdate, AddressResponse, AddressListResponse
from app.services.address_service import AddressService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/addresses",
    tags=["Addresses"],
    responses={
        401: {"description": "Unauthorized"},
        404: {"description": "Not Found"},
    },
)


def get_address_service(db=Depends(get_required_database)) -> AddressService:
    """AddressService dependency."""
    return AddressService(db)


@router.post(
    "",
    response_model=AddressResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Yeni adres ekle",
    description="Kullanıcıya yeni bir adres ekler."
)
async def create_address(
    data: AddressCreate,
    current_user=Depends(get_active_user),
    service: AddressService = Depends(get_address_service),
) -> AddressResponse:
    user_id = current_user.get("id")
    try:
        return await service.create_address(user_id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "",
    response_model=AddressListResponse,
    summary="Adreslerimi listele",
    description="Giriş yapmış kullanıcının adreslerini getirir (varsayılan olan en üstte gelir)."
)
async def list_my_addresses(
    current_user=Depends(get_active_user),
    service: AddressService = Depends(get_address_service),
) -> AddressListResponse:
    user_id = current_user.get("id")
    return await service.get_user_addresses(user_id)


@router.get(
    "/{address_id}",
    response_model=AddressResponse,
    summary="Adres detayını getir",
    description="Kullanıcının kendi adresinin detayını getirir."
)
async def get_address(
    address_id: str,
    current_user=Depends(get_active_user),
    service: AddressService = Depends(get_address_service),
) -> AddressResponse:
    user_id = current_user.get("id")
    try:
        address = await service.get_address(address_id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    if not address:
        raise HTTPException(status_code=404, detail="Address not found")
        
    return address


@router.put(
    "/{address_id}",
    response_model=AddressResponse,
    summary="Adresi güncelle",
    description="Adresin belirtilen alanlarını günceller."
)
async def update_address(
    address_id: str,
    update_data: AddressUpdate,
    current_user=Depends(get_active_user),
    service: AddressService = Depends(get_address_service),
) -> AddressResponse:
    user_id = current_user.get("id")
    try:
        address = await service.update_address(address_id, user_id, update_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    if not address:
        raise HTTPException(status_code=404, detail="Address not found")
        
    return address


@router.delete(
    "/{address_id}",
    summary="Adresi sil",
    description="Kullanıcının adresini tamamen siler."
)
async def delete_address(
    address_id: str,
    current_user=Depends(get_active_user),
    service: AddressService = Depends(get_address_service),
):
    user_id = current_user.get("id")
    try:
        deleted = await service.delete_address(address_id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    if not deleted:
        raise HTTPException(status_code=404, detail="Address not found")
        
    return JSONResponse(status_code=status.HTTP_200_OK, content={"detail": "Address deleted successfully"})
