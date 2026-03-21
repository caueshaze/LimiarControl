from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session as DbSession, select

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.campaign_member import CampaignMember
from app.models.character_sheet import CharacterSheet
from app.models.inventory import InventoryItem
from app.models.item import Item
from app.models.party import Party
from app.models.party_member import PartyMember, PartyMemberStatus
from app.models.session import Session, SessionStatus
from app.schemas.session_reward import (
    SessionGrantCurrencyRead,
    SessionGrantCurrencyRequest,
    SessionGrantItemRead,
    SessionGrantItemRequest,
    SessionGrantXpRead,
    SessionGrantXpRequest,
)
from app.services.character_progression import build_progression_snapshot, grant_experience
from app.services.centrifugo import centrifugo
from app.services.realtime import build_event, campaign_channel, event_version, session_channel

from ._shared import to_inventory_read
from .shop import (
    _cp_to_currency,
    _currency_to_cp,
    _ensure_player_session_state,
    _publish_session_state_realtime,
    _to_currency_read,
)

router = APIRouter()


def _get_active_party_session_for_gm(
    session_id: str,
    user,
    db: DbSession,
) -> tuple[Session, Party]:
    entry = db.exec(select(Session).where(Session.id == session_id)).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Session not found")
    if entry.status != SessionStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Session is not active")
    if not entry.party_id:
        raise HTTPException(status_code=400, detail="Session party is required")

    party = db.exec(select(Party).where(Party.id == entry.party_id)).first()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    if party.gm_user_id != user.id:
        raise HTTPException(status_code=403, detail="GM required")
    return entry, party


def _get_target_member(
    *,
    campaign_id: str,
    party_id: str,
    player_user_id: str,
    db: DbSession,
) -> CampaignMember:
    party_member = db.exec(
        select(PartyMember).where(
            PartyMember.party_id == party_id,
            PartyMember.user_id == player_user_id,
            PartyMember.status == PartyMemberStatus.JOINED,
        )
    ).first()
    if not party_member:
        raise HTTPException(status_code=404, detail="Player not found in party")

    campaign_member = db.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == campaign_id,
            CampaignMember.user_id == player_user_id,
        )
    ).first()
    if not campaign_member:
        raise HTTPException(status_code=404, detail="Campaign member not found")
    return campaign_member


def _merge_session_inventory(
    raw_inventory: object,
    *,
    item: Item,
    quantity: int,
    notes: str | None,
) -> list[dict]:
    entries = raw_inventory if isinstance(raw_inventory, list) else []
    normalized_target = _normalize_name(item.name)
    next_entries: list[dict] = []
    updated = False

    for raw_entry in entries:
        if not isinstance(raw_entry, dict):
            continue
        name = str(raw_entry.get("name", "")).strip()
        if name and _normalize_name(name) == normalized_target and not updated:
            merged = dict(raw_entry)
            merged["quantity"] = max(0, int(raw_entry.get("quantity", 0) or 0)) + quantity
            if item.weight is not None and raw_entry.get("weight") in (None, "", 0):
                merged["weight"] = item.weight
            if notes and not str(raw_entry.get("notes", "")).strip():
                merged["notes"] = notes
            next_entries.append(merged)
            updated = True
            continue
        next_entries.append(dict(raw_entry))

    if not updated:
        next_entries.append(
            {
                "id": f"grant-{uuid4()}",
                "name": item.name,
                "quantity": quantity,
                "weight": item.weight or 0,
                "notes": notes or "Granted by GM",
            }
        )

    return next_entries


def _normalize_name(value: str) -> str:
    return " ".join(value.lower().split())


async def _publish_reward_realtime(
    entry: Session,
    *,
    event_type: str,
    payload: dict,
    version_source,
) -> None:
    version = event_version(version_source)
    await centrifugo.publish(
        session_channel(entry.id),
        build_event(event_type, payload, version=version),
    )
    await centrifugo.publish(
        campaign_channel(entry.campaign_id),
        build_event(event_type, payload, version=version),
    )


@router.post(
    "/sessions/{session_id}/grants/currency",
    response_model=SessionGrantCurrencyRead,
)
async def grant_session_currency(
    session_id: str,
    payload: SessionGrantCurrencyRequest,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    entry, party = _get_active_party_session_for_gm(session_id, user, session)
    _get_target_member(
        campaign_id=entry.campaign_id,
        party_id=party.id,
        player_user_id=payload.playerUserId,
        db=session,
    )

    granted_currency = payload.currency.model_dump()
    granted_cp = _currency_to_cp(granted_currency)
    if granted_cp <= 0:
        raise HTTPException(status_code=400, detail="Grant amount must be greater than zero")

    state = _ensure_player_session_state(entry, payload.playerUserId, session)
    current_cp = _currency_to_cp(state.state_json.get("currency"))
    next_currency = _cp_to_currency(current_cp + granted_cp)
    state.state_json = {
        **state.state_json,
        "currency": next_currency,
    }
    session.add(state)
    session.commit()
    session.refresh(state)

    event_payload = {
        "sessionId": entry.id,
        "campaignId": entry.campaign_id,
        "partyId": entry.party_id,
        "playerUserId": payload.playerUserId,
        "grantedCurrency": granted_currency,
        "currentCurrency": next_currency,
        "issuedAt": (state.updated_at or state.created_at).isoformat(),
    }
    await _publish_reward_realtime(
        entry,
        event_type="gm_granted_currency",
        payload=event_payload,
        version_source=state.updated_at or state.created_at,
    )
    await _publish_session_state_realtime(
        entry,
        payload.playerUserId,
        state.updated_at or state.created_at,
    )

    return SessionGrantCurrencyRead(
        playerUserId=payload.playerUserId,
        currentCurrency=_to_currency_read(next_currency),
        grantedCurrency=_to_currency_read(granted_currency),
    )


@router.post(
    "/sessions/{session_id}/grants/item",
    response_model=SessionGrantItemRead,
)
async def grant_session_item(
    session_id: str,
    payload: SessionGrantItemRequest,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    entry, party = _get_active_party_session_for_gm(session_id, user, session)
    target_member = _get_target_member(
        campaign_id=entry.campaign_id,
        party_id=party.id,
        player_user_id=payload.playerUserId,
        db=session,
    )
    item = session.exec(
        select(Item).where(Item.id == payload.itemId, Item.campaign_id == entry.campaign_id)
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    state = _ensure_player_session_state(entry, payload.playerUserId, session)
    state.state_json = {
        **state.state_json,
        "inventory": _merge_session_inventory(
            state.state_json.get("inventory"),
            item=item,
            quantity=payload.quantity,
            notes=payload.notes,
        ),
    }
    session.add(state)

    inventory_entry = session.exec(
        select(InventoryItem).where(
            InventoryItem.campaign_id == entry.campaign_id,
            InventoryItem.party_id == entry.party_id,
            InventoryItem.member_id == target_member.id,
            InventoryItem.item_id == item.id,
        )
    ).first()
    if inventory_entry:
        inventory_entry.quantity += payload.quantity
        if payload.notes and not (inventory_entry.notes or "").strip():
            inventory_entry.notes = payload.notes
        session.add(inventory_entry)
    else:
        inventory_entry = InventoryItem(
            id=str(uuid4()),
            campaign_id=entry.campaign_id,
            party_id=entry.party_id,
            member_id=target_member.id,
            item_id=item.id,
            quantity=payload.quantity,
            is_equipped=False,
            notes=payload.notes or "Granted by GM",
        )
        session.add(inventory_entry)

    session.commit()
    session.refresh(state)
    session.refresh(inventory_entry)

    event_payload = {
        "sessionId": entry.id,
        "campaignId": entry.campaign_id,
        "partyId": entry.party_id,
        "playerUserId": payload.playerUserId,
        "itemId": item.id,
        "itemName": item.name,
        "quantity": payload.quantity,
        "inventoryItemId": inventory_entry.id,
        "issuedAt": (inventory_entry.updated_at or inventory_entry.created_at).isoformat(),
    }
    await _publish_reward_realtime(
        entry,
        event_type="gm_granted_item",
        payload=event_payload,
        version_source=inventory_entry.updated_at or inventory_entry.created_at,
    )
    await _publish_session_state_realtime(
        entry,
        payload.playerUserId,
        state.updated_at or state.created_at,
    )

    return SessionGrantItemRead(
        playerUserId=payload.playerUserId,
        itemId=item.id,
        itemName=item.name,
        quantity=payload.quantity,
        inventoryItem=to_inventory_read(inventory_entry),
    )


@router.post(
    "/sessions/{session_id}/grants/xp",
    response_model=SessionGrantXpRead,
)
async def grant_session_xp(
    session_id: str,
    payload: SessionGrantXpRequest,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    entry, party = _get_active_party_session_for_gm(session_id, user, session)
    _get_target_member(
        campaign_id=entry.campaign_id,
        party_id=party.id,
        player_user_id=payload.playerUserId,
        db=session,
    )

    sheet = session.exec(
        select(CharacterSheet).where(
            CharacterSheet.party_id == party.id,
            CharacterSheet.player_user_id == payload.playerUserId,
        )
    ).first()
    if not sheet:
        raise HTTPException(status_code=404, detail="Character sheet not found")

    data = grant_experience(sheet.data, payload.amount)
    snapshot = build_progression_snapshot(data)
    sheet.data = data
    session.add(sheet)
    state = _ensure_player_session_state(entry, payload.playerUserId, session)
    state.state_json = {
        **state.state_json,
        "experiencePoints": snapshot["experiencePoints"],
        "level": snapshot["level"],
        "pendingLevelUp": snapshot["pendingLevelUp"],
    }
    session.add(state)
    session.commit()
    session.refresh(sheet)
    session.refresh(state)

    event_payload = {
        "sessionId": entry.id,
        "campaignId": entry.campaign_id,
        "partyId": entry.party_id,
        "playerUserId": payload.playerUserId,
        "grantedAmount": payload.amount,
        "currentXp": snapshot["experiencePoints"],
        "currentLevel": snapshot["level"],
        "nextLevelThreshold": snapshot["nextLevelThreshold"],
        "issuedAt": (sheet.updated_at or sheet.created_at).isoformat(),
    }
    await _publish_reward_realtime(
        entry,
        event_type="gm_granted_xp",
        payload=event_payload,
        version_source=sheet.updated_at or sheet.created_at,
    )
    await _publish_session_state_realtime(
        entry,
        payload.playerUserId,
        state.updated_at or state.created_at,
    )

    return SessionGrantXpRead(
        playerUserId=payload.playerUserId,
        grantedAmount=payload.amount,
        currentXp=int(snapshot["experiencePoints"]),
        currentLevel=int(snapshot["level"]),
        nextLevelThreshold=(
            int(snapshot["nextLevelThreshold"])
            if snapshot["nextLevelThreshold"] is not None
            else None
        ),
    )
