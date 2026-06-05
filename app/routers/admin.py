"""
Admin Router - Sadece admin erişebilen endpoint'ler
"""

from datetime import datetime
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.core.database import get_database
from app.dependencies.admin import get_admin_user
from app.models.user import User
from app.schemas.user import UserListResponse, UserResponse

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Admin access required"},
    },
)


class UserStatusUpdate(BaseModel):
    is_active: bool


@router.get(
    "/test",
    summary="Admin test endpoint",
    description="Sadece is_admin=True kullanıcılar erişebilir. Yetkilendirme testi için.",
    responses={
        200: {
            "description": "Admin erişimi başarılı",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Admin access OK",
                        "user_email": "admin@example.com",
                    }
                }
            }
        },
        403: {
            "description": "Admin değilsiniz",
            "content": {
                "application/json": {
                    "example": {"detail": "Admin access required"}
                }
            }
        },
    },
)
async def admin_test(
    admin_user=Depends(get_admin_user),
):
    """Admin yetkisi test endpoint'i."""
    return {
        "message": "Admin access OK",
        "user_email": admin_user.get("email"),
    }


@router.get("/users", response_model=UserListResponse)
async def list_users_for_admin(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=300),
    search: Optional[str] = Query(default=None),
    admin_user=Depends(get_admin_user),
    db=Depends(get_database),
):
    """Admin paneli icin kullanici listesi."""
    if db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")

    query = {}
    if search:
        query = {
            "$or": [
                {"full_name": {"$regex": search, "$options": "i"}},
                {"email": {"$regex": search, "$options": "i"}},
                {"phone": {"$regex": search, "$options": "i"}},
            ]
        }

    cursor = db["users"].find(query).sort("created_at", -1).skip(skip).limit(limit)
    items = []
    async for doc in cursor:
        doc.setdefault("is_verified", False)
        items.append(UserResponse(**User.dict_to_response(doc)))

    total = await db["users"].count_documents(query)
    return UserListResponse(items=items, total=total, skip=skip, limit=limit)


@router.patch("/users/{user_id}/status", response_model=UserResponse)
async def update_user_status_for_admin(
    user_id: str,
    payload: UserStatusUpdate,
    admin_user=Depends(get_admin_user),
    db=Depends(get_database),
):
    """Admin panelinden kullaniciyi aktif/pasif yap."""
    if db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")

    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user_id")

    await db["users"].update_one(
        {"_id": oid},
        {"$set": {"is_active": payload.is_active, "updated_at": datetime.utcnow()}},
    )
    doc = await db["users"].find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    doc.setdefault("is_verified", False)
    return UserResponse(**User.dict_to_response(doc))


@router.get("/analytics")
async def get_admin_analytics(
    admin_user=Depends(get_admin_user),
    db=Depends(get_database),
):
    """Admin ana ekrani icin operasyon analitigi."""
    if db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")

    users = db["users"]
    products = db["products"]
    orders = db["orders"]

    users_total = await users.count_documents({})
    active_users = await users.count_documents({"is_active": True})
    products_total = await products.count_documents({"is_active": True})
    low_stock_products = await products.count_documents({"is_active": True, "stock": {"$lte": 5}})
    active_campaigns = await products.count_documents({"is_active": True, "is_promoted": True})
    orders_total = await orders.count_documents({})
    pending_orders = await orders.count_documents({"status": {"$in": ["PENDING", "PREPARING", "ON_THE_WAY"]}})

    revenue_rows = await orders.aggregate([
        {"$match": {"status": {"$ne": "CANCELLED"}}},
        {"$group": {"_id": None, "total": {"$sum": "$total_price"}}},
    ]).to_list(length=1)
    revenue_total = float(revenue_rows[0]["total"]) if revenue_rows else 0.0

    top_products_rows = await orders.aggregate([
        {"$unwind": "$items"},
        {
            "$group": {
                "_id": "$items.name",
                "quantity": {"$sum": "$items.quantity"},
                "revenue": {"$sum": "$items.subtotal"},
            }
        },
        {"$sort": {"quantity": -1}},
        {"$limit": 5},
    ]).to_list(length=5)

    status_rows = await orders.aggregate([
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]).to_list(length=20)

    return {
        "users_total": users_total,
        "active_users": active_users,
        "products_total": products_total,
        "low_stock_products": low_stock_products,
        "active_campaigns": active_campaigns,
        "orders_total": orders_total,
        "pending_orders": pending_orders,
        "revenue_total": revenue_total,
        "top_products": [
            {"name": row["_id"], "quantity": row["quantity"], "revenue": float(row["revenue"])}
            for row in top_products_rows
        ],
        "orders_by_status": [
            {"status": row["_id"], "count": row["count"]}
            for row in status_rows
        ],
    }
