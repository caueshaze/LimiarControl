from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session as DbSession, select

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.campaign_member import CampaignMember
from app.models.character_sheet import CharacterSheet
from app.models.inventory import InventoryItem
from app.models.item import Item
from app.models.purchase_event import PurchaseEvent
from app.models.session import Session, SessionStatus
from app.models.session_state import SessionState
from app.schemas.inventory import (
    CurrencyRead,
    InventoryBuy,
    InventoryRead,
    InventorySell,
    InventorySellRead,
)
from app.schemas.item import ItemRead
from app.services.centrifugo import centrifugo
from app.services.realtime import build_event, campaign_channel, event_version, session_channel
from ._shared import get_or_create_session_runtime, to_inventory_read, to_item_read

router = APIRouter()

CP_PER_GP = Decimal("100")
EMPTY_CURRENCY = {"cp": 0, "sp": 0, "ep": 0, "gp": 0, "pp": 0}


def _price_to_cp(price: float | None, quantity: int = 1) -> int:
    if not price or quantity < 1:
        return 0
    value = (Decimal(str(price)) * CP_PER_GP * Decimal(str(quantity))).quantize(
        Decimal("1"),
        rounding=ROUND_HALF_UP,
    )
    return max(0, int(value))


def _currency_to_cp(currency: dict | None) -> int:
    if not isinstance(currency, dict):
        return 0
    return (
        int(currency.get("cp", 0) or 0)
        + int(currency.get("sp", 0) or 0) * 10
        + int(currency.get("ep", 0) or 0) * 50
        + int(currency.get("gp", 0) or 0) * 100
        + int(currency.get("pp", 0) or 0) * 1000
    )


def _cp_to_currency(total_cp: int) -> dict[str, int]:
    remaining = max(0, total_cp)
    gp, remaining = divmod(remaining, 100)
    sp, cp = divmod(remaining, 10)
    return {
        **EMPTY_CURRENCY,
        "gp": gp,
        "sp": sp,
        "cp": cp,
    }


def _to_currency_read(currency: dict[str, int]) -> CurrencyRead:
    return CurrencyRead(
        cp=int(currency.get("cp", 0) or 0),
        sp=int(currency.get("sp", 0) or 0),
        ep=int(currency.get("ep", 0) or 0),
        gp=int(currency.get("gp", 0) or 0),
        pp=int(currency.get("pp", 0) or 0),
    )


def _format_cp_label(total_cp: int) -> str:
    currency = _cp_to_currency(total_cp)
    parts: list[str] = []
    if currency["gp"] > 0:
        parts.append(f"{currency['gp']} gp")
    if currency["sp"] > 0:
        parts.append(f"{currency['sp']} sp")
    if currency["cp"] > 0 or not parts:
        parts.append(f"{currency['cp']} cp")
    return " ".join(parts)


def _ensure_player_session_state(
    entry: Session,
    player_user_id: str,
    session: DbSession,
) -> SessionState:
    state = session.exec(
        select(SessionState).where(
            SessionState.session_id == entry.id,
            SessionState.player_user_id == player_user_id,
        )
    ).first()
    if state:
        if not isinstance(state.state_json, dict):
            state.state_json = {}
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
        session_id=entry.id,
        player_user_id=player_user_id,
        state_json=dict(base_sheet.data),
    )
    session.add(state)
    session.flush()
    return state


async def _publish_session_state_realtime(entry: Session, player_user_id: str, timestamp) -> None:
    await centrifugo.publish(
        campaign_channel(entry.campaign_id),
        build_event(
            "session_state_updated",
            {
                "campaignId": entry.campaign_id,
                "partyId": entry.party_id,
                "playerUserId": player_user_id,
                "sessionId": entry.id,
            },
            version=event_version(timestamp),
        ),
    )


@router.get("/sessions/{session_id}/shop/items", response_model=list[ItemRead])
def list_session_shop_items(
    session_id: str,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    entry = session.exec(select(Session).where(Session.id == session_id)).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Session not found")
    member = session.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == entry.campaign_id,
            CampaignMember.user_id == user.id,
        )
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Not a campaign member")
    items = session.exec(
        select(Item).where(Item.campaign_id == entry.campaign_id)
        .order_by(Item.created_at.desc())
    ).all()
    return [to_item_read(item) for item in items]


@router.post("/sessions/{session_id}/shop/buy", response_model=InventoryRead, status_code=201)
async def buy_session_shop_item(
    session_id: str,
    payload: InventoryBuy,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    entry = session.exec(select(Session).where(Session.id == session_id)).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Session not found")
    if entry.status != SessionStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Session is not active")
    runtime = get_or_create_session_runtime(entry.id, session)
    if not runtime.shop_open:
        raise HTTPException(status_code=400, detail="Shop is closed")
    member = session.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == entry.campaign_id,
            CampaignMember.user_id == user.id,
        )
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Not a campaign member")
    item = session.exec(select(Item).where(Item.id == payload.itemId)).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if item.campaign_id != entry.campaign_id:
        raise HTTPException(status_code=400, detail="Item does not belong to campaign")
    if payload.quantity < 1:
        raise HTTPException(status_code=400, detail="Invalid quantity")
    total_price_cp = _price_to_cp(item.price, payload.quantity)
    state = _ensure_player_session_state(entry, user.id, session)
    current_currency_cp = _currency_to_cp(state.state_json.get("currency"))
    if total_price_cp > current_currency_cp:
        raise HTTPException(status_code=400, detail="Not enough currency")
    state.state_json = {
        **state.state_json,
        "currency": _cp_to_currency(current_currency_cp - total_price_cp),
    }
    session.add(state)

    purchase_event = PurchaseEvent(
        id=str(uuid4()),
        session_id=session_id,
        user_id=user.id,
        member_id=member.id,
        item_id=payload.itemId,
        item_name=item.name,
        quantity=payload.quantity,
    )
    session.add(purchase_event)

    existing = session.exec(
        select(InventoryItem).where(
            InventoryItem.campaign_id == entry.campaign_id,
            InventoryItem.party_id == entry.party_id,
            InventoryItem.member_id == member.id,
            InventoryItem.item_id == payload.itemId,
        )
    ).first()

    if existing:
        existing.quantity += payload.quantity
        session.add(existing)
        session.commit()
        session.refresh(purchase_event)
        session.refresh(existing)
        session.refresh(state)
        created = to_inventory_read(existing)
        await publish_purchase_realtime(entry, purchase_event, member.display_name)
        await _publish_session_state_realtime(
            entry,
            user.id,
            state.updated_at or state.created_at,
        )
        return created

    new_entry = InventoryItem(
        id=str(uuid4()),
        campaign_id=entry.campaign_id,
        party_id=entry.party_id,
        member_id=member.id,
        item_id=payload.itemId,
        quantity=payload.quantity,
        is_equipped=False,
        notes=None,
    )
    session.add(new_entry)
    session.commit()
    session.refresh(purchase_event)
    session.refresh(new_entry)
    session.refresh(state)
    created = to_inventory_read(new_entry)
    await publish_purchase_realtime(entry, purchase_event, member.display_name)
    await _publish_session_state_realtime(
        entry,
        user.id,
        state.updated_at or state.created_at,
    )
    return created


@router.post("/sessions/{session_id}/shop/sell", response_model=InventorySellRead)
async def sell_session_shop_item(
    session_id: str,
    payload: InventorySell,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    entry = session.exec(select(Session).where(Session.id == session_id)).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Session not found")
    if entry.status != SessionStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Session is not active")
    runtime = get_or_create_session_runtime(entry.id, session)
    if not runtime.shop_open:
        raise HTTPException(status_code=400, detail="Shop is closed")
    member = session.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == entry.campaign_id,
            CampaignMember.user_id == user.id,
        )
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Not a campaign member")
    if payload.quantity < 1:
        raise HTTPException(status_code=400, detail="Invalid quantity")

    inventory_entry = session.exec(
        select(InventoryItem).where(
            InventoryItem.id == payload.inventoryItemId,
            InventoryItem.campaign_id == entry.campaign_id,
            InventoryItem.party_id == entry.party_id,
            InventoryItem.member_id == member.id,
        )
    ).first()
    if not inventory_entry:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    if payload.quantity > inventory_entry.quantity:
        raise HTTPException(status_code=400, detail="Not enough quantity to sell")

    item = session.exec(select(Item).where(Item.id == inventory_entry.item_id)).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    refund_cp = _price_to_cp(item.price, payload.quantity)
    state = _ensure_player_session_state(entry, user.id, session)
    current_currency_cp = _currency_to_cp(state.state_json.get("currency"))
    next_currency = _cp_to_currency(current_currency_cp + refund_cp)
    state.state_json = {
        **state.state_json,
        "currency": next_currency,
    }
    session.add(state)

    sold_item_id = inventory_entry.item_id
    sold_item_name = item.name
    remaining_quantity = inventory_entry.quantity - payload.quantity
    updated_inventory_entry: InventoryItem | None = inventory_entry
    if remaining_quantity > 0:
        inventory_entry.quantity = remaining_quantity
        session.add(inventory_entry)
    else:
        updated_inventory_entry = None
        session.delete(inventory_entry)

    session.commit()
    session.refresh(state)
    if updated_inventory_entry:
        session.refresh(updated_inventory_entry)

    refund_currency = _cp_to_currency(refund_cp)
    refund_label = _format_cp_label(refund_cp)
    event_payload = {
        "sessionId": entry.id,
        "campaignId": entry.campaign_id,
        "partyId": entry.party_id,
        "userId": user.id,
        "displayName": member.display_name,
        "itemId": sold_item_id,
        "itemName": sold_item_name,
        "quantity": payload.quantity,
        "refundCurrency": refund_currency,
        "refundLabel": refund_label,
        "createdAt": (state.updated_at or state.created_at).isoformat(),
    }
    await centrifugo.publish(
        session_channel(entry.id),
        build_event(
            "shop_sale_created",
            event_payload,
            version=event_version(state.updated_at or state.created_at),
        ),
    )
    await centrifugo.publish(
        campaign_channel(entry.campaign_id),
        build_event(
            "shop_sale_created",
            event_payload,
            version=event_version(state.updated_at or state.created_at),
        ),
    )
    await _publish_session_state_realtime(
        entry,
        user.id,
        state.updated_at or state.created_at,
    )

    return InventorySellRead(
        inventoryItem=to_inventory_read(updated_inventory_entry) if updated_inventory_entry else None,
        itemId=sold_item_id,
        itemName=sold_item_name,
        soldQuantity=payload.quantity,
        refundCurrency=_to_currency_read(refund_currency),
        refundLabel=refund_label,
        currentCurrency=_to_currency_read(next_currency),
    )


async def publish_purchase_realtime(entry: Session, event: PurchaseEvent, display_name: str | None) -> None:
    payload = {
        "sessionId": entry.id,
        "campaignId": entry.campaign_id,
        "partyId": entry.party_id,
        "userId": event.user_id,
        "displayName": display_name,
        "itemId": event.item_id,
        "itemName": event.item_name,
        "quantity": event.quantity,
        "createdAt": event.created_at.isoformat() if event.created_at else None,
    }
    await centrifugo.publish(
        session_channel(entry.id),
        build_event("shop_purchase_created", payload, version=event_version(event.created_at)),
    )
    await centrifugo.publish(
        campaign_channel(entry.campaign_id),
        build_event("shop_purchase_created", payload, version=event_version(event.created_at)),
    )
