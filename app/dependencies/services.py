"""
Service Dependencies - Veritabanı ve servis factory'leri
========================================================

Router'larda tekrarlanan "db None ise 503" kontrolünü merkezileştirir.
"""

from fastapi import Depends, HTTPException, status

from app.core.database import get_database


async def get_required_database(db=Depends(get_database)):
    """
    Veritabanı instance'ını döner. Bağlı değilse 503.
    """
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )
    return db
