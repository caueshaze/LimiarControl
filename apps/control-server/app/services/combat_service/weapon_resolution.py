from __future__ import annotations

from enum import Enum
from math import floor
from typing import Any
import unicodedata

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session, select

from app.models.base_item import BaseItemWeaponRangeType
from app.models.campaign_member import CampaignMember
from app.models.inventory import InventoryItem
from app.models.item import Item, ItemType
from app.models.session import Session as CampaignSession

from .exceptions import CombatServiceError
from .host_protocol import CombatServiceHostProtocol


_SPECIFIC_WEAPON_PROFICIENCY_ALIASES = {
    "club": ("clava", "clavas", "club", "clubs"),
    "dagger": ("adaga", "adagas", "dagger", "daggers"),
    "dart": ("dardo", "dardos", "dart", "darts"),
    "hand_crossbow": (
        "besta de mao",
        "bestas de mao",
        "hand crossbow",
        "hand crossbows",
    ),
    "javelin": ("azagaia", "azagaias", "javelin", "javelins"),
    "light_crossbow": (
        "besta leve",
        "bestas leves",
        "light crossbow",
        "light crossbows",
    ),
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


def _normalize_lookup(value: object) -> str:
    if isinstance(value, Enum):
        value = value.value
    if not isinstance(value, str):
        return ""
    normalized = unicodedata.normalize("NFD", value.strip().lower())
    normalized = "".join(
        char for char in normalized if unicodedata.category(char) != "Mn"
    )
    normalized = normalized.replace("_", " ").replace("-", " ")
    return " ".join(normalized.split())


def _normalize_class_id(value: object) -> str:
    return str(value or "").strip().lower()


class CombatWeaponResolutionMixin(CombatServiceHostProtocol):
    _SPECIFIC_WEAPON_PROFICIENCY_ALIASES = _SPECIFIC_WEAPON_PROFICIENCY_ALIASES
    _SHILLELAGH_ELIGIBLE_WEAPONS = {"club", "quarterstaff"}

    @staticmethod
    def _enum_value_or_none(value: object) -> str | None:
        if isinstance(value, Enum):
            raw = value.value
            return raw if isinstance(raw, str) else str(raw)
        if isinstance(value, str):
            return value
        return None

    @classmethod
    def _coerce_optional_int(cls, value: object) -> int | None:
        if value is None:
            return None
        if not isinstance(value, (int, float, str)):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @classmethod
    def _get_player_legacy_weapon_profile(cls, data: dict, item: Item) -> dict | None:
        raw_weapons = data.get("weapons")
        if not isinstance(raw_weapons, list):
            return None

        candidates = {
            _normalize_lookup(item.name),
            _normalize_lookup(item.name_en_snapshot),
            _normalize_lookup(item.name_pt_snapshot),
            _normalize_lookup(item.canonical_key_snapshot),
        }
        canonical_slug = _normalize_lookup(item.canonical_key_snapshot).replace(
            " ", "_"
        )
        if canonical_slug:
            candidates.update(
                _normalize_lookup(alias)
                for alias in _SPECIFIC_WEAPON_PROFICIENCY_ALIASES.get(
                    canonical_slug, ()
                )
            )
        candidates.discard("")
        if not candidates:
            return None

        for raw_weapon in raw_weapons:
            if not isinstance(raw_weapon, dict):
                continue
            if _normalize_lookup(raw_weapon.get("name")) in candidates:
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
        proficiency_entries = (
            raw_proficiencies if isinstance(raw_proficiencies, list) else []
        )
        proficiencies = {
            _normalize_lookup(entry)
            for entry in proficiency_entries
            if isinstance(entry, str)
        }
        category = _normalize_lookup(item.weapon_category)
        if category == "simple" and (
            "simple" in proficiencies or "simples" in proficiencies
        ):
            return True
        if category == "martial" and (
            "martial" in proficiencies or "marciais" in proficiencies
        ):
            return True

        candidates = {
            _normalize_lookup(item.name),
            _normalize_lookup(item.name_en_snapshot),
            _normalize_lookup(item.name_pt_snapshot),
        }
        canonical_slug = _normalize_lookup(item.canonical_key_snapshot).replace(
            " ", "_"
        )
        if canonical_slug:
            for alias in _SPECIFIC_WEAPON_PROFICIENCY_ALIASES.get(canonical_slug, ()):
                candidates.add(_normalize_lookup(alias))

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
        properties = {_normalize_lookup(value) for value in (item.properties or [])}
        if "finesse" in properties:
            strength_mod = cls._ability_modifier(
                cls._get_player_ability_score(data, "strength")
            )
            dexterity_mod = cls._ability_modifier(
                cls._get_player_ability_score(data, "dexterity")
            )
            return "dexterity" if dexterity_mod >= strength_mod else "strength"

        if _normalize_lookup(item.weapon_range_type) == "ranged":
            return "dexterity"

        legacy_ability = _normalize_lookup((legacy_weapon or {}).get("ability"))
        if legacy_ability in cls._ENTITY_ABILITY_ALIASES:
            return legacy_ability

        return "strength"

    @classmethod
    def _resolve_player_weapon_item(
        cls,
        db: Session,
        session_id: str,
        player_user_id: str,
        weapon_item_id: str,
    ) -> tuple[InventoryItem, Item]:
        inventory_item_id = weapon_item_id
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
        if session_entry.party_id and inventory_item.party_id not in (
            None,
            session_entry.party_id,
        ):
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
        attacker_effects: list[dict] | None = None,
    ) -> dict:
        requested_id = (
            requested_weapon_item_id.strip()
            if isinstance(requested_weapon_item_id, str)
            else None
        )
        current_weapon_id_value = data.get("currentWeaponId")
        current_weapon_id = (
            current_weapon_id_value.strip()
            if isinstance(current_weapon_id_value, str)
            else None
        )
        effective_current_weapon_id = (
            current_weapon_id
            if isinstance(current_weapon_id, str) and current_weapon_id
            else "unarmed"
        )
        selected_inventory_item_id = current_weapon_id

        if requested_id and requested_id != effective_current_weapon_id:
            raise CombatServiceError("Weapon attacks must use the currently equipped weapon.", 400)

        strength_mod = cls._ability_modifier(
            cls._get_player_ability_score(data, "strength")
        )
        level = max(1, cls._safe_int(data.get("level"), 1))
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
                "weapon_canonical_key": None,
                "range_meters": 1.5,
                "range_long_meters": None,
                "weapon_range_type": BaseItemWeaponRangeType.MELEE.value,
                "has_reach": False,
            }

        if (
            not isinstance(selected_inventory_item_id, str)
            or not selected_inventory_item_id.strip()
        ):
            return {
                "name": "Unarmed Strike",
                "damage_dice": "unarmed",
                "attack_bonus": strength_mod + proficiency_bonus,
                "damage_bonus": strength_mod,
                "damage_type": "bludgeoning",
                "ability": "strength",
                "is_proficient": True,
                "inventory_item_id": "unarmed",
                "weapon_canonical_key": None,
                "range_meters": 1.5,
                "range_long_meters": None,
                "weapon_range_type": BaseItemWeaponRangeType.MELEE.value,
                "has_reach": False,
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
                "weapon_canonical_key": None,
                "range_meters": 1.5,
                "range_long_meters": None,
                "weapon_range_type": BaseItemWeaponRangeType.MELEE.value,
                "has_reach": False,
            }

        legacy_weapon = cls._get_player_legacy_weapon_profile(data, item)
        ability_name = cls._choose_player_weapon_ability(data, item, legacy_weapon)
        ability_mod = cls._ability_modifier(
            cls._get_player_ability_score(data, ability_name)
        )
        is_proficient = cls._is_player_weapon_proficient(data, item, legacy_weapon)
        legacy_magic_bonus = cls._safe_int((legacy_weapon or {}).get("magicBonus"), 0)
        legacy_attack_bonus = cls._safe_int((legacy_weapon or {}).get("attackBonus"), 0)
        legacy_damage_bonus = cls._safe_int((legacy_weapon or {}).get("damageBonus"), 0)
        item_magic_bonus = getattr(item, "magic_bonus", None)
        item_attack_bonus = getattr(item, "attack_bonus", None)
        item_damage_bonus = getattr(item, "damage_bonus", None)
        magic_bonus = (
            item_magic_bonus
            if isinstance(item_magic_bonus, int)
            else legacy_magic_bonus
        )
        attack_bonus_extra = (
            item_attack_bonus
            if isinstance(item_attack_bonus, int)
            else legacy_attack_bonus
        )
        damage_bonus_extra = (
            item_damage_bonus
            if isinstance(item_damage_bonus, int)
            else legacy_damage_bonus
        )
        legacy_range_type = _normalize_lookup(
            (legacy_weapon or {}).get("rangeType")
        ).replace(" ", "_")
        is_ranged_weapon = (
            getattr(item, "weapon_range_type", None) == BaseItemWeaponRangeType.RANGED
            or legacy_range_type == "ranged"
        )
        fighting_style = cls._get_player_fighting_style(data)
        fighting_style_attack_bonus = (
            2 if fighting_style == "archery" and is_ranged_weapon else 0
        )
        shillelagh_override = cls._resolve_shillelagh_weapon_override(
            attacker_data=data,
            attacker_effects=attacker_effects,
            inventory_item_id=inventory_item.id,
            weapon_canonical_key=getattr(item, "canonical_key_snapshot", None),
            weapon_range_type=cls._enum_value_or_none(
                getattr(item, "weapon_range_type", None)
            ),
        )
        if shillelagh_override is not None:
            ability_name = shillelagh_override["attack_ability"]
            ability_mod = shillelagh_override["attack_ability_mod"]

        return {
            "name": item.name,
            "damage_dice": shillelagh_override["damage_die"] if shillelagh_override else (item.damage_dice or "1d4"),
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
            "weapon_canonical_key": getattr(item, "canonical_key_snapshot", None),
            "range_meters": cls._coerce_optional_int(getattr(item, "range_meters", None)),
            "range_long_meters": cls._coerce_optional_int(
                getattr(item, "range_long_meters", None)
            ),
            "weapon_range_type": cls._enum_value_or_none(
                getattr(item, "weapon_range_type", None)
            ),
            "has_reach": "reach"
            in {
                _normalize_lookup(value)
                for value in (item.properties or [])
                if isinstance(value, str)
            },
            "is_magical_damage": bool(
                shillelagh_override and shillelagh_override["damage_counts_as_magical"]
            ),
        }

    @classmethod
    def _resolve_shillelagh_weapon_override(
        cls,
        *,
        attacker_data: dict,
        attacker_effects: list[dict] | None,
        inventory_item_id: str | None,
        weapon_canonical_key: str | None,
        weapon_range_type: str | None,
    ) -> dict | None:
        if not isinstance(inventory_item_id, str) or not inventory_item_id.strip():
            return None
        if _normalize_lookup(weapon_range_type) != "melee":
            return None
        normalized_weapon_key = _normalize_lookup(weapon_canonical_key).replace(" ", "_")
        if normalized_weapon_key not in cls._SHILLELAGH_ELIGIBLE_WEAPONS:
            return None
        for effect in attacker_effects or []:
            if not isinstance(effect, dict):
                continue
            metadata = effect.get("metadata")
            if not isinstance(metadata, dict):
                continue
            if _normalize_lookup(metadata.get("source_spell_key")) != "shillelagh":
                continue
            if metadata.get("weapon_item_id") != inventory_item_id:
                continue
            spellcasting = cls._as_dict(attacker_data.get("spellcasting"))
            spell_ability = _normalize_lookup(spellcasting.get("ability"))
            if spell_ability not in cls._ENTITY_ABILITY_ALIASES:
                spell_ability = "wisdom"
            spell_mod = spellcasting.get("modifier")
            if not isinstance(spell_mod, int):
                spell_mod = cls._ability_modifier(
                    cls._get_player_ability_score(attacker_data, spell_ability)
                )
            return {
                "attack_ability": spell_ability,
                "attack_ability_mod": spell_mod,
                "damage_ability": spell_ability,
                "damage_ability_mod": spell_mod,
                "damage_die": "1d8",
                "damage_counts_as_magical": True,
                "source_spell_key": "shillelagh",
            }
        return None
