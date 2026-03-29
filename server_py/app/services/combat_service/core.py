from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
import random
from math import floor
import unicodedata
from uuid import uuid4

from sqlalchemy import func
from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session, select

from app.models.base_item import BaseItemKind, BaseItemWeaponRangeType
from app.models.campaign import Campaign, SystemType
from app.models.campaign_member import CampaignMember
from app.models.campaign_spell import CampaignSpell
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
    CombatAttackRequest,
    CombatCastSpellRequest,
    CombatEntityActionRequest,
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
from app.services.realtime import build_event, campaign_channel, event_version, session_channel
from app.services.session_state_finalize import calculate_player_armor_class_from_state
from app.schemas.roll import RollActorStats

from .exceptions import CombatServiceError, _parse_dice, _roll_dice_expression


class CombatCoreMixin:
    _PLAYER_SHIELD_BONUS = 2
    _SAVE_SUCCESS_OUTCOME_VALUES = {"none", "half_damage"}
    _COMBAT_SPELL_ACTION_COSTS = {"action", "bonus_action", "reaction"}
    _RESOLUTION_TYPE_TO_SPELL_MODE: dict[str, str] = {
        "spell_attack": "spell_attack",
        "saving_throw": "saving_throw",
        "heal": "heal",
        "automatic": "direct_damage",
        "utility": "utility",
        "buff": "utility",
    }

    @classmethod
    def _map_resolution_type_to_spell_mode(cls, resolution_type: object) -> str | None:
        if not isinstance(resolution_type, str):
            return None
        return cls._RESOLUTION_TYPE_TO_SPELL_MODE.get(resolution_type)

    @classmethod
    def _resolve_spell_action_cost(cls, casting_time_type: object) -> str:
        normalized = cls._normalize_lookup(casting_time_type).replace(" ", "_")
        if not normalized:
            return "action"
        if normalized in cls._COMBAT_SPELL_ACTION_COSTS:
            return normalized
        raise CombatServiceError(
            "This spell cannot be cast through the combat action flow because its casting time is longer than a combat action.",
            400,
        )

    @classmethod
    def _get_structured_spell_upcast(cls, raw_upcast: object) -> dict | None:
        if not isinstance(raw_upcast, dict):
            return None
        mode = raw_upcast.get("mode")
        if not isinstance(mode, str) or not mode.strip():
            return None
        normalized: dict[str, object] = {"mode": mode.strip()}
        dice = raw_upcast.get("dice")
        if isinstance(dice, str) and dice.strip():
            normalized["dice"] = dice.strip()
        flat = raw_upcast.get("flat")
        if isinstance(flat, int):
            normalized["flat"] = flat
        per_level = raw_upcast.get("perLevel")
        if isinstance(per_level, int) and per_level > 0:
            normalized["perLevel"] = per_level
        max_level = raw_upcast.get("maxLevel")
        if isinstance(max_level, int) and max_level > 0:
            normalized["maxLevel"] = max_level
        return normalized

    @classmethod
    def _build_dice_expression(cls, count: int, sides: int, modifier: int) -> str | None:
        if count <= 0:
            return str(modifier) if modifier else None
        expression = f"{count}d{sides}"
        if modifier > 0:
            expression += f"+{modifier}"
        elif modifier < 0:
            expression += str(modifier)
        return expression

    @classmethod
    def _merge_dice_expressions(
        cls,
        base_expression: str | None,
        extra_expression: str | None,
        repeats: int = 1,
    ) -> str | None:
        if repeats <= 0 or not isinstance(extra_expression, str) or not extra_expression.strip():
            return base_expression

        base_count, base_sides, base_mod = _parse_dice(base_expression or "")
        extra_count, extra_sides, extra_mod = _parse_dice(extra_expression)
        if extra_count <= 0 and extra_mod == 0:
            return base_expression

        scaled_count = extra_count * repeats
        scaled_mod = extra_mod * repeats

        if base_count > 0 and scaled_count > 0 and base_sides != extra_sides:
            raise CombatServiceError(
                "Structured upcast dice must use the same die size as the base spell effect.",
                400,
            )

        total_sides = base_sides or extra_sides
        total_count = base_count + scaled_count
        total_mod = base_mod + scaled_mod
        return cls._build_dice_expression(total_count, total_sides, total_mod)

    @classmethod
    def _apply_structured_spell_upcast(
        cls,
        *,
        spell_level: int,
        slot_level: int | None,
        effect_kind: str | None,
        effect_dice: str | None,
        effect_bonus: int,
        upcast: dict | None,
    ) -> dict[str, object]:
        if (
            slot_level is None
            or spell_level <= 0
            or slot_level <= spell_level
            or not isinstance(upcast, dict)
        ):
            return {
                "effect_dice": effect_dice,
                "effect_bonus": effect_bonus,
                "upcast_levels": 0,
                "upcast_applied": False,
            }

        mode = str(upcast.get("mode") or "").strip()
        if not mode or mode == "custom":
            return {
                "effect_dice": effect_dice,
                "effect_bonus": effect_bonus,
                "upcast_levels": 0,
                "upcast_applied": False,
            }

        max_level = upcast.get("maxLevel")
        effective_slot_level = (
            min(slot_level, max_level)
            if isinstance(max_level, int) and max_level > 0
            else slot_level
        )
        extra_levels = max(0, effective_slot_level - spell_level)
        if extra_levels <= 0:
            return {
                "effect_dice": effect_dice,
                "effect_bonus": effect_bonus,
                "upcast_levels": 0,
                "upcast_applied": False,
            }

        per_level = upcast.get("perLevel")
        repeats = extra_levels * (per_level if isinstance(per_level, int) and per_level > 0 else 1)
        dice = upcast.get("dice") if isinstance(upcast.get("dice"), str) else None
        flat = upcast.get("flat") if isinstance(upcast.get("flat"), int) else 0

        if mode == "add_heal" and effect_kind != "healing":
            return {
                "effect_dice": effect_dice,
                "effect_bonus": effect_bonus,
                "upcast_levels": 0,
                "upcast_applied": False,
            }
        if mode == "add_damage" and effect_kind == "healing":
            return {
                "effect_dice": effect_dice,
                "effect_bonus": effect_bonus,
                "upcast_levels": 0,
                "upcast_applied": False,
            }

        next_effect_dice = effect_dice
        next_effect_bonus = effect_bonus

        if mode in {"add_damage", "add_heal", "increase_targets"}:
            if dice:
                next_effect_dice = cls._merge_dice_expressions(
                    effect_dice,
                    dice,
                    repeats,
                )
            if flat:
                next_effect_bonus += flat * repeats

        return {
            "effect_dice": next_effect_dice,
            "effect_bonus": next_effect_bonus,
            "upcast_levels": extra_levels,
            "upcast_applied": next_effect_dice != effect_dice or next_effect_bonus != effect_bonus,
        }

    _SPECIFIC_WEAPON_PROFICIENCY_ALIASES = {
        "club": ("clava", "clavas", "club", "clubs"),
        "dagger": ("adaga", "adagas", "dagger", "daggers"),
        "dart": ("dardo", "dardos", "dart", "darts"),
        "hand_crossbow": ("besta de mao", "bestas de mao", "hand crossbow", "hand crossbows"),
        "javelin": ("azagaia", "azagaias", "javelin", "javelins"),
        "light_crossbow": ("besta leve", "bestas leves", "light crossbow", "light crossbows"),
        "longsword": ("espada longa", "espadas longas", "longsword", "longswords"),
        "mace": ("maca", "macas", "maça", "maças", "mace", "maces"),
        "quarterstaff": ("cajado", "cajados", "quarterstaff", "quarterstaffs", "staff"),
        "rapier": ("rapieira", "rapieiras", "rapier", "rapiers"),
        "scimitar": ("cimitarra", "cimitarras", "scimitar", "scimitars"),
        "shortsword": ("espada curta", "espadas curtas", "shortsword", "shortswords"),
        "sickle": ("foice", "foices", "sickle", "sickles"),
        "sling": ("funda", "fundas", "sling", "slings"),
        "spear": ("lanca", "lancas", "lança", "lanças", "spear", "spears"),
    }

    @classmethod
    def _normalize_lookup(cls, value: object) -> str:
        if isinstance(value, Enum):
            value = value.value
        if not isinstance(value, str):
            return ""
        normalized = unicodedata.normalize("NFD", value.strip().lower())
        normalized = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
        normalized = normalized.replace("_", " ").replace("-", " ")
        return " ".join(normalized.split())

    @classmethod
    def _safe_optional_int(cls, value: object) -> int | None:
        return value if isinstance(value, int) else None

    @classmethod
    def _normalize_class_id(cls, value: object) -> str:
        return str(value or "").strip().lower()

    @classmethod
    def _get_player_class_feature_ids(cls, data: dict | None) -> set[str]:
        raw_features = cls._as_dict(data).get("classFeatures") if isinstance(data, dict) else None
        if not isinstance(raw_features, list):
            return set()
        return {
            str(feature.get("id"))
            for feature in raw_features
            if isinstance(feature, dict) and isinstance(feature.get("id"), str)
        }

    @classmethod
    def _get_player_fighting_style(cls, data: dict | None) -> str | None:
        payload = cls._as_dict(data)
        fighting_style = payload.get("fightingStyle")
        if isinstance(fighting_style, str) and fighting_style.strip():
            return fighting_style.strip().lower()

        class_id = cls._normalize_class_id(payload.get("class"))
        level = cls._safe_int(payload.get("level"), 1)
        if class_id == "guardian" and level >= 2:
            return "archery"
        return None

    @classmethod
    def _player_has_colossus_slayer(cls, data: dict | None) -> bool:
        payload = cls._as_dict(data)
        feature_ids = cls._get_player_class_feature_ids(payload)
        if "hunter_colossus_slayer" in feature_ids:
            return True
        class_id = cls._normalize_class_id(payload.get("class"))
        subclass = cls._normalize_class_id(payload.get("subclass"))
        level = cls._safe_int(payload.get("level"), 1)
        return class_id == "guardian" and subclass == "hunter" and level >= 3

    @classmethod
    def _normalize_save_success_outcome(cls, value: object) -> str | None:
        normalized = cls._normalize_lookup(value).replace(" ", "_")
        if normalized in cls._SAVE_SUCCESS_OUTCOME_VALUES:
            return normalized
        return None

    @classmethod
    def _resolve_save_damage_amount(
        cls,
        rolled_amount: int,
        *,
        is_saved: bool,
        save_success_outcome: object,
    ) -> int:
        total = max(0, rolled_amount)
        if not is_saved:
            return total
        if cls._normalize_save_success_outcome(save_success_outcome) == "half_damage":
            return floor(total / 2)
        return 0

    @classmethod
    def _get_player_ability_score(cls, data: dict, ability_name: str, default: int = 10) -> int:
        abilities = cls._as_dict(data.get("abilities"))
        value = abilities.get(ability_name)
        return value if isinstance(value, int) else default

    @classmethod
    def _get_player_legacy_weapon_profile(cls, data: dict, item: Item) -> dict | None:
        raw_weapons = data.get("weapons")
        if not isinstance(raw_weapons, list):
            return None

        candidates = {
            cls._normalize_lookup(item.name),
            cls._normalize_lookup(item.name_en_snapshot),
            cls._normalize_lookup(item.name_pt_snapshot),
            cls._normalize_lookup(item.canonical_key_snapshot),
        }
        canonical_slug = cls._normalize_lookup(item.canonical_key_snapshot).replace(" ", "_")
        if canonical_slug:
            candidates.update(
                cls._normalize_lookup(alias)
                for alias in cls._SPECIFIC_WEAPON_PROFICIENCY_ALIASES.get(canonical_slug, ())
            )
        candidates.discard("")
        if not candidates:
            return None

        for raw_weapon in raw_weapons:
            if not isinstance(raw_weapon, dict):
                continue
            if cls._normalize_lookup(raw_weapon.get("name")) in candidates:
                return raw_weapon
        return None

    @classmethod
    def _is_player_weapon_proficient(
        cls,
        data: dict,
        item: Item,
        legacy_weapon: dict | None = None,
    ) -> bool:
        raw_proficiencies = data.get("weaponProficiencies")
        proficiency_entries = raw_proficiencies if isinstance(raw_proficiencies, list) else []
        proficiencies = {
            cls._normalize_lookup(entry)
            for entry in proficiency_entries
            if isinstance(entry, str)
        }
        category = cls._normalize_lookup(item.weapon_category)
        if category == "simple" and ("simple" in proficiencies or "simples" in proficiencies):
            return True
        if category == "martial" and ("martial" in proficiencies or "marciais" in proficiencies):
            return True

        candidates = {
            cls._normalize_lookup(item.name),
            cls._normalize_lookup(item.name_en_snapshot),
            cls._normalize_lookup(item.name_pt_snapshot),
        }
        canonical_slug = cls._normalize_lookup(item.canonical_key_snapshot).replace(" ", "_")
        if canonical_slug:
            for alias in cls._SPECIFIC_WEAPON_PROFICIENCY_ALIASES.get(canonical_slug, ()):
                candidates.add(cls._normalize_lookup(alias))

        for candidate in candidates:
            if candidate and candidate in proficiencies:
                return True

        return bool(legacy_weapon and legacy_weapon.get("proficient") is True)

    @classmethod
    def _choose_player_weapon_ability(
        cls,
        data: dict,
        item: Item,
        legacy_weapon: dict | None = None,
    ) -> str:
        properties = {cls._normalize_lookup(value) for value in (item.properties or [])}
        if "finesse" in properties:
            strength_mod = cls._ability_modifier(cls._get_player_ability_score(data, "strength"))
            dexterity_mod = cls._ability_modifier(cls._get_player_ability_score(data, "dexterity"))
            return "dexterity" if dexterity_mod >= strength_mod else "strength"

        if cls._normalize_lookup(item.weapon_range_type) == "ranged":
            return "dexterity"

        legacy_ability = cls._normalize_lookup((legacy_weapon or {}).get("ability"))
        if legacy_ability in cls._ENTITY_ABILITY_ALIASES:
            return legacy_ability

        return "strength"

    @classmethod
    def _resolve_player_weapon_item(
        cls,
        db: Session,
        session_id: str,
        player_user_id: str,
        inventory_item_id: str,
    ) -> tuple[InventoryItem, Item]:
        session_entry = db.exec(
            select(CampaignSession).where(CampaignSession.id == session_id)
        ).first()
        if not session_entry:
            raise CombatServiceError("Session not found", 404)

        member = db.exec(
            select(CampaignMember).where(
                CampaignMember.campaign_id == session_entry.campaign_id,
                CampaignMember.user_id == player_user_id,
            )
        ).first()
        if not member or not member.id:
            raise CombatServiceError("Campaign member not found", 404)

        inventory_item = db.exec(
            select(InventoryItem).where(
                InventoryItem.id == inventory_item_id,
                InventoryItem.campaign_id == session_entry.campaign_id,
                InventoryItem.member_id == member.id,
            )
        ).first()
        if not inventory_item:
            raise CombatServiceError("Weapon not found", 404)
        if session_entry.party_id and inventory_item.party_id not in (None, session_entry.party_id):
            raise CombatServiceError("Weapon not found", 404)

        item = db.exec(
            select(Item).where(
                Item.id == inventory_item.item_id,
                Item.campaign_id == session_entry.campaign_id,
            )
        ).first()
        if not item or item.type != ItemType.WEAPON:
            raise CombatServiceError("Weapon not found", 404)
        return inventory_item, item

    @classmethod
    def _build_player_attack_context(
        cls,
        db: Session,
        session_id: str,
        player_user_id: str,
        data: dict,
        requested_weapon_item_id: str | None = None,
    ) -> dict:
        requested_id = requested_weapon_item_id.strip() if isinstance(requested_weapon_item_id, str) else None
        selected_inventory_item_id = requested_id or data.get("currentWeaponId")

        strength_mod = cls._ability_modifier(cls._get_player_ability_score(data, "strength"))
        level = data.get("level") if isinstance(data.get("level"), int) else 1
        proficiency_bonus = floor((level - 1) / 4) + 2

        if selected_inventory_item_id == "unarmed":
            return {
                "name": "Unarmed Strike",
                "damage_dice": "unarmed",
                "attack_bonus": strength_mod + proficiency_bonus,
                "damage_bonus": strength_mod,
                "damage_type": "bludgeoning",
                "ability": "strength",
                "is_proficient": True,
                "inventory_item_id": "unarmed",
            }

        if not isinstance(selected_inventory_item_id, str) or not selected_inventory_item_id.strip():
            return {
                "name": "Unarmed Strike",
                "damage_dice": "unarmed",
                "attack_bonus": strength_mod + proficiency_bonus,
                "damage_bonus": strength_mod,
                "damage_type": "bludgeoning",
                "ability": "strength",
                "is_proficient": True,
                "inventory_item_id": "unarmed",
            }

        try:
            inventory_item, item = cls._resolve_player_weapon_item(
                db,
                session_id,
                player_user_id,
                selected_inventory_item_id,
            )
        except CombatServiceError:
            if requested_id:
                raise
            return {
                "name": "Unarmed Strike",
                "damage_dice": "unarmed",
                "attack_bonus": strength_mod + proficiency_bonus,
                "damage_bonus": strength_mod,
                "damage_type": "bludgeoning",
                "ability": "strength",
                "is_proficient": True,
                "inventory_item_id": "unarmed",
            }

        legacy_weapon = cls._get_player_legacy_weapon_profile(data, item)
        ability_name = cls._choose_player_weapon_ability(data, item, legacy_weapon)
        ability_mod = cls._ability_modifier(cls._get_player_ability_score(data, ability_name))
        is_proficient = cls._is_player_weapon_proficient(data, item, legacy_weapon)
        legacy_magic_bonus = cls._safe_int((legacy_weapon or {}).get("magicBonus"), 0)
        legacy_attack_bonus = cls._safe_int((legacy_weapon or {}).get("attackBonus"), 0)
        legacy_damage_bonus = cls._safe_int((legacy_weapon or {}).get("damageBonus"), 0)
        item_magic_bonus = getattr(item, "magic_bonus", None)
        item_attack_bonus = getattr(item, "attack_bonus", None)
        item_damage_bonus = getattr(item, "damage_bonus", None)
        magic_bonus = item_magic_bonus if isinstance(item_magic_bonus, int) else legacy_magic_bonus
        attack_bonus_extra = item_attack_bonus if isinstance(item_attack_bonus, int) else legacy_attack_bonus
        damage_bonus_extra = item_damage_bonus if isinstance(item_damage_bonus, int) else legacy_damage_bonus
        legacy_range_type = cls._normalize_lookup((legacy_weapon or {}).get("rangeType")).replace(" ", "_")
        is_ranged_weapon = (
            getattr(item, "weapon_range_type", None) == BaseItemWeaponRangeType.RANGED
            or legacy_range_type == "ranged"
        )
        fighting_style = cls._get_player_fighting_style(data)
        fighting_style_attack_bonus = 2 if fighting_style == "archery" and is_ranged_weapon else 0

        return {
            "name": item.name,
            "damage_dice": item.damage_dice or "1d4",
            "attack_bonus": (
                ability_mod
                + (proficiency_bonus if is_proficient else 0)
                + magic_bonus
                + attack_bonus_extra
                + fighting_style_attack_bonus
            ),
            "damage_bonus": ability_mod + magic_bonus + damage_bonus_extra,
            "damage_type": item.damage_type,
            "ability": ability_name,
            "is_proficient": is_proficient,
            "inventory_item_id": inventory_item.id,
            "item_id": item.id,
            "magic_bonus": magic_bonus,
            "is_ranged_weapon": is_ranged_weapon,
        }

    @classmethod
    def calculate_player_armor_class_from_state(cls, data: dict | None) -> int:
        return calculate_player_armor_class_from_state(data)

    @classmethod
    def _get_spell_catalog_entry_for_session(
        cls,
        db: Session,
        session_id: str,
        canonical_key: str,
    ):
        normalized_key = canonical_key.strip().lower()
        if not normalized_key:
            raise CombatServiceError("Spell canonical key is required.", 400)

        session_entry = cls._get_session_entry(db, session_id)
        if not session_entry:
            raise CombatServiceError("Session not found", 404)

        campaign_spell = db.exec(
            select(CampaignSpell).where(
                CampaignSpell.campaign_id == session_entry.campaign_id,
                CampaignSpell.is_enabled == True,  # noqa: E712
                func.lower(CampaignSpell.canonical_key) == normalized_key,
            )
        ).first()
        if campaign_spell:
            return campaign_spell

        base_spell = get_base_spell_by_canonical_key(
            db=db,
            system=cls._get_campaign_system_for_session(db, session_id),
            canonical_key=canonical_key,
        )
        if not base_spell:
            raise CombatServiceError("Referenced spellCanonicalKey was not found in the catalog.")
        return base_spell

    @classmethod
    def _resolve_player_spell_entry(
        cls,
        data: dict,
        *,
        spell_canonical_key: str | None,
        spell_name: str | None = None,
    ) -> dict:
        spellcasting = cls._as_dict(data.get("spellcasting"))
        spells = spellcasting.get("spells")
        if not isinstance(spells, list):
            raise CombatServiceError("Player has no spellcasting configured.", 400)

        canonical_lookup = cls._normalize_lookup(spell_canonical_key)
        name_lookup = cls._normalize_lookup(spell_name)

        for raw_spell in spells:
            if not isinstance(raw_spell, dict):
                continue
            raw_canonical = cls._normalize_lookup(raw_spell.get("canonicalKey"))
            raw_name = cls._normalize_lookup(raw_spell.get("name"))
            if canonical_lookup and raw_canonical == canonical_lookup:
                return raw_spell
            if canonical_lookup and spell_name and raw_name == cls._normalize_lookup(spell_name):
                return raw_spell
            if not canonical_lookup and name_lookup and raw_name == name_lookup:
                return raw_spell

        raise CombatServiceError("Spell is not available on the player's sheet.", 400)

    @classmethod
    def _build_roll_actor_stats_for_save(
        cls,
        db: Session,
        session_id: str,
        ref_id: str,
        kind: str,
        display_name: str,
    ) -> RollActorStats:
        if kind == "player":
            target_model, _, _, _, prof_bonus, _ = cls._get_stats(db, ref_id, kind, session_id)
            data = cls._as_dict(target_model.state_json)
            abilities = {
                ability_name: cls._safe_int(value, 10)
                for ability_name, value in cls._as_dict(data.get("abilities")).items()
                if ability_name in cls._ENTITY_ABILITY_ALIASES
            }
            saving_throw_proficiencies = cls._as_dict(data.get("savingThrowProficiencies"))
            saving_throws: dict[str, int] = {}
            for ability_name in cls._ENTITY_ABILITY_ALIASES:
                if saving_throw_proficiencies.get(ability_name) is True:
                    saving_throws[ability_name] = cls._ability_modifier(
                        cls._safe_int(abilities.get(ability_name), 10)
                    ) + prof_bonus
            return RollActorStats(
                display_name=display_name,
                abilities=abilities,
                saving_throws=saving_throws or None,
                proficiency_bonus=prof_bonus,
                actor_kind="player",
                actor_ref_id=ref_id,
            )

        session_entity, npc = cls._get_session_entity_and_campaign_entity(db, ref_id)
        overrides = cls._as_dict(session_entity.overrides)
        abilities = {
            ability_name: cls._get_entity_ability_score(cls._as_dict(npc.abilities), overrides, ability_name)
            for ability_name in cls._ENTITY_ABILITY_ALIASES
        }
        saving_throws = cls._get_entity_saving_throw_overrides(npc, overrides) or None
        _, _, _, _, prof_bonus, _ = cls._get_stats(db, ref_id, kind, session_id)
        return RollActorStats(
            display_name=display_name,
            abilities=abilities,
            saving_throws=saving_throws,
            proficiency_bonus=prof_bonus,
            actor_kind="session_entity",
            actor_ref_id=ref_id,
        )

    @classmethod
    def _clear_participant_pending_attack(cls, participant: dict | None) -> None:
        if not participant or not isinstance(participant, dict):
            return
        participant.pop("pending_attack", None)

    @classmethod
    def _create_pending_attack(
        cls,
        state: CombatState,
        participant: dict,
        payload: dict,
    ) -> str:
        pending_attack_id = str(uuid4())
        participant["pending_attack"] = {
            **payload,
            "id": pending_attack_id,
        }
        flag_modified(state, "participants")
        return pending_attack_id

    @classmethod
    def _create_pending_spell_effect(
        cls,
        state: CombatState,
        participant: dict,
        payload: dict,
    ) -> str:
        # Spells reuse the participant-level pending slot so combat state shape stays stable,
        # but the type marker keeps the lifecycle explicit and prevents attack/effect mixups.
        return cls._create_pending_attack(
            state,
            participant,
            {
                **payload,
                "type": "player_spell_effect",
            },
        )

    @classmethod
    def _require_pending_attack(
        cls,
        participant: dict,
        pending_attack_id: str,
        *,
        expected_type: str,
    ) -> dict:
        pending_attack = participant.get("pending_attack") if isinstance(participant, dict) else None
        if not isinstance(pending_attack, dict):
            raise CombatServiceError("No pending damage roll for this actor.", 404)
        if pending_attack.get("id") != pending_attack_id:
            raise CombatServiceError("Pending damage roll not found.", 404)
        if pending_attack.get("type") != expected_type:
            raise CombatServiceError("Pending damage roll type mismatch.", 400)
        return pending_attack

    @classmethod
    def _require_pending_spell_effect(
        cls,
        participant: dict,
        pending_spell_id: str,
    ) -> dict:
        return cls._require_pending_attack(
            participant,
            pending_spell_id,
            expected_type="player_spell_effect",
        )

    @classmethod
    def _resolve_damage_roll(
        cls,
        damage_dice: str,
        *,
        critical: bool = False,
        roll_source: str = "system",
        manual_rolls: list[int] | None = None,
    ) -> tuple[list[int], int]:
        if damage_dice == "unarmed":
            return [], 2 if critical else 1

        count, sides, expression_modifier = _parse_dice(damage_dice)
        if count <= 0 or sides <= 0:
            return [], max(0, expression_modifier)

        effective_count = count * (2 if critical else 1)
        if roll_source == "manual":
            manual_values = manual_rolls or []
            if len(manual_values) != effective_count:
                raise CombatServiceError(f"Manual damage roll requires exactly {effective_count} result(s).")
            for value in manual_values:
                if not isinstance(value, int) or value < 1 or value > sides:
                    raise CombatServiceError(f"Manual damage roll values must be between 1 and {sides}.")
            rolls = manual_values
        else:
            rolls = [random.randint(1, sides) for _ in range(effective_count)]

        return rolls, sum(rolls) + expression_modifier

    @classmethod
    def get_state(cls, db: Session, session_id: str) -> CombatState | None:
        return db.exec(select(CombatState).where(CombatState.session_id == session_id)).first()

    @classmethod
    def _require_active(cls, state: CombatState | None):
        if not state:
            raise CombatServiceError("No combat active for this session", 404)
        if state.phase != CombatPhase.active:
            raise CombatServiceError("Combat is not in active phase")

    @classmethod
    def _resolve_actor_participant(
        cls,
        state: CombatState,
        actor_user_id: str,
        is_gm: bool,
        actor_participant_id: str | None = None,
    ) -> dict:
        current_p = cls._get_current_participant(state)

        if actor_participant_id and current_p.get("id") != actor_participant_id:
            raise CombatServiceError("Selected actor is not the active participant", 403)

        if is_gm:
            return current_p

        if current_p.get("kind") != "player":
            raise CombatServiceError("It's not a player's turn")

        if current_p.get("actor_user_id") != actor_user_id:
            raise CombatServiceError("Not your turn", 403)

        return current_p

    @classmethod
    def _require_actor_status(cls, attacker: dict, allowed_statuses: tuple[str, ...], message: str):
        if attacker.get("status") not in allowed_statuses:
            raise CombatServiceError(message, 403)

    @classmethod
    def _get_stats(cls, db: Session, ref_id: str, kind: str, session_id: str = ""):
        if kind == "player":
            target = db.exec(
                select(SessionState).where(
                    SessionState.player_user_id == ref_id,
                    SessionState.session_id == session_id,
                )
            ).first() if session_id else db.exec(
                select(SessionState).where(SessionState.player_user_id == ref_id)
            ).first()
            if not target: raise CombatServiceError("Player not found")
            data = cls._as_dict(target.state_json)
            abilities = cls._as_dict(data.get("abilities"))
            spellcasting = cls._as_dict(data.get("spellcasting"))
            str_val = abilities.get("strength", 10)
            dex_val = abilities.get("dexterity", 10)
            ac = cls.calculate_player_armor_class_from_state(data)

            # Wild Shape: override AC and physical ability scores with beast form
            wild_shape = cls._as_dict(data.get("wildShape"))
            if wild_shape.get("active"):
                from app.services.wild_shape_catalog import get_form
                form_key = wild_shape.get("formKey")
                form = get_form(form_key) if isinstance(form_key, str) else None
                if form is not None:
                    ac = form.armor_class
                    str_val = form.str_score
                    dex_val = form.dex_score

            level = data.get("level", 1)
            prof_bonus = floor((level - 1) / 4) + 2
            spell_ability = spellcasting.get("ability")
            spell_mod = spellcasting.get("modifier")
            if not isinstance(spell_mod, int) and isinstance(spell_ability, str):
                spell_score = abilities.get(spell_ability, 10)
                spell_mod = floor((spell_score - 10) / 2)
            if not isinstance(spell_mod, int):
                spell_mod = 0
            return target, ac, str_val, dex_val, prof_bonus, spell_mod
        else:
            target = db.exec(select(SessionEntity).where(SessionEntity.id == ref_id)).first()
            if not target: raise CombatServiceError("Entity not found")
            npc = db.exec(select(CampaignEntity).where(CampaignEntity.id == target.campaign_entity_id)).first()
            if not npc: raise CombatServiceError("Campaign entity not found")
            abilities = cls._as_dict(npc.abilities)
            overrides = cls._as_dict(target.overrides)
            spellcasting = cls._get_entity_spellcasting(npc, overrides)

            str_val = cls._get_entity_ability_score(abilities, overrides, "strength")
            dex_val = cls._get_entity_ability_score(abilities, overrides, "dexterity")
            ac = cls._get_entity_armor_class(npc, overrides)
            spell_ability = cls._normalize_ability_name(spellcasting.get("ability")) or "intelligence"
            spell_mod = cls._ability_modifier(
                cls._get_entity_ability_score(abilities, overrides, spell_ability)
            )
            explicit_spell_attack_bonus = spellcasting.get("attackBonus")
            explicit_spell_save_dc = spellcasting.get("saveDc")
            prof_bonus = 2
            if isinstance(explicit_spell_attack_bonus, int):
                prof_bonus = max(0, explicit_spell_attack_bonus - spell_mod)
            elif isinstance(explicit_spell_save_dc, int):
                prof_bonus = max(0, explicit_spell_save_dc - 8 - spell_mod)
            return target, ac, str_val, dex_val, prof_bonus, spell_mod

    @classmethod
    def _get_session_entity_and_campaign_entity(
        cls,
        db: Session,
        session_entity_id: str,
    ) -> tuple[SessionEntity, CampaignEntity]:
        target = db.exec(select(SessionEntity).where(SessionEntity.id == session_entity_id)).first()
        if not target:
            raise CombatServiceError("Entity not found")
        npc = db.exec(select(CampaignEntity).where(CampaignEntity.id == target.campaign_entity_id)).first()
        if not npc:
            raise CombatServiceError("Campaign entity not found")
        return target, npc

    @classmethod
    def _get_combat_action_for_entity(
        cls,
        db: Session,
        session_entity_id: str,
        combat_action_id: str,
    ) -> tuple[SessionEntity, CampaignEntity, CombatAction]:
        target, npc = cls._get_session_entity_and_campaign_entity(db, session_entity_id)
        raw_actions = npc.combat_actions if isinstance(npc.combat_actions, list) else []
        raw_action = next(
            (
                entry for entry in raw_actions
                if isinstance(entry, dict) and entry.get("id") == combat_action_id
            ),
            None,
        )
        if not raw_action:
            raise CombatServiceError("Combat action not found", 404)
        try:
            action = CombatAction(**raw_action)
        except Exception as exc:
            raise CombatServiceError(f"Invalid combat action definition: {exc}", 400) from exc
        return target, npc, action
