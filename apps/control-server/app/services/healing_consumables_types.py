from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Literal
from uuid import uuid4

from sqlmodel import Session, select

from app.models.campaign import RoleMode
from app.models.campaign_member import CampaignMember
from app.models.character_sheet import CharacterSheet
from app.models.inventory import InventoryItem
from app.models.item import Item
from app.models.party_member import PartyMember, PartyMemberStatus
from app.models.session import Session as CampaignSession
from app.models.session_command_event import SessionCommandEvent
from app.models.session_state import SessionState
from app.services.session_state_finalize import finalize_session_state_data


class HealingConsumableError(Exception):
    def __init__(self, detail: str, status_code: int = 400):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


@dataclass
class HealingConsumableContext:
    session_entry: CampaignSession
    actor_member: CampaignMember
    inventory_item: InventoryItem
    item: Item


@dataclass
class HealingConsumableRoll:
    effect_dice: str | None
    effect_bonus: int
    effect_rolls: list[int]
    base_effect: int
    total_healing: int
    roll_source: Literal["system", "manual"]


@dataclass
class HealingConsumableTargetSummary:
    player_user_id: str
    display_name: str
    current_hp: int
    max_hp: int
    is_self: bool


@dataclass
class HealingConsumableApplication:
    target_user_id: str
    target_display_name: str
    previous_hp: int
    new_hp: int
    max_hp: int
    state_model: SessionState


def _parse_heal_dice(expression: str) -> tuple[int, int, int]:
    if not expression:
        return 0, 0, 0
    static_match = re.fullmatch(r"\s*(\d+)\s*", expression.lower())
    if static_match:
        return 0, 0, int(static_match.group(1))
    match = re.search(r"(\d+)d(\d+)\s*(?:([+-])\s*(\d+))?", expression.lower())
    if not match:
        return 0, 0, 0
    count = int(match.group(1))
    sides = int(match.group(2))
    mod = 0
    if match.group(3) and match.group(4):
        sign = 1 if match.group(3) == "+" else -1
        mod = sign * int(match.group(4))
    return count, sides, mod


def _safe_int(value: object, fallback: int = 0) -> int:
    return value if isinstance(value, int) else fallback


def require_identifier(value: str | None, detail: str) -> str:
    if value is None:
        raise HealingConsumableError(detail, 500)
    return value


def get_session_entry(db: Session, session_id: str) -> CampaignSession:
    session_entry = db.exec(
        select(CampaignSession).where(CampaignSession.id == session_id)
    ).first()
    if not session_entry:
        raise HealingConsumableError("Session not found", 404)
    return session_entry


def get_actor_member(
    db: Session,
    session_entry: CampaignSession,
    actor_user_id: str,
) -> CampaignMember:
    member = db.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == session_entry.campaign_id,
            CampaignMember.user_id == actor_user_id,
        )
    ).first()
    if not member:
        raise HealingConsumableError("Campaign member not found", 404)
    return member


def _ensure_player_session_state(
    db: Session,
    *,
    session_entry: CampaignSession,
    player_user_id: str,
) -> SessionState:
    session_id = require_identifier(session_entry.id, "Session is missing an id")
    state = db.exec(
        select(SessionState).where(
            SessionState.session_id == session_id,
            SessionState.player_user_id == player_user_id,
        )
    ).first()
    if state:
        if not isinstance(state.state_json, dict):
            state.state_json = {}
        state.state_json = finalize_session_state_data(dict(state.state_json))
        db.add(state)
        return state

    if not session_entry.party_id:
        raise HealingConsumableError("Session state not found", 404)

    base_sheet = db.exec(
        select(CharacterSheet).where(
            CharacterSheet.party_id == session_entry.party_id,
            CharacterSheet.player_user_id == player_user_id,
        )
    ).first()
    if not base_sheet or not isinstance(base_sheet.data, dict):
        raise HealingConsumableError("Character sheet not found", 404)

    state = SessionState(
        id=str(uuid4()),
        session_id=session_id,
        player_user_id=player_user_id,
        state_json=finalize_session_state_data(dict(base_sheet.data)),
        created_at=datetime.now(timezone.utc),
        updated_at=None,
    )
    db.add(state)
    db.flush()
    return state


def _extract_hp_snapshot(payload: dict | None) -> tuple[int, int]:
    data = payload if isinstance(payload, dict) else {}
    return (
        max(0, _safe_int(data.get("currentHP"), 0)),
        max(0, _safe_int(data.get("maxHP"), 0)),
    )


def consume_inventory_item(db: Session, inventory_item: InventoryItem) -> int:
    remaining_quantity = max(0, inventory_item.quantity - 1)
    if remaining_quantity > 0:
        inventory_item.quantity = remaining_quantity
        db.add(inventory_item)
    else:
        db.delete(inventory_item)
    return remaining_quantity


def _collect_target_user_ids(
    db: Session,
    session_entry: CampaignSession,
    actor_user_id: str,
) -> list[str]:
    target_user_ids: list[str] = []
    if session_entry.party_id:
        party_members = db.exec(
            select(PartyMember).where(
                PartyMember.party_id == session_entry.party_id,
                PartyMember.status == PartyMemberStatus.JOINED,
            )
        ).all()
        target_user_ids = [
            member.user_id
            for member in party_members
            if isinstance(member.user_id, str)
        ]
    else:
        campaign_members = db.exec(
            select(CampaignMember).where(
                CampaignMember.campaign_id == session_entry.campaign_id,
                CampaignMember.role_mode == RoleMode.PLAYER,
            )
        ).all()
        target_user_ids = [
            member.user_id
            for member in campaign_members
            if isinstance(member.user_id, str)
        ]

    unique_target_ids = list(dict.fromkeys(target_user_ids or [actor_user_id]))
    if actor_user_id not in unique_target_ids:
        unique_target_ids.insert(0, actor_user_id)
    return unique_target_ids


def _fetch_target_lookup_maps(
    db: Session,
    session_entry: CampaignSession,
    unique_target_ids: list[str],
) -> tuple[dict[str, CampaignMember], dict[str, SessionState], dict[str, CharacterSheet]]:
    members = db.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == session_entry.campaign_id,
            CampaignMember.user_id.in_(unique_target_ids),  # type: ignore[arg-type]
        )
    ).all()
    member_by_user_id = {
        member.user_id: member
        for member in members
        if isinstance(member.user_id, str)
    }

    session_states = db.exec(
        select(SessionState).where(
            SessionState.session_id == require_identifier(session_entry.id, "Session is missing an id"),
            SessionState.player_user_id.in_(unique_target_ids),  # type: ignore[arg-type]
        )
    ).all()
    state_by_user_id = {
        state.player_user_id: state
        for state in session_states
        if isinstance(state.player_user_id, str)
    }

    character_sheets = db.exec(
        select(CharacterSheet).where(
            CharacterSheet.party_id == session_entry.party_id,
            CharacterSheet.player_user_id.in_(unique_target_ids),  # type: ignore[arg-type]
        )
    ).all() if session_entry.party_id else []
    sheet_by_user_id = {
        sheet.player_user_id: sheet
        for sheet in character_sheets
        if isinstance(sheet.player_user_id, str)
    }
    return member_by_user_id, state_by_user_id, sheet_by_user_id


def build_consumable_used_payload(
    *,
    context: HealingConsumableContext,
    target_kind: Literal["player", "session_entity"],
    target_ref_id: str,
    target_display_name: str,
    healing: int,
    new_hp: int,
    remaining_quantity: int,
    roll: HealingConsumableRoll,
    target_user_id: str | None = None,
    previous_hp: int | None = None,
    max_hp: int | None = None,
    timestamp: datetime | None = None,
) -> dict:
    issued_at = timestamp or datetime.now(timezone.utc)
    return {
        "sessionId": require_identifier(context.session_entry.id, "Session is missing an id"),
        "campaignId": context.session_entry.campaign_id,
        "partyId": context.session_entry.party_id,
        "actorUserId": context.actor_member.user_id,
        "actorDisplayName": context.actor_member.display_name,
        "inventoryItemId": context.inventory_item.id,
        "itemId": context.item.id,
        "itemName": context.item.name,
        "consumedQuantity": 1,
        "remainingQuantity": remaining_quantity,
        "targetKind": target_kind,
        "targetRefId": target_ref_id,
        "targetUserId": target_user_id,
        "targetDisplayName": target_display_name,
        "healingApplied": healing,
        "newHp": new_hp,
        "previousHp": previous_hp,
        "maxHp": max_hp,
        "effectDice": roll.effect_dice,
        "effectBonus": roll.effect_bonus,
        "effectRolls": roll.effect_rolls,
        "baseEffect": roll.base_effect,
        "effectRollSource": roll.roll_source,
        "issuedAt": issued_at.isoformat(),
    }


def record_consumable_used_activity(
    db: Session,
    *,
    context: HealingConsumableContext,
    payload: dict,
    created_at: datetime | None = None,
) -> SessionCommandEvent:
    entry = SessionCommandEvent(
        id=str(uuid4()),
        session_id=require_identifier(context.session_entry.id, "Session is missing an id"),
        user_id=context.actor_member.user_id,
        member_id=require_identifier(context.actor_member.id, "Campaign member is missing an id"),
        actor_name=context.actor_member.display_name,
        command_type="use_consumable",
        payload_json=payload,
        created_at=created_at or datetime.now(timezone.utc),
    )
    db.add(entry)
    return entry
