from __future__ import annotations

from datetime import datetime, timezone
import random
from math import floor

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session, select

from app.models.base_item import BaseItemKind, BaseItemWeaponRangeType
from app.models.campaign import Campaign, SystemType
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

from .exceptions import CombatServiceError, _roll_dice_expression


class CombatEntityStatsMixin:
    _ENTITY_ABILITY_ALIASES = {
        "strength": "str",
        "dexterity": "dex",
        "constitution": "con",
        "intelligence": "int",
        "wisdom": "wis",
        "charisma": "cha",
    }

    @classmethod
    def _as_dict(cls, value: object) -> dict:
        return value if isinstance(value, dict) else {}

    @classmethod
    def _safe_int(cls, value: object, default: int = 0) -> int:
        return value if isinstance(value, int) else default

    @classmethod
    def _ability_modifier(cls, score: int) -> int:
        return derive_ability_modifier(score)

    @classmethod
    def _normalize_ability_name(cls, value: object) -> str | None:
        if not isinstance(value, str):
            return None
        normalized = value.strip().lower()
        if normalized in cls._ENTITY_ABILITY_ALIASES:
            return normalized
        reverse_aliases = {alias: name for name, alias in cls._ENTITY_ABILITY_ALIASES.items()}
        return reverse_aliases.get(normalized)

    @classmethod
    def _normalize_damage_type(cls, value: object) -> str | None:
        if not isinstance(value, str):
            return None
        normalized = value.strip().lower()
        return normalized or None

    @classmethod
    def _get_entity_ability_score(cls, stats: dict, overrides: dict, ability_name: str) -> int:
        short_name = cls._ENTITY_ABILITY_ALIASES.get(ability_name)
        override_abilities = cls._as_dict(overrides.get("abilities"))
        legacy_override_stats = cls._as_dict(overrides.get("stats"))
        for source in (override_abilities, legacy_override_stats, stats):
            value = source.get(ability_name)
            if isinstance(value, int):
                return value
            if short_name:
                short_value = source.get(short_name)
                if isinstance(short_value, int):
                    return short_value
        return 10

    @classmethod
    def _get_entity_spellcasting(cls, npc: CampaignEntity, overrides: dict) -> dict:
        override_spellcasting = cls._as_dict(overrides.get("spellcasting"))
        if override_spellcasting:
            return override_spellcasting
        return cls._as_dict(npc.spellcasting)

    @classmethod
    def _get_entity_saving_throw_overrides(cls, npc: CampaignEntity, overrides: dict) -> dict:
        merged = dict(cls._as_dict(npc.saving_throws))
        for raw_overrides in (
            cls._as_dict(overrides.get("savingThrows")),
            cls._as_dict(overrides.get("saving_throws")),
        ):
            for key, value in raw_overrides.items():
                normalized_key = cls._normalize_ability_name(key)
                if normalized_key and isinstance(value, int):
                    merged[normalized_key] = value
        return merged

    @classmethod
    def _get_entity_skill_overrides(cls, npc: CampaignEntity, overrides: dict) -> dict:
        merged = dict(cls._as_dict(npc.skills))
        for raw_overrides in (cls._as_dict(overrides.get("skills")),):
            for key, value in raw_overrides.items():
                if key in SKILL_ABILITY_MAP and isinstance(value, int):
                    merged[key] = value
        return merged

    @classmethod
    def _get_entity_initiative_bonus(cls, npc: CampaignEntity, overrides: dict) -> int:
        override_bonus = overrides.get("initiativeBonus")
        if isinstance(override_bonus, int):
            return override_bonus
        abilities = {
            ability_name: cls._get_entity_ability_score(cls._as_dict(npc.abilities), overrides, ability_name)
            for ability_name in cls._ENTITY_ABILITY_ALIASES
        }
        return resolve_entity_initiative_bonus(abilities, npc.initiative_bonus)

    @classmethod
    def _get_entity_skill_bonus(cls, npc: CampaignEntity, overrides: dict, skill_name: str) -> int:
        if skill_name not in SKILL_ABILITY_MAP:
            raise CombatServiceError("Invalid skill")
        abilities = {
            ability_name: cls._get_entity_ability_score(cls._as_dict(npc.abilities), overrides, ability_name)
            for ability_name in cls._ENTITY_ABILITY_ALIASES
        }
        return resolve_entity_skill_bonus(
            abilities,
            cls._get_entity_skill_overrides(npc, overrides),
            skill_name,
        )

    @classmethod
    def _get_entity_armor_class(cls, npc: CampaignEntity, overrides: dict) -> int:
        override_ac = overrides.get("armorClass")
        if isinstance(override_ac, int):
            return override_ac
        legacy_override_ac = overrides.get("ac")
        if isinstance(legacy_override_ac, int):
            return legacy_override_ac
        return npc.armor_class or 10
