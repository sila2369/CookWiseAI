"""
Admin Authorization Dependency
==============================

Sadece admin kullanıcıların erişebileceği endpoint'ler için.
current_user'ı alır, is_admin False ise 403 döner.
"""

import logging
from typing import Dict, Any

from fastapi import Depends, HTTPException, status

from app.dependencies.auth import get_active_user

logger = logging.getLogger(__name__)


async def get_admin_user(
    current_user: Dict[str, Any] = Depends(get_active_user),
) -> Dict[str, Any]:
    """
    Admin yetkisi kontrolü.

    current_user'dan is_admin değerini kontrol eder.
    is_admin False ise 403 Forbidden döner.

    Kullanım:
        @router.get("/admin/test")
        async def admin_test(admin=Depends(get_admin_user)):
            return {"message": "Admin only"}
    """
    if not current_user.get("is_admin", False):
        logger.warning(f"Non-admin access denied: {current_user.get('email')}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
