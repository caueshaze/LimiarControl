from fastapi import APIRouter

from .campaign_sessions import router as campaign_sessions_router
from .party_sessions import router as party_sessions_router
from .lobby import router as lobby_router
from .lifecycle import router as lifecycle_router
from .shop import router as shop_router
from .commands import router as commands_router
from .rolls import router as rolls_router
from .activity import router as activity_router
from .runtime import router as runtime_router
from .state import router as state_router
from .rewards import router as rewards_router
from .rest import router as rest_router

router = APIRouter()
router.include_router(campaign_sessions_router)
router.include_router(party_sessions_router)
router.include_router(lobby_router)
router.include_router(lifecycle_router)
router.include_router(shop_router)
router.include_router(commands_router)
router.include_router(rolls_router)
router.include_router(activity_router)
router.include_router(runtime_router)
router.include_router(state_router)
router.include_router(rewards_router)
router.include_router(rest_router)
