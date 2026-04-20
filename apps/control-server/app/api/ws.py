from fastapi import APIRouter

from app.api.ws_registry import (
    DICE_RE,
    CampaignRoomRegistry,
    RoomRegistry,
    campaign_room_registry,
    parse_expression,
    room_registry,
    to_roll_read,
)
from app.api.ws_session import router as session_router, session_ws
from app.api.ws_campaign import router as campaign_router, campaign_ws

router = APIRouter()
router.include_router(session_router)
router.include_router(campaign_router)
