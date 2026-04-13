from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException
from sqlmodel import Session as DbSession, select

from app.models.campaign import RoleMode
from app.models.campaign_member import CampaignMember
from app.models.character_sheet import CharacterSheet
from app.models.inventory import InventoryItem
from app.models.item import Item, ItemType
from app.models.party import Party
from app.models.party_member import PartyMember, PartyMemberStatus
from app.models.session import Session, SessionStatus
from app.models.session_state import SessionState
from app.schemas.session_state import SessionStateRead
from app.services.centrifugo import centrifugo
from app.services.realtime import build_event, campaign_channel, event_version
from app.services.session_rest import ensure_rest_state
from app.services.session_state_finalize import finalize_session_state_data
from app.services.session_state_merge import merge_session_state_data
from ._shared import require_identifier

REQUIRED_SHEET_KEYS = {
    "name",
    "class",
    "level",
    "experiencePoints",
    "pendingLevelUp",
    "background",
    "playerName",
    "race",
    "alignment",
    "abilities",
    "savingThrowProficiencies",
    "skillProficiencies",
    "equippedArmor",
    "currency",
    "conditions",
}


def to_state_read(entry: SessionState) -> SessionStateRead:
    return SessionStateRead(
        id=require_identifier(entry.id, "Session state is missing an id"),
        sessionId=entry.session_id,
        playerUserId=entry.player_user_id,
        state=entry.state_json,
        createdAt=entry.created_at,
        updatedAt=entry.updated_at,
    )


async def publish_state_update(
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
                "sessionId": require_identifier(entry.id, "Session is missing an id"),
                "campaignId": entry.campaign_id,
                "partyId": entry.party_id,
                "playerUserId": player_user_id,
                "state": state_data,
            },
            version=event_version(timestamp),
        ),
    )


def get_session_entry(session_id: str, db: DbSession) -> Session:
    entry = db.exec(select(Session).where(Session.id == session_id)).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Session not found")
    if entry.status not in (SessionStatus.LOBBY, SessionStatus.ACTIVE):
        raise HTTPException(status_code=400, detail="Session is not active")
    return entry


def require_session_view_access(
    entry: Session,
    user,
    db: DbSession,
    player_user_id: str | None = None,
) -> None:
    if entry.party_id:
        party = db.exec(select(Party).where(Party.id == entry.party_id)).first()
        if not party:
            raise HTTPException(status_code=404, detail="Party not found")
        if party.gm_user_id == user.id:
            return

        member = db.exec(
            select(PartyMember).where(
                PartyMember.party_id == entry.party_id,
                PartyMember.user_id == user.id,
                PartyMember.status == PartyMemberStatus.JOINED,
            )
        ).first()
        if not member:
            raise HTTPException(status_code=403, detail="Not a party member")
        if player_user_id and player_user_id != user.id:
            raise HTTPException(status_code=403, detail="GM required")
        return

    campaign_member = db.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == entry.campaign_id,
            CampaignMember.user_id == user.id,
        )
    ).first()
    if not campaign_member:
        raise HTTPException(status_code=403, detail="Not a campaign member")
    if player_user_id and player_user_id != user.id and campaign_member.role_mode != RoleMode.GM:
        raise HTTPException(status_code=403, detail="GM required")


def require_session_gm(entry: Session, user, db: DbSession) -> None:
    if entry.party_id:
        party = db.exec(select(Party).where(Party.id == entry.party_id)).first()
        if not party or party.gm_user_id != user.id:
            raise HTTPException(status_code=403, detail="GM required")
        return

    campaign_member = db.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == entry.campaign_id,
            CampaignMember.user_id == user.id,
        )
    ).first()
    if not campaign_member or campaign_member.role_mode != RoleMode.GM:
        raise HTTPException(status_code=403, detail="GM required")


def seed_state_from_character_sheet(
    session_id: str,
    player_user_id: str,
    party_id: str | None,
    db: DbSession,
) -> SessionState | None:
    if not party_id:
        return None
    base_sheet = db.exec(
        select(CharacterSheet).where(
            CharacterSheet.party_id == party_id,
            CharacterSheet.player_user_id == player_user_id,
        )
    ).first()
    if not base_sheet:
        return None
    entry = SessionState(
        id=str(uuid4()),
        session_id=session_id,
        player_user_id=player_user_id,
        state_json=finalize_session_state_data(
            base_sheet.data if isinstance(base_sheet.data, dict) else {}
        ),
        created_at=datetime.now(timezone.utc),
        updated_at=None,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def ensure_session_state(
    state: SessionState | None,
    session_id: str,
    player_user_id: str,
    party_id: str | None,
    db: DbSession,
) -> SessionState | None:
    if not state:
        return seed_state_from_character_sheet(session_id, player_user_id, party_id, db)

    needs_base_merge = not (
        isinstance(state.state_json, dict)
        and REQUIRED_SHEET_KEYS.issubset(state.state_json.keys())
    )

    base_sheet_data: dict | None = None
    if needs_base_merge:
        base_sheet = db.exec(
            select(CharacterSheet).where(
                CharacterSheet.party_id == party_id,
                CharacterSheet.player_user_id == player_user_id,
            )
        ).first()
        if base_sheet and isinstance(base_sheet.data, dict):
            base_sheet_data = dict(base_sheet.data)

    merged_state = merge_session_state_data(
        state.state_json if isinstance(state.state_json, dict) else None,
        base_sheet_data,
    )
    merged_state = finalize_session_state_data(merged_state)
    if merged_state != state.state_json:
        state.state_json = merged_state
        db.add(state)
        db.commit()
        db.refresh(state)
    return state


def require_campaign_member(session_entry: Session, user, db: DbSession) -> CampaignMember:
    member = db.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == session_entry.campaign_id,
            CampaignMember.user_id == user.id,
        )
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Not a campaign member")
    return member


def resolve_owned_inventory_item(
    *,
    session_entry: Session,
    member: CampaignMember,
    db: DbSession,
    inventory_item_id: str | None,
    expected_type: ItemType,
    allow_shield: bool = True,
) -> tuple[InventoryItem, Item] | None:
    if not inventory_item_id:
        return None

    inventory_item = db.exec(
        select(InventoryItem).where(
            InventoryItem.id == inventory_item_id,
            InventoryItem.campaign_id == session_entry.campaign_id,
            InventoryItem.member_id == require_identifier(
                member.id,
                "Campaign member is missing an id",
            ),
        )
    ).first()
    if not inventory_item:
        raise HTTPException(status_code=400, detail="Inventory item not found for player")
    if session_entry.party_id and inventory_item.party_id not in (None, session_entry.party_id):
        raise HTTPException(status_code=400, detail="Inventory item does not belong to this party")

    item = db.exec(
        select(Item).where(
            Item.id == inventory_item.item_id,
            Item.campaign_id == session_entry.campaign_id,
        )
    ).first()
    if not item or item.type != expected_type:
        raise HTTPException(status_code=400, detail="Inventory item type is not valid for this slot")
    if expected_type == ItemType.ARMOR and not allow_shield and item.is_shield:
        raise HTTPException(status_code=400, detail="Shields are not valid for the armor slot")

    return inventory_item, item


def serialize_equipped_armor(item: Item | None) -> dict:
    if not item or item.type != ItemType.ARMOR or item.is_shield:
        return {
            "name": "None",
            "baseAC": 0,
            "dexCap": None,
            "armorType": "none",
            "allowsDex": True,
            "stealthDisadvantage": False,
            "minStrength": None,
        }

    armor_category = item.armor_category.value if item.armor_category else None
    dex_rule = (item.dex_bonus_rule or "").strip().lower()
    dex_cap = None
    if dex_rule == "max_2":
        dex_cap = 2
    elif dex_rule == "none":
        dex_cap = 0

    armor_type = armor_category if armor_category in {"light", "medium", "heavy"} else "none"
    if armor_type == "none":
        return {
            "name": "None",
            "baseAC": 0,
            "dexCap": None,
            "armorType": "none",
            "allowsDex": True,
            "stealthDisadvantage": False,
            "minStrength": None,
        }

    return {
        "name": item.name,
        "baseAC": int(item.armor_class_base or 0),
        "dexCap": dex_cap,
        "armorType": armor_type,
        "allowsDex": dex_rule != "none",
        "stealthDisadvantage": bool(item.stealth_disadvantage),
        "minStrength": int(item.strength_requirement) if isinstance(item.strength_requirement, int) else None,
    }
