from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException
from sqlmodel import Session as DbSession, select

from app.models.campaign_member import CampaignMember
from app.models.character_sheet import CharacterSheet
from app.models.inventory import InventoryItem
from app.models.item import Item
from app.models.purchase_event import PurchaseEvent
from app.models.session import Session
from app.models.session_state import SessionState
from app.schemas.inventory import CurrencyRead
from app.services.centrifugo import centrifugo
from app.services.money import format_money, normalize_money, to_copper
from app.services.realtime import build_event, campaign_channel, event_version, session_channel
from app.services.session_rest import ensure_rest_state
from app.services.session_state_finalize import finalize_session_state_data
from ._shared import get_or_create_session_runtime, require_identifier, to_inventory_read, to_item_read


def _price_to_cp(item: Item, quantity: int = 1) -> int:
    if quantity < 1:
        return 0
    if item.cost_unit and item.price is not None:
        return to_copper(
            item.price * quantity,
            item.cost_unit.value if hasattr(item.cost_unit, "value") else str(item.cost_unit),
        )
    if item.price is None:
        return 0
    return to_copper(item.price * quantity, "gp")


def _to_currency_read(currency: dict[str, int]) -> CurrencyRead:
    return CurrencyRead(copperValue=int(currency.get("copperValue", 0) or 0))


def _format_cp_label(total_cp: int) -> str:
    return format_money(total_cp)


def _ensure_player_session_state(
    entry: Session,
    player_user_id: str,
    session: DbSession,
) -> SessionState:
    state = session.exec(
        select(SessionState).where(
            SessionState.session_id == require_identifier(entry.id, "Session is missing an id"),
            SessionState.player_user_id == player_user_id,
        )
    ).first()
    if state:
        if not isinstance(state.state_json, dict):
            state.state_json = {}
        state.state_json = finalize_session_state_data(state.state_json)
        state.state_json["currency"] = normalize_money(state.state_json.get("currency"))
        return state

    if not entry.party_id:
        raise HTTPException(status_code=404, detail="Session state not found")

    base_sheet = session.exec(
        select(CharacterSheet).where(
            CharacterSheet.party_id == entry.party_id,
            CharacterSheet.player_user_id == player_user_id,
        )
    ).first()
    if not base_sheet or not isinstance(base_sheet.data, dict):
        raise HTTPException(status_code=404, detail="Character sheet not found")

    state = SessionState(
        id=str(uuid4()),
        session_id=require_identifier(entry.id, "Session is missing an id"),
        player_user_id=player_user_id,
        state_json=finalize_session_state_data(
            {
                **dict(base_sheet.data),
                "currency": normalize_money(
                    dict(base_sheet.data).get("currency") if isinstance(base_sheet.data, dict) else None
                ),
            }
        ),
        created_at=datetime.now(timezone.utc),
        updated_at=None,
    )
    session.add(state)
    session.flush()
    return state


async def _publish_session_state_realtime(
    entry: Session,
    player_user_id: str,
    timestamp: datetime,
    state_data: dict | None = None,
) -> None:
    await centrifugo.publish(
        campaign_channel(entry.campaign_id),
        build_event(
            "session_state_updated",
            {
                "campaignId": entry.campaign_id,
                "partyId": entry.party_id,
                "playerUserId": player_user_id,
                "sessionId": require_identifier(entry.id, "Session is missing an id"),
                "state": state_data,
            },
            version=event_version(timestamp),
        ),
    )


def require_active_shop_session(session_id: str, session: DbSession) -> tuple[Session, object]:
    entry = session.exec(select(Session).where(Session.id == session_id)).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Session not found")
    runtime = get_or_create_session_runtime(
        require_identifier(entry.id, "Session is missing an id"),
        session,
    )
    return entry, runtime


def create_purchase_event(
    *,
    session_id: str,
    user_id: str,
    member: CampaignMember,
    item_id: str,
    item_name: str,
    quantity: int,
) -> PurchaseEvent:
    return PurchaseEvent(
        id=str(uuid4()),
        session_id=session_id,
        user_id=user_id,
        member_id=require_identifier(member.id, "Campaign member is missing an id"),
        item_id=item_id,
        item_name=item_name,
        quantity=quantity,
        created_at=datetime.now(timezone.utc),
    )


def create_inventory_entry(
    *,
    entry: Session,
    member: CampaignMember,
    item_id: str,
    quantity: int,
) -> InventoryItem:
    return InventoryItem(
        id=str(uuid4()),
        campaign_id=entry.campaign_id,
        party_id=entry.party_id,
        member_id=require_identifier(member.id, "Campaign member is missing an id"),
        item_id=item_id,
        quantity=quantity,
        is_equipped=False,
        notes=None,
        created_at=datetime.now(timezone.utc),
        updated_at=None,
    )


async def publish_purchase_realtime(
    entry: Session,
    event: PurchaseEvent,
    display_name: str | None,
) -> None:
    payload = {
        "sessionId": require_identifier(entry.id, "Session is missing an id"),
        "campaignId": entry.campaign_id,
        "partyId": entry.party_id,
        "userId": event.user_id,
        "displayName": display_name,
        "itemId": event.item_id,
        "itemName": event.item_name,
        "quantity": event.quantity,
        "createdAt": event.created_at.isoformat(),
    }
    built_event = build_event(
        "shop_purchase_created",
        payload,
        version=event_version(event.created_at),
    )
    await centrifugo.publish(
        session_channel(require_identifier(entry.id, "Session is missing an id")),
        built_event,
    )
    await centrifugo.publish(campaign_channel(entry.campaign_id), built_event)


async def publish_sale_realtime(
    entry: Session,
    *,
    payload: dict,
    timestamp: datetime,
) -> None:
    built_event = build_event(
        "shop_sale_created",
        payload,
        version=event_version(timestamp),
    )
    await centrifugo.publish(
        session_channel(require_identifier(entry.id, "Session is missing an id")),
        built_event,
    )
    await centrifugo.publish(campaign_channel(entry.campaign_id), built_event)


__all__ = [
    "_ensure_player_session_state",
    "_format_cp_label",
    "_price_to_cp",
    "_publish_session_state_realtime",
    "_to_currency_read",
    "create_inventory_entry",
    "create_purchase_event",
    "publish_purchase_realtime",
    "publish_sale_realtime",
    "require_active_shop_session",
    "to_inventory_read",
    "to_item_read",
]
