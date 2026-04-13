from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import random
import re
from typing import Literal
from uuid import uuid4

from sqlmodel import Session, select

from app.models.campaign import RoleMode
from app.models.campaign_member import CampaignMember
from app.models.character_sheet import CharacterSheet
from app.models.inventory import InventoryItem
from app.models.item import Item, ItemType
from app.models.party_member import PartyMember, PartyMemberStatus
from app.models.session import Session as CampaignSession
from app.models.session_command_event import SessionCommandEvent
from app.models.session_state import SessionState
from app.services.inventory_expiration import is_inventory_item_expired
from app.services.centrifugo import centrifugo
from app.services.realtime import build_event, campaign_channel, event_version, session_channel
from app.services.session_state_finalize import finalize_session_state_data
from app.services.wild_shape_catalog import get_form
from app.services.wild_shape_service import (
    apply_healing_to_form,
    is_active as is_wild_shape_active,
)


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


def resolve_healing_consumable(
    db: Session,
    *,
    session_entry: CampaignSession,
    actor_user_id: str,
    inventory_item_id: str,
) -> HealingConsumableContext:
    actor_member = get_actor_member(db, session_entry, actor_user_id)
    actor_member_id = require_identifier(actor_member.id, "Campaign member is missing an id")

    inventory_item = db.exec(
        select(InventoryItem).where(
            InventoryItem.id == inventory_item_id,
            InventoryItem.campaign_id == session_entry.campaign_id,
            InventoryItem.member_id == actor_member_id,
        )
    ).first()
    if not inventory_item:
        raise HealingConsumableError("Inventory item not found for player", 404)
    if session_entry.party_id and inventory_item.party_id not in (None, session_entry.party_id):
        raise HealingConsumableError("Inventory item does not belong to this party", 404)
    if is_inventory_item_expired(inventory_item):
        db.delete(inventory_item)
        db.flush()
        raise HealingConsumableError("Consumable has expired", 400)
    if inventory_item.quantity < 1:
        raise HealingConsumableError("Consumable is out of stock", 400)

    item = db.exec(
        select(Item).where(
            Item.id == inventory_item.item_id,
            Item.campaign_id == session_entry.campaign_id,
        )
    ).first()
    if not item or item.type != ItemType.CONSUMABLE:
        raise HealingConsumableError("Inventory item is not a consumable", 400)
    if item.heal_dice is None and item.heal_bonus is None:
        raise HealingConsumableError("Consumable has no structured healing effect", 400)

    return HealingConsumableContext(
        session_entry=session_entry,
        actor_member=actor_member,
        inventory_item=inventory_item,
        item=item,
    )


def roll_healing_consumable(
    item: Item,
    *,
    roll_source: str = "system",
    manual_rolls: list[int] | None = None,
) -> HealingConsumableRoll:
    effect_dice = item.heal_dice
    effect_bonus = int(item.heal_bonus or 0)
    manual_values = manual_rolls or []

    if effect_dice is None:
        if roll_source == "manual" and manual_values:
            raise HealingConsumableError("Manual healing roll requires exactly 0 result(s).")
        return HealingConsumableRoll(
            effect_dice=None,
            effect_bonus=effect_bonus,
            effect_rolls=[],
            base_effect=0,
            total_healing=max(0, effect_bonus),
            roll_source="manual" if roll_source == "manual" else "system",
        )

    count, sides, expression_modifier = _parse_heal_dice(effect_dice)
    effective_count = count if count > 0 and sides > 0 else 0

    if roll_source == "manual":
        if len(manual_values) != effective_count:
            raise HealingConsumableError(
                f"Manual healing roll requires exactly {effective_count} result(s)."
            )
        for value in manual_values:
            if not isinstance(value, int) or value < 1 or value > sides:
                raise HealingConsumableError(
                    f"Manual healing roll values must be between 1 and {sides}."
                )
        effect_rolls = manual_values
    else:
        effect_rolls = [
            random.randint(1, sides) for _ in range(effective_count)
        ] if effective_count > 0 else []

    base_effect = max(0, sum(effect_rolls) + expression_modifier)
    return HealingConsumableRoll(
        effect_dice=effect_dice,
        effect_bonus=effect_bonus,
        effect_rolls=effect_rolls,
        base_effect=base_effect,
        total_healing=max(0, base_effect + effect_bonus),
        roll_source="manual" if roll_source == "manual" else "system",
    )


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


def apply_healing_outside_combat(
    db: Session,
    *,
    session_entry: CampaignSession,
    target_user_id: str,
    amount: int,
) -> HealingConsumableApplication:
    target_member = get_actor_member(db, session_entry, target_user_id)
    target_state = _ensure_player_session_state(
        db,
        session_entry=session_entry,
        player_user_id=target_user_id,
    )
    data = dict(target_state.state_json) if isinstance(target_state.state_json, dict) else {}
    previous_hp, max_hp = _extract_hp_snapshot(data)

    if is_wild_shape_active(data):
        form_key = (data.get("wildShape") or {}).get("formKey")
        form = get_form(form_key) if isinstance(form_key, str) else None
        if form is not None:
            data = apply_healing_to_form(data, amount, form)
            target_state.state_json = finalize_session_state_data(data)
            db.add(target_state)
            wild_shape = target_state.state_json.get("wildShape") if isinstance(target_state.state_json, dict) else {}
            new_hp = _safe_int(
                wild_shape.get("formCurrentHP") if isinstance(wild_shape, dict) else None,
                previous_hp,
            )
            return HealingConsumableApplication(
                target_user_id=target_user_id,
                target_display_name=target_member.display_name,
                previous_hp=previous_hp,
                new_hp=new_hp,
                max_hp=form.max_hp,
                state_model=target_state,
            )

    new_hp = min(max_hp, previous_hp + max(0, amount))
    data["currentHP"] = new_hp
    target_state.state_json = finalize_session_state_data(data)
    db.add(target_state)
    return HealingConsumableApplication(
        target_user_id=target_user_id,
        target_display_name=target_member.display_name,
        previous_hp=previous_hp,
        new_hp=new_hp,
        max_hp=max_hp,
        state_model=target_state,
    )


def consume_inventory_item(db: Session, inventory_item: InventoryItem) -> int:
    remaining_quantity = max(0, inventory_item.quantity - 1)
    if remaining_quantity > 0:
        inventory_item.quantity = remaining_quantity
        db.add(inventory_item)
    else:
        db.delete(inventory_item)
    return remaining_quantity


def list_healing_consumable_targets(
    db: Session,
    *,
    session_entry: CampaignSession,
    actor_user_id: str,
) -> list[HealingConsumableTargetSummary]:
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

    targets: list[HealingConsumableTargetSummary] = []
    for user_id in unique_target_ids:
        member = member_by_user_id.get(user_id)
        if not member:
            continue
        state_payload = (
            state_by_user_id[user_id].state_json
            if user_id in state_by_user_id and isinstance(state_by_user_id[user_id].state_json, dict)
            else sheet_by_user_id.get(user_id).data if user_id in sheet_by_user_id and isinstance(sheet_by_user_id[user_id].data, dict) else {}
        )
        current_hp, max_hp = _extract_hp_snapshot(state_payload if isinstance(state_payload, dict) else {})
        targets.append(
            HealingConsumableTargetSummary(
                player_user_id=user_id,
                display_name=member.display_name,
                current_hp=current_hp,
                max_hp=max_hp,
                is_self=user_id == actor_user_id,
            )
        )

    targets.sort(key=lambda target: (not target.is_self, target.display_name.lower()))
    return targets


def require_valid_healing_target(
    db: Session,
    *,
    session_entry: CampaignSession,
    actor_user_id: str,
    target_user_id: str,
) -> CampaignMember:
    allowed_target = db.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == session_entry.campaign_id,
            CampaignMember.user_id == target_user_id,
            CampaignMember.role_mode == RoleMode.PLAYER,
        )
    ).first()
    if not allowed_target:
        raise HealingConsumableError("Target player not found", 404)

    if session_entry.party_id:
        joined_target = db.exec(
            select(PartyMember).where(
                PartyMember.party_id == session_entry.party_id,
                PartyMember.user_id == target_user_id,
                PartyMember.status == PartyMemberStatus.JOINED,
            )
        ).first()
        if not joined_target:
            raise HealingConsumableError("Target player is not part of this active party", 403)

        joined_actor = db.exec(
            select(PartyMember).where(
                PartyMember.party_id == session_entry.party_id,
                PartyMember.user_id == actor_user_id,
                PartyMember.status == PartyMemberStatus.JOINED,
            )
        ).first()
        if not joined_actor:
            raise HealingConsumableError("Actor is not a joined party member", 403)

    return allowed_target


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


async def publish_consumable_used_realtime(
    session_entry: CampaignSession,
    *,
    payload: dict,
    timestamp: datetime,
) -> None:
    event = build_event(
        "consumable_used",
        payload,
        version=event_version(timestamp),
    )
    await centrifugo.publish(
        session_channel(require_identifier(session_entry.id, "Session is missing an id")),
        event,
    )
    await centrifugo.publish(
        campaign_channel(session_entry.campaign_id),
        event,
    )
