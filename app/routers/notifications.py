"""
Notifications Router - in-app notification box endpoints.
"""

from datetime import datetime
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.dependencies.admin import get_admin_user
from app.dependencies.auth import get_active_user
from app.dependencies.services import get_required_database


router = APIRouter(prefix="/notifications", tags=["Notifications"])


class NotificationResponse(BaseModel):
    id: str
    title: str
    body: str
    type: str
    product_id: Optional[str] = None
    product_name: Optional[str] = None
    promotion_label: Optional[str] = None
    is_read: bool = False
    created_at: datetime | str


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    unread_count: int
    total: int


class AdminNotificationCreate(BaseModel):
    title: str
    body: str
    type: str = "announcement"


def _notification_to_response(doc: dict, user_id: str) -> NotificationResponse:
    read_by = {str(item) for item in doc.get("read_by", [])}
    product_id = doc.get("product_id")
    return NotificationResponse(
        id=str(doc["_id"]),
        title=doc.get("title", "Bildirim"),
        body=doc.get("body", ""),
        type=doc.get("type", "info"),
        product_id=str(product_id) if product_id else None,
        product_name=doc.get("product_name"),
        promotion_label=doc.get("promotion_label"),
        is_read=user_id in read_by,
        created_at=doc.get("created_at") or datetime.utcnow(),
    )


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    limit: int = Query(20, ge=1, le=100),
    current_user=Depends(get_active_user),
    db=Depends(get_required_database),
) -> NotificationListResponse:
    user_id = str(current_user.get("user_id") or current_user.get("id") or "")
    query = {
        "is_active": True,
        "$or": [
            {"audience": "all"},
            {"user_id": user_id},
        ],
    }
    cursor = db["notifications"].find(query).sort("created_at", -1).limit(limit)
    items = [_notification_to_response(doc, user_id) async for doc in cursor]
    unread_count = sum(1 for item in items if not item.is_read)
    total = await db["notifications"].count_documents(query)
    return NotificationListResponse(items=items, unread_count=unread_count, total=total)


@router.post("/admin/broadcast", response_model=NotificationResponse)
async def create_broadcast_notification(
    data: AdminNotificationCreate,
    _admin=Depends(get_admin_user),
    db=Depends(get_required_database),
) -> NotificationResponse:
    now = datetime.utcnow()
    title = data.title.strip()
    body = data.body.strip()
    notification_type = data.type.strip() or "announcement"
    if not title or not body:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Title and body are required")

    result = await db["notifications"].insert_one(
        {
            "title": title,
            "body": body,
            "type": notification_type,
            "audience": "all",
            "is_active": True,
            "read_by": [],
            "created_at": now,
            "updated_at": now,
        }
    )
    doc = await db["notifications"].find_one({"_id": result.inserted_id})
    return _notification_to_response(doc, "")


@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: str,
    current_user=Depends(get_active_user),
    db=Depends(get_required_database),
) -> NotificationResponse:
    try:
        oid = ObjectId(notification_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    user_id = str(current_user.get("user_id") or current_user.get("id") or "")
    await db["notifications"].update_one(
        {"_id": oid},
        {"$addToSet": {"read_by": user_id}, "$set": {"updated_at": datetime.utcnow()}},
    )
    doc = await db["notifications"].find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return _notification_to_response(doc, user_id)
