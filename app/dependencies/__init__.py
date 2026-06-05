"""
Dependencies - FastAPI Dependency Injection
==========================================

Auth: app.dependencies.auth
  - get_current_user, get_current_user_from_db
  - get_active_user, get_optional_user
  - security (HTTPBearer)

Admin: app.dependencies.admin
  - get_admin_user
"""

from app.dependencies.auth import (
    security,
    get_current_user,
    get_current_user_from_db,
    get_active_user,
    get_optional_user,
)
from app.dependencies.admin import get_admin_user

__all__ = [
    "security",
    "get_current_user",
    "get_current_user_from_db",
    "get_active_user",
    "get_optional_user",
    "get_admin_user",
]
