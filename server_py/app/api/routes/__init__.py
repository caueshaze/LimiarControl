from app.api.routes.campaigns import router as campaigns_router
from app.api.routes.dev import router as dev_router
from app.api.routes.inventory import router as inventory_router
from app.api.routes.items import router as items_router
from app.api.routes.members import router as members_router
from app.api.routes.npcs import router as npcs_router
from app.api.routes.preferences import router as preferences_router
from app.api.routes.role_mode import router as role_mode_router
from app.api.routes.sessions import router as sessions_router
from app.api.routes.auth import router as auth_router
from app.api.routes.me import router as me_router

__all__ = [
    "campaigns_router",
    "items_router",
    "role_mode_router",
    "dev_router",
    "inventory_router",
    "npcs_router",
    "preferences_router",
    "sessions_router",
    "members_router",
    "auth_router",
    "me_router",
]
