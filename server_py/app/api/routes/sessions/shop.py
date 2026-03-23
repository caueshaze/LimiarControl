from fastapi import APIRouter, Depends
from sqlmodel import Session as DbSession

from app.api.deps import get_current_user
from app.db.session import get_session
from app.schemas.inventory import (
    InventoryBuy,
    InventoryRead,
    InventorySell,
    InventorySellRead,
)
from app.schemas.item import ItemRead
from .shop_common import (
    _ensure_player_session_state,
    _format_cp_label,
    _price_to_cp,
    _publish_session_state_realtime,
    _to_currency_read,
)
from .shop_service import (
    buy_session_shop_item_service,
    list_session_shop_items_service,
    sell_session_shop_item_service,
)

router = APIRouter()


@router.get("/sessions/{session_id}/shop/items", response_model=list[ItemRead])
def list_session_shop_items(
    session_id: str,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    return list_session_shop_items_service(session_id, user, session)


@router.post("/sessions/{session_id}/shop/buy", response_model=InventoryRead, status_code=201)
async def buy_session_shop_item(
    session_id: str,
    payload: InventoryBuy,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    return await buy_session_shop_item_service(session_id, payload, user, session)


@router.post("/sessions/{session_id}/shop/sell", response_model=InventorySellRead)
async def sell_session_shop_item(
    session_id: str,
    payload: InventorySell,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    return await sell_session_shop_item_service(session_id, payload, user, session)


__all__ = [
    "router",
    "_ensure_player_session_state",
    "_format_cp_label",
    "_price_to_cp",
    "_publish_session_state_realtime",
    "_to_currency_read",
]
