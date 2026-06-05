"""
Uploads Router - image upload endpoints.
"""

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status

from app.dependencies.admin import get_admin_user

router = APIRouter(prefix="/uploads", tags=["Uploads"])

UPLOAD_ROOT = Path("static/uploads")
MAX_IMAGE_BYTES = 12 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/heic": ".heic",
    "image/heif": ".heif",
}


@router.post(
    "/image",
    status_code=status.HTTP_201_CREATED,
    summary="Admin image upload",
)
async def upload_image(
    request: Request,
    file: UploadFile = File(...),
    _admin=Depends(get_admin_user),
):
    content_type = (file.content_type or "").lower()
    extension = ALLOWED_IMAGE_TYPES.get(content_type)
    if not extension:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only jpg, png, webp, heic and heif images are supported.",
        )

    content = await file.read()
    if len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image file must be 12 MB or smaller.",
        )

    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}{extension}"
    target_path = UPLOAD_ROOT / filename
    target_path.write_bytes(content)

    relative_url = f"/static/uploads/{filename}"
    return {
        "image_url": str(request.base_url).rstrip("/") + relative_url,
        "path": relative_url,
    }
