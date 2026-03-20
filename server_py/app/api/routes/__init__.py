from app.api.routes.base_items import router as base_items_router
from app.api.routes.base_spells import router as base_spells_router
from app.api.routes.campaign_catalog import router as campaign_catalog_router
from app.api.routes.campaign_spells import router as campaign_spells_router
from app.api.routes.campaigns import router as campaigns_router
from app.api.routes.character_sheets import router as character_sheets_router
from app.api.routes.dev import router as dev_router
from app.api.routes.inventory import router as inventory_router
from app.api.routes.items import router as items_router
from app.api.routes.members import router as members_router
from app.api.routes.parties import router as parties_router
from app.api.routes.campaign_entities import router as campaign_entities_router
from app.api.routes.session_entities import router as session_entities_router
from app.api.routes.preferences import router as preferences_router
from app.api.routes.role_mode import router as role_mode_router
from app.api.routes.sessions import router as sessions_router
from app.api.routes.auth import router as auth_router
from app.api.routes.me import router as me_router
from app.api.routes.users import router as users_router
from app.api.routes.centrifugo import router as centrifugo_router

__all__ = [
    "campaigns_router",
    "base_items_router",
    "base_spells_router",
    "campaign_catalog_router",
    "campaign_spells_router",
    "centrifugo_router",
    "character_sheets_router",
    "items_router",
    "role_mode_router",
    "dev_router",
    "inventory_router",
    "campaign_entities_router",
    "session_entities_router",
    "preferences_router",
    "sessions_router",
    "members_router",
    "parties_router",
    "auth_router",
    "me_router",
    "users_router",
]
