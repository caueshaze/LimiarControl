from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException
from sqlmodel import Session as DbSession, select

from app.models.campaign_member import CampaignMember
from app.models.campaign import RoleMode
from app.models.item import Item
from app.models.session import SessionStatus
from app.models.session_command_event import SessionCommandEvent
from app.schemas.inventory import (
    InventoryBuy,
    InventoryConditionTagAdd,
    InventoryRead,
    InventorySell,
    InventorySellRead,
)
from app.schemas.item import ItemRead
from ._shared import require_identifier
from .shop_common import (
    _ensure_player_session_state,
    _format_cp_label,
    _price_to_cp,
    _publish_session_state_realtime,
    _to_currency_read,
    create_inventory_entry,
    create_purchase_event,
    publish_purchase_realtime,
    publish_sale_realtime,
    require_active_shop_session,
    to_inventory_read,
    to_item_read,
)
from app.models.inventory import InventoryItem
from app.services.combat import CombatService
from app.services.magic_item_effects import inventory_item_supports_stacking
from app.services.item_condition_tags import (
    ALLOWED_ITEM_CONDITION_TAGS,
    add_item_condition_tag,
    normalize_item_condition_tags,
    remove_item_condition_tag,
)
from app.services.money import normalize_money
from app.services.session_state_finalize import finalize_session_state_data


def require_campaign_member(entry, user, session: DbSession) -> CampaignMember:
    member = session.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == entry.campaign_id,
            CampaignMember.user_id == user.id,
        )
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Not a campaign member")
    return member


def create_session_command_event(
    *,
    session_id: str,
    user_id: str,
    member: CampaignMember,
    command_type: str,
    payload_json: dict,
) -> SessionCommandEvent:
    return SessionCommandEvent(
        id=str(uuid4()),
        session_id=session_id,
        user_id=user_id,
        member_id=require_identifier(member.id, "Campaign member is missing an id"),
        actor_name=member.display_name,
        command_type=command_type,
        payload_json=payload_json,
        created_at=datetime.now(timezone.utc),
    )


def ensure_shop_open(entry, runtime) -> None:
    if entry.status != SessionStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Session is not active")
    if not runtime.shop_open:
        raise HTTPException(status_code=400, detail="Shop is closed")


def _require_inventory_access(entry, user, session: DbSession) -> CampaignMember:
    member = require_campaign_member(entry, user, session)
    if not member:
        raise HTTPException(status_code=403, detail="Not a campaign member")
    return member


def list_session_shop_items_service(
    session_id: str,
    user,
    session: DbSession,
) -> list[ItemRead]:
    entry, _runtime = require_active_shop_session(session_id, session)
    member = require_campaign_member(entry, user, session)
    if not member:
        raise HTTPException(status_code=403, detail="Not a campaign member")
    items = list(
        session.exec(select(Item).where(Item.campaign_id == entry.campaign_id)).all()
    )
    items.sort(
        key=lambda item: item.created_at.timestamp() if item.created_at is not None else 0.0,
        reverse=True,
    )
    return [to_item_read(item) for item in items]


async def buy_session_shop_item_service(
    session_id: str,
    payload: InventoryBuy,
    user,
    session: DbSession,
) -> InventoryRead:
    entry, runtime = require_active_shop_session(session_id, session)
    ensure_shop_open(entry, runtime)
    member = require_campaign_member(entry, user, session)
    item = session.exec(select(Item).where(Item.id == payload.itemId)).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if item.campaign_id != entry.campaign_id:
        raise HTTPException(status_code=400, detail="Item does not belong to campaign")
    item_id = require_identifier(item.id, "Item is missing an id")
    if payload.quantity < 1:
        raise HTTPException(status_code=400, detail="Invalid quantity")

    total_price_cp = _price_to_cp(item, payload.quantity)
    state = _ensure_player_session_state(entry, user.id, session)
    current_currency_cp = normalize_money(state.state_json.get("currency")).get("copperValue", 0)
    if total_price_cp > current_currency_cp:
        raise HTTPException(status_code=400, detail="Not enough currency")
    state.state_json = finalize_session_state_data({
        **state.state_json,
        "currency": {"copperValue": max(0, current_currency_cp - total_price_cp)},
    })
    session.add(state)

    purchase_event = create_purchase_event(
        session_id=session_id,
        user_id=user.id,
        member=member,
        item_id=item_id,
        item_name=item.name,
        quantity=payload.quantity,
    )
    session.add(purchase_event)
    session.add(
        create_session_command_event(
            session_id=session_id,
            user_id=user.id,
            member=member,
            command_type="shop_purchase",
            payload_json={
                "itemId": item_id,
                "itemName": item.name,
                "quantity": payload.quantity,
                "amountLabel": _format_cp_label(total_price_cp),
            },
        )
    )

    existing = session.exec(
        select(InventoryItem).where(
            InventoryItem.campaign_id == entry.campaign_id,
            InventoryItem.party_id == entry.party_id,
            InventoryItem.member_id == require_identifier(member.id, "Campaign member is missing an id"),
            InventoryItem.item_id == item_id,
        )
    ).first()

    if existing and inventory_item_supports_stacking(item):
        existing.quantity += payload.quantity
        session.add(existing)
        _cs_buy, _tier_buy = CombatService.get_state_and_recompute_encumbrance(session, session_id, user.id)
        session.commit()
        session.refresh(purchase_event)
        session.refresh(existing)
        session.refresh(state)
        if _tier_buy and _cs_buy:
            session.refresh(_cs_buy)
            await CombatService._emit_state(session_id, _cs_buy)
        await publish_purchase_realtime(entry, purchase_event, member.display_name)
        await _publish_session_state_realtime(
            entry,
            user.id,
            state.updated_at or state.created_at,
            state.state_json if isinstance(state.state_json, dict) else None,
        )
        return to_inventory_read(existing)

    new_entry = create_inventory_entry(
        entry=entry,
        member=member,
        item=item,
        quantity=payload.quantity,
    )
    session.add(new_entry)
    _cs_buy, _tier_buy = CombatService.get_state_and_recompute_encumbrance(session, session_id, user.id)
    session.commit()
    session.refresh(purchase_event)
    session.refresh(new_entry)
    session.refresh(state)
    if _tier_buy and _cs_buy:
        session.refresh(_cs_buy)
        await CombatService._emit_state(session_id, _cs_buy)
    await publish_purchase_realtime(entry, purchase_event, member.display_name)
    await _publish_session_state_realtime(
        entry,
        user.id,
        state.updated_at or state.created_at,
        state.state_json if isinstance(state.state_json, dict) else None,
    )
    return to_inventory_read(new_entry)


async def sell_session_shop_item_service(
    session_id: str,
    payload: InventorySell,
    user,
    session: DbSession,
) -> InventorySellRead:
    entry, runtime = require_active_shop_session(session_id, session)
    ensure_shop_open(entry, runtime)
    member = require_campaign_member(entry, user, session)
    if payload.quantity < 1:
        raise HTTPException(status_code=400, detail="Invalid quantity")

    inventory_entry = session.exec(
        select(InventoryItem).where(
            InventoryItem.id == payload.inventoryItemId,
            InventoryItem.campaign_id == entry.campaign_id,
            InventoryItem.party_id == entry.party_id,
            InventoryItem.member_id == require_identifier(member.id, "Campaign member is missing an id"),
        )
    ).first()
    if not inventory_entry:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    if payload.quantity > inventory_entry.quantity:
        raise HTTPException(status_code=400, detail="Not enough quantity to sell")

    item = session.exec(select(Item).where(Item.id == inventory_entry.item_id)).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    refund_cp = _price_to_cp(item, payload.quantity)
    state = _ensure_player_session_state(entry, user.id, session)
    current_currency_cp = normalize_money(state.state_json.get("currency")).get("copperValue", 0)
    next_currency = {"copperValue": current_currency_cp + refund_cp}
    state.state_json = finalize_session_state_data({**state.state_json, "currency": next_currency})
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

    _cs_sell, _tier_sell = CombatService.get_state_and_recompute_encumbrance(session, session_id, user.id)
    session.commit()
    session.refresh(state)
    if updated_inventory_entry:
        session.refresh(updated_inventory_entry)
    if _tier_sell and _cs_sell:
        session.refresh(_cs_sell)
        await CombatService._emit_state(session_id, _cs_sell)

    refund_currency = {"copperValue": refund_cp}
    refund_label = _format_cp_label(refund_cp)
    session.add(
        create_session_command_event(
            session_id=session_id,
            user_id=user.id,
            member=member,
            command_type="shop_sale",
            payload_json={
                "itemId": sold_item_id,
                "itemName": sold_item_name,
                "quantity": payload.quantity,
                "amountLabel": refund_label,
            },
        )
    )
    session.commit()
    sale_timestamp = state.updated_at or state.created_at
    await publish_sale_realtime(
        entry,
        payload={
            "sessionId": require_identifier(entry.id, "Session is missing an id"),
            "campaignId": entry.campaign_id,
            "partyId": entry.party_id,
            "userId": user.id,
            "displayName": member.display_name,
            "itemId": sold_item_id,
            "itemName": sold_item_name,
            "quantity": payload.quantity,
            "refundCurrency": refund_currency,
            "refundLabel": refund_label,
            "createdAt": sale_timestamp.isoformat(),
        },
        timestamp=sale_timestamp,
    )
    await _publish_session_state_realtime(
        entry,
        user.id,
        sale_timestamp,
        state.state_json if isinstance(state.state_json, dict) else None,
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


def _build_condition_tag_event_payload(*, inventory_item: InventoryItem, item: Item, tag: str, action: str) -> dict:
    return {
        "inventoryItemId": require_identifier(inventory_item.id, "Inventory item is missing an id"),
        "itemId": inventory_item.item_id,
        "itemName": item.name,
        "tag": tag,
        "action": action,
    }


async def add_inventory_item_condition_tag_service(
    session_id: str,
    inventory_item_id: str,
    payload: InventoryConditionTagAdd,
    user,
    session: DbSession,
) -> InventoryRead:
    entry, _runtime = require_active_shop_session(session_id, session)
    member = _require_inventory_access(entry, user, session)
    inventory_item = session.exec(
        select(InventoryItem).where(
            InventoryItem.id == inventory_item_id,
            InventoryItem.campaign_id == entry.campaign_id,
            InventoryItem.party_id == entry.party_id,
        )
    ).first()
    if not inventory_item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    if member.role_mode != RoleMode.GM and inventory_item.member_id != require_identifier(member.id, "Campaign member is missing an id"):
        raise HTTPException(status_code=403, detail="Not allowed")

    tag = payload.tag.strip() if isinstance(payload.tag, str) else ""
    if tag not in ALLOWED_ITEM_CONDITION_TAGS:
        raise HTTPException(status_code=400, detail="Invalid item condition tag")

    next_tags, changed = add_item_condition_tag(inventory_item.condition_tags, tag)
    inventory_item.condition_tags = normalize_item_condition_tags(next_tags)
    session.add(inventory_item)

    item = session.exec(select(Item).where(Item.id == inventory_item.item_id)).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if changed:
        session.add(
            create_session_command_event(
                session_id=session_id,
                user_id=user.id,
                member=member,
                command_type="inventory_condition_tag_added",
                payload_json=_build_condition_tag_event_payload(
                    inventory_item=inventory_item,
                    item=item,
                    tag=tag,
                    action="add",
                ),
            )
        )
    session.commit()
    session.refresh(inventory_item)
    return to_inventory_read(inventory_item)


async def remove_inventory_item_condition_tag_service(
    session_id: str,
    inventory_item_id: str,
    tag: str,
    user,
    session: DbSession,
) -> InventoryRead:
    entry, _runtime = require_active_shop_session(session_id, session)
    member = _require_inventory_access(entry, user, session)
    inventory_item = session.exec(
        select(InventoryItem).where(
            InventoryItem.id == inventory_item_id,
            InventoryItem.campaign_id == entry.campaign_id,
            InventoryItem.party_id == entry.party_id,
        )
    ).first()
    if not inventory_item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    if member.role_mode != RoleMode.GM and inventory_item.member_id != require_identifier(member.id, "Campaign member is missing an id"):
        raise HTTPException(status_code=403, detail="Not allowed")

    normalized_tag = tag.strip()
    if normalized_tag not in ALLOWED_ITEM_CONDITION_TAGS:
        raise HTTPException(status_code=400, detail="Invalid item condition tag")
    next_tags, changed = remove_item_condition_tag(inventory_item.condition_tags, normalized_tag)
    inventory_item.condition_tags = normalize_item_condition_tags(next_tags)
    session.add(inventory_item)

    item = session.exec(select(Item).where(Item.id == inventory_item.item_id)).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if changed:
        session.add(
            create_session_command_event(
                session_id=session_id,
                user_id=user.id,
                member=member,
                command_type="inventory_condition_tag_removed",
                payload_json=_build_condition_tag_event_payload(
                    inventory_item=inventory_item,
                    item=item,
                    tag=normalized_tag,
                    action="remove",
                ),
            )
        )
    session.commit()
    session.refresh(inventory_item)
    return to_inventory_read(inventory_item)
