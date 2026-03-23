from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from fastapi import HTTPException
from sqlmodel import Session as DbSession, select

from app.models.campaign_member import CampaignMember
from app.models.inventory import InventoryItem
from app.models.item import Item
from app.models.party import Party
from app.models.party_member import PartyMember, PartyMemberStatus
from app.models.session import Session, SessionStatus
from app.services.centrifugo import centrifugo
from app.services.realtime import build_event, campaign_channel, event_version, session_channel
from ._shared import require_identifier, to_inventory_read


def get_active_party_session_for_gm(
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


def get_target_member(
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


def get_actor_member(entry: Session, user_id: str, db: DbSession) -> CampaignMember:
    member = db.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == entry.campaign_id,
            CampaignMember.user_id == user_id,
        )
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="Campaign member not found")
    return member


def normalize_name(value: str) -> str:
    return " ".join(value.lower().split())


def merge_session_inventory(
    raw_inventory: object,
    *,
    item: Item,
    quantity: int,
    notes: str | None,
) -> list[dict]:
    entries = raw_inventory if isinstance(raw_inventory, list) else []
    normalized_target = normalize_name(item.name)
    next_entries: list[dict] = []
    updated = False

    for raw_entry in entries:
        if not isinstance(raw_entry, dict):
            continue
        name = str(raw_entry.get("name", "")).strip()
        if name and normalize_name(name) == normalized_target and not updated:
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


async def publish_reward_realtime(
    entry: Session,
    *,
    event_type: str,
    payload: dict,
    version_source: datetime,
) -> None:
    version = event_version(version_source)
    built_event = build_event(event_type, payload, version=version)
    await centrifugo.publish(
        session_channel(require_identifier(entry.id, "Session is missing an id")),
        built_event,
    )
    await centrifugo.publish(campaign_channel(entry.campaign_id), built_event)


def create_inventory_entry(
    *,
    entry: Session,
    target_member: CampaignMember,
    item: Item,
    quantity: int,
    notes: str | None,
) -> InventoryItem:
    return InventoryItem(
        id=str(uuid4()),
        campaign_id=entry.campaign_id,
        party_id=entry.party_id,
        member_id=require_identifier(target_member.id, "Campaign member is missing an id"),
        item_id=require_identifier(item.id, "Item is missing an id"),
        quantity=quantity,
        is_equipped=False,
        notes=notes or "Granted by GM",
        created_at=datetime.now(),
        updated_at=None,
    )


def progression_int(value: int | bool | None, fallback: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    return fallback


def progression_optional_int(value: int | bool | None) -> int | None:
    if value is None:
        return None
    return progression_int(value)


def inventory_read(entry: InventoryItem):
    return to_inventory_read(entry)
