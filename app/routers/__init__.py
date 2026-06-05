"""
Routers: API route'ları (endpoints)
Her resource için ayrı router dosyası
"""

from .health import router as health_router
from .auth import router as auth_router
from .users import router as users_router
from .admin import router as admin_router
from .categories import router as categories_router
from .products import router as products_router
from .recipes import router as recipes_router
from .ai import router as ai_router
from .cart import router as cart_router
from .orders import router as orders_router
from .addresses import router as addresses_router
from .favorites import router as favorites_router
from .notifications import router as notifications_router
from .uploads import router as uploads_router

__all__ = [
    "health_router",
    "auth_router",
    "users_router",
    "admin_router",
    "categories_router",
    "products_router",
    "recipes_router",
    "ai_router",
    "cart_router",
    "orders_router",
    "addresses_router",
    "favorites_router",
    "notifications_router",
    "uploads_router",
]
