from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlmodel import Session as DbSession, select

from app.models.character_sheet import CharacterSheet
from app.models.inventory import InventoryItem
from app.models.item import Item
from app.schemas.session_reward import (
    SessionGrantCurrencyRead,
    SessionGrantCurrencyRequest,
    SessionGrantItemRead,
    SessionGrantItemRequest,
    SessionGrantXpRead,
    SessionGrantXpRequest,
)
from app.services.character_progression import build_progression_snapshot, grant_experience
from app.services.magic_item_effects import inventory_item_supports_stacking
from app.services.money import normalize_money
from app.services.session_state_finalize import finalize_session_state_data
from ._shared import record_session_activity, require_identifier
from .rewards_common import (
    create_inventory_entry,
    get_active_party_session_for_gm,
    get_actor_member,
    get_target_member,
    inventory_read,
    merge_session_inventory,
    progression_int,
    progression_optional_int,
    publish_reward_realtime,
)
from .shop import (
    _ensure_player_session_state,
    _format_cp_label,
    _publish_session_state_realtime,
    _to_currency_read,
)


async def grant_session_currency_service(
    session_id: str,
    payload: SessionGrantCurrencyRequest,
    user,
    session: DbSession,
) -> SessionGrantCurrencyRead:
    entry, party = get_active_party_session_for_gm(session_id, user, session)
    actor_member = get_actor_member(entry, user.id, session)
    target_member = get_target_member(
        campaign_id=entry.campaign_id,
        party_id=require_identifier(party.id, "Party is missing an id"),
        player_user_id=payload.playerUserId,
        db=session,
    )

    granted_currency = {"copperValue": payload.copperValue}
    granted_cp = payload.copperValue
    if granted_cp <= 0:
        raise HTTPException(status_code=400, detail="Grant amount must be greater than zero")

    state = _ensure_player_session_state(entry, payload.playerUserId, session)
    current_cp = normalize_money(state.state_json.get("currency")).get("copperValue", 0)
    next_currency = {"copperValue": current_cp + granted_cp}
    state.state_json = finalize_session_state_data({**state.state_json, "currency": next_currency})
    session.add(state)

    issued_at = datetime.now(timezone.utc)
    record_session_activity(
        entry,
        "grant_currency",
        session,
        member_id=require_identifier(actor_member.id, "Campaign member is missing an id"),
        user_id=user.id,
        actor_name=actor_member.display_name,
        payload={
            "targetUserId": payload.playerUserId,
            "targetDisplayName": target_member.display_name,
            "amountLabel": _format_cp_label(granted_cp),
        },
        created_at=issued_at,
    )
    session.commit()
    session.refresh(state)

    state_version = state.updated_at or state.created_at
    event_payload = {
        "sessionId": require_identifier(entry.id, "Session is missing an id"),
        "campaignId": entry.campaign_id,
        "partyId": entry.party_id,
        "playerUserId": payload.playerUserId,
        "grantedCurrency": granted_currency,
        "currentCurrency": next_currency,
        "issuedAt": state_version.isoformat(),
    }
    await publish_reward_realtime(
        entry,
        event_type="gm_granted_currency",
        payload=event_payload,
        version_source=state_version,
    )
    await _publish_session_state_realtime(
        entry,
        payload.playerUserId,
        state_version,
        state.state_json if isinstance(state.state_json, dict) else None,
    )

    return SessionGrantCurrencyRead(
        playerUserId=payload.playerUserId,
        currentCurrency=_to_currency_read(next_currency),
        grantedCurrency=_to_currency_read(granted_currency),
    )


async def grant_session_item_service(
    session_id: str,
    payload: SessionGrantItemRequest,
    user,
    session: DbSession,
) -> SessionGrantItemRead:
    entry, party = get_active_party_session_for_gm(session_id, user, session)
    actor_member = get_actor_member(entry, user.id, session)
    target_member = get_target_member(
        campaign_id=entry.campaign_id,
        party_id=require_identifier(party.id, "Party is missing an id"),
        player_user_id=payload.playerUserId,
        db=session,
    )
    item = session.exec(
        select(Item).where(
            Item.id == payload.itemId,
            Item.campaign_id == entry.campaign_id,
        )
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    state = _ensure_player_session_state(entry, payload.playerUserId, session)
    state.state_json = finalize_session_state_data({
        **state.state_json,
        "inventory": merge_session_inventory(
            state.state_json.get("inventory"),
            item=item,
            quantity=payload.quantity,
            notes=payload.notes,
        ),
    })
    session.add(state)

    inventory_entry = session.exec(
        select(InventoryItem).where(
            InventoryItem.campaign_id == entry.campaign_id,
            InventoryItem.party_id == entry.party_id,
            InventoryItem.member_id == require_identifier(
                target_member.id,
                "Campaign member is missing an id",
            ),
            InventoryItem.item_id == require_identifier(item.id, "Item is missing an id"),
        )
    ).first()
    if inventory_entry and inventory_item_supports_stacking(item):
        inventory_entry.quantity += payload.quantity
        if payload.notes and not (inventory_entry.notes or "").strip():
            inventory_entry.notes = payload.notes
        session.add(inventory_entry)
    else:
        inventory_entry = create_inventory_entry(
            entry=entry,
            target_member=target_member,
            item=item,
            quantity=payload.quantity,
            notes=payload.notes,
        )
        session.add(inventory_entry)

    issued_at = datetime.now(timezone.utc)
    record_session_activity(
        entry,
        "grant_item",
        session,
        member_id=require_identifier(actor_member.id, "Campaign member is missing an id"),
        user_id=user.id,
        actor_name=actor_member.display_name,
        payload={
            "targetUserId": payload.playerUserId,
            "targetDisplayName": target_member.display_name,
            "itemName": item.name,
            "quantity": payload.quantity,
        },
        created_at=issued_at,
    )

    session.commit()
    session.refresh(state)
    session.refresh(inventory_entry)

    inventory_version = inventory_entry.updated_at or inventory_entry.created_at
    event_payload = {
        "sessionId": require_identifier(entry.id, "Session is missing an id"),
        "campaignId": entry.campaign_id,
        "partyId": entry.party_id,
        "playerUserId": payload.playerUserId,
        "itemId": require_identifier(item.id, "Item is missing an id"),
        "itemName": item.name,
        "quantity": payload.quantity,
        "inventoryItemId": require_identifier(
            inventory_entry.id,
            "Inventory item is missing an id",
        ),
        "issuedAt": inventory_version.isoformat(),
    }
    await publish_reward_realtime(
        entry,
        event_type="gm_granted_item",
        payload=event_payload,
        version_source=inventory_version,
    )
    await _publish_session_state_realtime(
        entry,
        payload.playerUserId,
        state.updated_at or state.created_at,
        state.state_json if isinstance(state.state_json, dict) else None,
    )

    return SessionGrantItemRead(
        playerUserId=payload.playerUserId,
        itemId=require_identifier(item.id, "Item is missing an id"),
        itemName=item.name,
        quantity=payload.quantity,
        inventoryItem=inventory_read(inventory_entry),
    )


async def grant_session_xp_service(
    session_id: str,
    payload: SessionGrantXpRequest,
    user,
    session: DbSession,
) -> SessionGrantXpRead:
    entry, party = get_active_party_session_for_gm(session_id, user, session)
    actor_member = get_actor_member(entry, user.id, session)
    target_member = get_target_member(
        campaign_id=entry.campaign_id,
        party_id=require_identifier(party.id, "Party is missing an id"),
        player_user_id=payload.playerUserId,
        db=session,
    )

    sheet = session.exec(
        select(CharacterSheet).where(
            CharacterSheet.party_id == require_identifier(party.id, "Party is missing an id"),
            CharacterSheet.player_user_id == payload.playerUserId,
        )
    ).first()
    if not sheet:
        raise HTTPException(status_code=404, detail="Character sheet not found")

    data = grant_experience(sheet.data, payload.amount)
    snapshot = build_progression_snapshot(data)
    current_xp = progression_int(snapshot.get("experiencePoints"))
    current_level = progression_int(snapshot.get("level"), 1)
    next_level_threshold = progression_optional_int(snapshot.get("nextLevelThreshold"))
    pending_level_up = bool(snapshot.get("pendingLevelUp", False))

    sheet.data = data
    session.add(sheet)
    state = _ensure_player_session_state(entry, payload.playerUserId, session)
    state.state_json = finalize_session_state_data({
        **state.state_json,
        "experiencePoints": current_xp,
        "level": current_level,
        "pendingLevelUp": pending_level_up,
    })
    session.add(state)

    issued_at = datetime.now(timezone.utc)
    record_session_activity(
        entry,
        "grant_xp",
        session,
        member_id=require_identifier(actor_member.id, "Campaign member is missing an id"),
        user_id=user.id,
        actor_name=actor_member.display_name,
        payload={
            "targetUserId": payload.playerUserId,
            "targetDisplayName": target_member.display_name,
            "amountLabel": f"{payload.amount} XP",
            "currentXp": current_xp,
            "nextLevelThreshold": next_level_threshold,
        },
        created_at=issued_at,
    )
    session.commit()
    session.refresh(sheet)
    session.refresh(state)

    sheet_version = sheet.updated_at or sheet.created_at
    event_payload = {
        "sessionId": require_identifier(entry.id, "Session is missing an id"),
        "campaignId": entry.campaign_id,
        "partyId": entry.party_id,
        "playerUserId": payload.playerUserId,
        "grantedAmount": payload.amount,
        "currentXp": current_xp,
        "currentLevel": current_level,
        "nextLevelThreshold": next_level_threshold,
        "issuedAt": sheet_version.isoformat(),
    }
    await publish_reward_realtime(
        entry,
        event_type="gm_granted_xp",
        payload=event_payload,
        version_source=sheet_version,
    )
    await _publish_session_state_realtime(
        entry,
        payload.playerUserId,
        state.updated_at or state.created_at,
        state.state_json if isinstance(state.state_json, dict) else None,
    )

    return SessionGrantXpRead(
        playerUserId=payload.playerUserId,
        grantedAmount=payload.amount,
        currentXp=current_xp,
        currentLevel=current_level,
        nextLevelThreshold=next_level_threshold,
    )
