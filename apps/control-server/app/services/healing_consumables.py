from __future__ import annotations

from datetime import datetime, timezone
import random
from typing import Literal

from sqlmodel import Session, select

from app.models.campaign import RoleMode
from app.models.campaign_member import CampaignMember
from app.models.inventory import InventoryItem
from app.models.item import Item, ItemType
from app.models.party_member import PartyMember, PartyMemberStatus
from app.models.session import Session as CampaignSession
from app.services.inventory_expiration import is_inventory_item_expired
from app.services.centrifugo import centrifugo
from app.services.realtime import build_event, campaign_channel, event_version, session_channel
from app.services.session_state_finalize import finalize_session_state_data
from app.services.wild_shape_catalog import get_form
from app.services.wild_shape_service import (
    apply_healing_to_form,
    is_active as is_wild_shape_active,
)
from app.services.healing_consumables_types import (
    HealingConsumableApplication,
    HealingConsumableContext,
    HealingConsumableError,
    HealingConsumableRoll,
    HealingConsumableTargetSummary,
    _collect_target_user_ids,
    _ensure_player_session_state,
    _extract_hp_snapshot,
    _fetch_target_lookup_maps,
    _parse_heal_dice,
    _safe_int,
    build_consumable_used_payload,
    consume_inventory_item,
    get_actor_member,
    get_session_entry,
    record_consumable_used_activity,
    require_identifier,
)


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


def list_healing_consumable_targets(
    db: Session,
    *,
    session_entry: CampaignSession,
    actor_user_id: str,
) -> list[HealingConsumableTargetSummary]:
    unique_target_ids = _collect_target_user_ids(db, session_entry, actor_user_id)
    member_map, state_map, sheet_map = _fetch_target_lookup_maps(db, session_entry, unique_target_ids)

    targets: list[HealingConsumableTargetSummary] = []
    for user_id in unique_target_ids:
        member = member_map.get(user_id)
        if not member:
            continue
        state_payload = (
            state_map[user_id].state_json
            if user_id in state_map and isinstance(state_map[user_id].state_json, dict)
            else sheet_map[user_id].data if user_id in sheet_map and isinstance(sheet_map[user_id].data, dict) else {}
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
