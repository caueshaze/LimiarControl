from __future__ import annotations

from datetime import datetime, timezone
import random
from math import floor
from typing import Any
from uuid import uuid4

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session, select

from app.core.config import settings
from app.integrations import LimiarMapClient, LimiarMapClientError
from app.models.base_item import BaseItemKind, BaseItemWeaponRangeType
from app.models.campaign import Campaign, SystemType
from app.models.campaign_member import CampaignMember
from app.models.combat import CombatPhase, CombatState
from app.models.session import Session as CampaignSession
from app.models.session_entity import SessionEntity
from app.models.session_state import SessionState
from app.models.campaign_entity import CampaignEntity
from app.models.inventory import InventoryItem
from app.models.item import Item, ItemType
from app.schemas.combat import (
    CombatApplyDamageRequest,
    CombatApplyHealingRequest,
    CombatAreaPreviewRequest,
    CombatAttackRequest,
    CombatCastSpellRequest,
    CombatEntityActionRequest,
    CombatMapPreviewState,
    CombatResolveDamageRequest,
    CombatResolveSpellEffectRequest,
    CombatSetInitiativeRequest,
    CombatStartRequest,
)
from app.schemas.campaign_entity import (
    SKILL_ABILITY_MAP,
    CombatAction,
    ability_modifier as derive_ability_modifier,
    resolve_initiative_bonus as resolve_entity_initiative_bonus,
    resolve_saving_throw_bonus as resolve_entity_saving_throw_bonus,
    resolve_skill_bonus as resolve_entity_skill_bonus,
)
from app.services.base_items import get_base_item_by_canonical_key
from app.services.base_spells import get_base_spell_by_canonical_key
from app.services.centrifugo import centrifugo
from app.services.draconic_ancestry import resolve_elemental_affinity
from app.services.magic_item_effects import (
    consume_inventory_item_charge,
    get_magic_item_effect,
    get_inventory_item_charges_current,
    get_magic_item_spell_key,
)
from app.services.realtime import (
    build_event,
    campaign_channel,
    event_version,
    session_channel,
)
from app.services.session_state_finalize import finalize_session_state_data
from app.services.roll_resolution import resolve_attack_base, resolve_saving_throw
from app.schemas.roll import RollActorStats, RollResult

from ..combat_targeting import get_combat_targeting_service
from ..exceptions import CombatServiceError, _parse_dice
from ..targeting_requirements import (
    resolve_spell_targeting_requirements,
    resolve_weapon_targeting_requirements,
)
from ..targeting_intent import AreaTargetingIntent, SpellCastIntent, WeaponAttackIntent
from ..unit_conversion import meters_to_cells


class SpellContextMixin:
    def _resolve_player_inventory_spell_item(
        cls,
        db: Session,
        session_id: str,
        *,
        player_user_id: str,
        inventory_item_id: str,
    ) -> tuple[InventoryItem, Item, dict]:
        session_entry = db.exec(
            select(CampaignSession).where(CampaignSession.id == session_id)
        ).first()
        if not session_entry:
            raise CombatServiceError("Session not found.", 404)

        member = db.exec(
            select(CampaignMember).where(
                CampaignMember.campaign_id == session_entry.campaign_id,
                CampaignMember.user_id == player_user_id,
            )
        ).first()
        if not member or not member.id:
            raise CombatServiceError("Campaign member not found for this player.", 400)

        inventory_entry = db.exec(
            select(InventoryItem).where(
                InventoryItem.id == inventory_item_id,
                InventoryItem.campaign_id == session_entry.campaign_id,
                InventoryItem.member_id == member.id,
            )
        ).first()
        if not inventory_entry:
            raise CombatServiceError(
                "Magic item not found in the player's inventory.", 404
            )
        if session_entry.party_id is not None and inventory_entry.party_id not in (
            None,
            session_entry.party_id,
        ):
            raise CombatServiceError(
                "Magic item is not available in this session party.", 400
            )

        item = db.exec(
            select(Item).where(
                Item.id == inventory_entry.item_id,
                Item.campaign_id == session_entry.campaign_id,
            )
        ).first()
        if not item:
            raise CombatServiceError(
                "Catalog item for the magic item was not found.", 404
            )

        effect = get_magic_item_effect(item)
        if not effect or effect.get("type") != "cast_spell":
            raise CombatServiceError("This item cannot cast a spell.", 400)

        return inventory_entry, item, effect

    @classmethod
    def _get_target_hp_snapshot(
        cls,
        db: Session,
        session_id: str,
        target_ref_id: str,
        target_kind: str,
    ) -> tuple[int | None, int | None]:
        target_model, *_ = cls._get_stats(db, target_ref_id, target_kind, session_id)
        if target_kind == "player":
            data = cls._as_dict(target_model.state_json)
            return (
                cls._safe_int(data.get("currentHP"), 0),
                cls._safe_int(data.get("maxHP"), 0),
            )

        npc = db.exec(
            select(CampaignEntity).where(
                CampaignEntity.id == target_model.campaign_entity_id
            )
        ).first()
        max_hp = npc.max_hp if npc and npc.max_hp is not None else 0
        current_hp = (
            target_model.current_hp if target_model.current_hp is not None else max_hp
        )
        return current_hp, max_hp

    @classmethod
    def _consume_player_spell_slot(
        cls, attacker_model: SessionState, slot_level: int
    ) -> None:
        data = cls._as_dict(attacker_model.state_json)
        spellcasting = cls._as_dict(data.get("spellcasting"))
        slots = cls._as_dict(spellcasting.get("slots"))
        lvl_key = str(slot_level)
        slot_data = cls._as_dict(slots.get(lvl_key))
        if not slot_data:
            slot_data = {"used": 0, "max": 0}
        if slot_data.get("used", 0) >= slot_data.get("max", 0):
            raise CombatServiceError("No spell slots of this level remaining")
        slot_data["used"] = cls._safe_int(slot_data.get("used"), 0) + 1
        slots[lvl_key] = slot_data
        spellcasting["slots"] = slots
        data["spellcasting"] = spellcasting
        attacker_model.state_json = finalize_session_state_data(data)
        flag_modified(attacker_model, "state_json")

    @classmethod
    def _resolve_player_spell_context(
        cls,
        db: Session,
        session_id: str,
        attacker: dict,
        attacker_model: SessionState,
        req: CombatCastSpellRequest,
    ) -> dict:
        """Build the full mechanical spell context for a player cast.

        Authority model (Spell System Hardening):
        ─────────────────────────────────────────
        catalog_spell (CampaignSpell or BaseSpell) is the mechanical truth.
        It is resolved by _get_spell_catalog_entry_for_session(), which
        prefers CampaignSpell over BaseSpell for campaign play.

        player_spell (from character_sheet.spellcasting.spells[]) provides
        selection state only: known / prepared / learned status and the
        character's perceived spell level.  It does NOT override core
        mechanics (damage, save, range, etc.) from the catalog entry.

        The request (CombatCastSpellRequest) may provide explicit overrides
        for caster-derived values (save_dc, attack_bonus, dice_expression)
        that are character-specific rather than spell-specific.
        """
        attacker_data = cls._as_dict(attacker_model.state_json)
        inventory_item = None
        source_item = None
        source_kind = "spellcasting"
        source_item_name = None
        ignore_components = False
        no_free_hand_required = False

        if isinstance(req.inventory_item_id, str) and req.inventory_item_id.strip():
            source_kind = "magic_item"
            inventory_item, source_item, magic_effect = (
                cls._resolve_player_inventory_spell_item(
                    db,
                    session_id,
                    player_user_id=str(
                        attacker.get("actor_user_id") or attacker.get("ref_id") or ""
                    ).strip(),
                    inventory_item_id=req.inventory_item_id.strip(),
                )
            )
            requested_canonical_key = get_magic_item_spell_key(source_item)
            if (
                isinstance(req.spell_canonical_key, str)
                and req.spell_canonical_key.strip()
                and requested_canonical_key
                and req.spell_canonical_key.strip().lower() != requested_canonical_key
            ):
                raise CombatServiceError(
                    "Selected spell does not match the magic item.", 400
                )
            source_item_name = source_item.name
            ignore_components = bool(magic_effect.get("ignoreComponents"))
            no_free_hand_required = bool(magic_effect.get("noFreeHandRequired"))
        else:
            requested_canonical_key = (
                req.spell_canonical_key.strip()
                if isinstance(req.spell_canonical_key, str)
                and req.spell_canonical_key.strip()
                else (
                    req.spell_id.strip()
                    if isinstance(req.spell_id, str) and req.spell_id.strip()
                    else None
                )
            )
        if not requested_canonical_key:
            raise CombatServiceError("Spell canonical key is required.", 400)

        catalog_spell = cls._get_spell_catalog_entry_for_session(
            db, session_id, requested_canonical_key
        )
        spell_name = (
            catalog_spell.name_pt or catalog_spell.name_en or requested_canonical_key
        )
        if source_kind == "magic_item":
            player_spell = None
            spell_level = cls._safe_int(
                cls._as_dict(source_item.magic_effect_json).get("castLevel"),
                catalog_spell.level,
            )
        else:
            player_spell = cls._resolve_player_spell_entry(
                attacker_data,
                spell_canonical_key=catalog_spell.canonical_key
                or requested_canonical_key,
                spell_name=spell_name,
                campaign_spell_id=req.campaign_spell_id or None,
            )

            spell_level = cls._safe_int(player_spell.get("level"), catalog_spell.level)
            if spell_level > 0 and player_spell.get("prepared") is False:
                raise CombatServiceError("Spell is not prepared.", 400)

        _, _, _, _, prof_bonus, spell_mod = cls._get_stats(
            db, attacker["ref_id"], attacker["kind"], session_id
        )
        catalog_resolution = getattr(catalog_spell, "resolution_type", None)
        catalog_spell_mode = cls._map_resolution_type_to_spell_mode(catalog_resolution)
        automation_default_mode = cls._spell_default_mode_override(
            catalog_spell.canonical_key or requested_canonical_key
        )
        requires_effect_payload = cls._spell_requires_effect_payload(
            catalog_spell.canonical_key or requested_canonical_key
        )
        catalog_save_ability = cls._normalize_ability_name(catalog_spell.saving_throw)
        legacy_mode = (
            "heal" if req.is_heal else ("spell_attack" if req.is_attack else None)
        )
        spell_mode = (
            req.spell_mode
            or automation_default_mode
            or catalog_spell_mode
            or legacy_mode
            or ("saving_throw" if catalog_save_ability else None)
        )
        if spell_mode not in (
            "spell_attack",
            "saving_throw",
            "direct_damage",
            "heal",
            "utility",
        ):
            raise CombatServiceError("Spell cast mode is required for this spell.", 400)
        if spell_mode == "direct_damage" and catalog_save_ability:
            raise CombatServiceError(
                "This spell is structured as a saving throw spell. "
                "direct_damage is only allowed as an explicit fallback for spells without attack/save automation.",
                400,
            )
        targeting_requirements = resolve_spell_targeting_requirements(
            catalog_spell,
            spell_mode=spell_mode,
        )

        slot_level = None
        if spell_level > 0:
            if source_kind == "magic_item":
                slot_level = spell_level
            else:
                slot_level = req.slot_level or spell_level
                if slot_level < spell_level:
                    raise CombatServiceError(
                        "Spell slot level cannot be lower than the spell level.", 400
                    )
        action_cost = cls._resolve_spell_action_cost(
            getattr(catalog_spell, "casting_time_type", None)
        )

        legacy_expression = (
            req.dice_expression.strip()
            if isinstance(req.dice_expression, str) and req.dice_expression.strip()
            else None
        )

        effect_kind = (
            None
            if spell_mode == "utility"
            else ("healing" if spell_mode == "heal" else "damage")
        )
        effect_dice = None
        effect_bonus = 0
        damage_type = None
        save_ability = None
        save_dc = None
        save_success_outcome = None
        attack_bonus = None

        if spell_mode == "heal":
            effect_dice = catalog_spell.heal_dice
            if not isinstance(effect_dice, str) or not effect_dice.strip():
                effect_dice = req.heal_dice or (
                    legacy_expression if req.is_heal else None
                )
            # heal_bonus is derived from the caster, not the spell catalog
            effect_bonus = req.heal_bonus if isinstance(req.heal_bonus, int) else 0
        elif spell_mode != "utility":
            effect_dice = catalog_spell.damage_dice
            if not isinstance(effect_dice, str) or not effect_dice.strip():
                effect_dice = req.damage_dice or (
                    legacy_expression if not req.is_heal else None
                )
            # damage_bonus is derived from the caster, not the spell catalog
            effect_bonus = req.damage_bonus if isinstance(req.damage_bonus, int) else 0
            should_require_damage_type = bool(
                requires_effect_payload or effect_dice or effect_bonus > 0
            )
            damage_type = cls._normalize_damage_type(
                catalog_spell.damage_type or req.damage_type
            )
            if should_require_damage_type and not damage_type:
                raise CombatServiceError(
                    "Spell damage type is missing a structured value.", 400
                )

        if isinstance(effect_dice, str):
            effect_dice = effect_dice.strip() or None
        if effect_dice:
            count, sides, _ = _parse_dice(effect_dice)
            if count <= 0 or sides <= 0:
                raise CombatServiceError(
                    "Spell effect dice must use a valid dice expression.", 400
                )
        elif spell_mode != "utility" and requires_effect_payload and effect_bonus <= 0:
            raise CombatServiceError(
                "Spell effect is missing structured dice or a fixed bonus.", 400
            )

        if spell_mode == "spell_attack":
            # spell_attack_bonus is derived from the caster (spell_mod + prof_bonus),
            # not from the spell catalog; the request can override it explicitly.
            attack_bonus = (
                req.spell_attack_bonus
                if isinstance(req.spell_attack_bonus, int)
                else None
            )
            if not isinstance(attack_bonus, int):
                attack_bonus = spell_mod + prof_bonus
        elif spell_mode == "saving_throw":
            save_ability = cls._normalize_ability_name(
                req.save_ability or catalog_save_ability
            )
            # save_dc is derived from the caster (8 + prof + spell_mod),
            # not from the spell catalog; the request can override it explicitly.
            save_dc = req.save_dc if isinstance(req.save_dc, int) else None
            if not isinstance(save_dc, int):
                save_dc = 8 + prof_bonus + spell_mod
            save_success_outcome = (
                cls._normalize_save_success_outcome(catalog_spell.save_success_outcome)
                or "none"
            )
            if not save_ability or save_dc <= 0:
                raise CombatServiceError(
                    "Saving throw spells require save ability and save DC.", 400
                )

        structured_upcast = cls._get_structured_spell_upcast(
            getattr(catalog_spell, "upcast_json", None)
        )
        upcast_result = cls._apply_structured_spell_upcast(
            spell_level=spell_level,
            slot_level=slot_level,
            effect_kind=effect_kind,
            effect_dice=effect_dice,
            effect_bonus=effect_bonus,
            upcast=structured_upcast,
        )
        effect_dice = (
            upcast_result["effect_dice"]
            if isinstance(upcast_result.get("effect_dice"), str)
            or upcast_result.get("effect_dice") is None
            else effect_dice
        )
        effect_bonus = cls._safe_int(upcast_result.get("effect_bonus"), effect_bonus)
        elemental_affinity = resolve_elemental_affinity(
            attacker_data,
            damage_type,
        )

        return {
            "spell_name": spell_name,
            "spell_canonical_key": catalog_spell.canonical_key
            or requested_canonical_key,
            "spell_mode": spell_mode,
            "target_mode": getattr(catalog_spell, "target_mode", None),
            "range_meters": getattr(catalog_spell, "range_meters", None),
            "area_size_meters": getattr(catalog_spell, "area_size_meters", None),
            "requires_target_sight": targeting_requirements.requires_target_sight,
            "requires_target_effect": targeting_requirements.requires_target_effect,
            "requires_point_sight": targeting_requirements.requires_point_sight,
            "requires_point_effect": targeting_requirements.requires_point_effect,
            "effect_kind": effect_kind,
            "effect_dice": effect_dice,
            "effect_bonus": effect_bonus,
            "damage_type": damage_type,
            "save_ability": save_ability,
            "save_dc": save_dc,
            "save_success_outcome": save_success_outcome,
            "cover_applies_to_save": getattr(
                catalog_spell, "cover_applies_to_save", None
            ),
            "attack_bonus": attack_bonus,
            "slot_level": slot_level,
            "action_cost": action_cost,
            "upcast": structured_upcast,
            "upcast_applied": bool(upcast_result.get("upcast_applied")),
            "upcast_levels": cls._safe_int(upcast_result.get("upcast_levels"), 0),
            "elemental_affinity_eligible": bool(elemental_affinity.get("eligible")),
            "elemental_affinity_damage_type": elemental_affinity.get("damageType"),
            "elemental_affinity_bonus": elemental_affinity.get("bonus"),
            "source_kind": source_kind,
            "source_item_name": source_item_name,
            "inventory_item": inventory_item,
            "inventory_item_id": getattr(inventory_item, "id", None),
            "ignore_components": ignore_components,
            "no_free_hand_required": no_free_hand_required,
            "source_item": source_item,
        }
