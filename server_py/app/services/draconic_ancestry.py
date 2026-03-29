from __future__ import annotations

from typing import Any
from math import floor


DRACONIC_ANCESTRIES: tuple[dict[str, str], ...] = (
    {"id": "black", "label": "Black", "damageType": "acid", "resistanceType": "acid", "breathWeaponShape": "line", "breathWeaponSaveType": "dexterity", "breathWeaponAreaSize": "1.5m x 9m"},
    {"id": "blue", "label": "Blue", "damageType": "lightning", "resistanceType": "lightning", "breathWeaponShape": "line", "breathWeaponSaveType": "dexterity", "breathWeaponAreaSize": "1.5m x 9m"},
    {"id": "brass", "label": "Brass", "damageType": "fire", "resistanceType": "fire", "breathWeaponShape": "line", "breathWeaponSaveType": "dexterity", "breathWeaponAreaSize": "1.5m x 9m"},
    {"id": "bronze", "label": "Bronze", "damageType": "lightning", "resistanceType": "lightning", "breathWeaponShape": "line", "breathWeaponSaveType": "dexterity", "breathWeaponAreaSize": "1.5m x 9m"},
    {"id": "copper", "label": "Copper", "damageType": "acid", "resistanceType": "acid", "breathWeaponShape": "line", "breathWeaponSaveType": "dexterity", "breathWeaponAreaSize": "1.5m x 9m"},
    {"id": "gold", "label": "Gold", "damageType": "fire", "resistanceType": "fire", "breathWeaponShape": "cone", "breathWeaponSaveType": "constitution", "breathWeaponAreaSize": "4.5m"},
    {"id": "green", "label": "Green", "damageType": "poison", "resistanceType": "poison", "breathWeaponShape": "cone", "breathWeaponSaveType": "constitution", "breathWeaponAreaSize": "4.5m"},
    {"id": "red", "label": "Red", "damageType": "fire", "resistanceType": "fire", "breathWeaponShape": "cone", "breathWeaponSaveType": "constitution", "breathWeaponAreaSize": "4.5m"},
    {"id": "silver", "label": "Silver", "damageType": "cold", "resistanceType": "cold", "breathWeaponShape": "cone", "breathWeaponSaveType": "constitution", "breathWeaponAreaSize": "4.5m"},
    {"id": "white", "label": "White", "damageType": "cold", "resistanceType": "cold", "breathWeaponShape": "cone", "breathWeaponSaveType": "constitution", "breathWeaponAreaSize": "4.5m"},
)

DRACONIC_ANCESTRY_BY_ID: dict[str, dict[str, str]] = {
    ancestry["id"]: ancestry for ancestry in DRACONIC_ANCESTRIES
}

DRACONIC_ANCESTRY_DAMAGE_TYPES: dict[str, str] = {
    ancestry["id"]: ancestry["damageType"] for ancestry in DRACONIC_ANCESTRIES
}

DRACONIC_ANCESTRY_SUBCLASS_CONFIG_KEY = "draconicAncestry"
LEGACY_DRACONIC_ANCESTRY_SUBCLASS_CONFIG_KEY = "dragonAncestor"


def is_valid_draconic_ancestry(value: object) -> bool:
    return isinstance(value, str) and value in DRACONIC_ANCESTRY_DAMAGE_TYPES


def get_draconic_damage_type(ancestry: str | None) -> str | None:
    if ancestry is None:
        return None
    return DRACONIC_ANCESTRY_DAMAGE_TYPES.get(ancestry)


def get_draconic_ancestry_label(ancestry: str | None) -> str | None:
    if ancestry is None:
        return None
    entry = DRACONIC_ANCESTRY_BY_ID.get(ancestry)
    if entry is None:
        return None
    return entry["label"]


def get_draconic_resistance_type(ancestry: str | None) -> str | None:
    if ancestry is None:
        return None
    entry = DRACONIC_ANCESTRY_BY_ID.get(ancestry)
    if entry is None:
        return None
    return entry["resistanceType"]


def get_draconic_breath_weapon_shape(ancestry: str | None) -> str | None:
    if ancestry is None:
        return None
    entry = DRACONIC_ANCESTRY_BY_ID.get(ancestry)
    if entry is None:
        return None
    return entry["breathWeaponShape"]


def get_draconic_breath_weapon_save_type(ancestry: str | None) -> str | None:
    if ancestry is None:
        return None
    entry = DRACONIC_ANCESTRY_BY_ID.get(ancestry)
    if entry is None:
        return None
    return entry["breathWeaponSaveType"]


def get_draconic_breath_weapon_area_size(ancestry: str | None) -> str | None:
    if ancestry is None:
        return None
    entry = DRACONIC_ANCESTRY_BY_ID.get(ancestry)
    if entry is None:
        return None
    return entry["breathWeaponAreaSize"]


def get_draconic_ancestry_from_data(data: object) -> str | None:
    if not isinstance(data, dict):
        return None
    normalized_config = normalize_subclass_config(
        data.get("subclass"),
        data.get("subclassConfig"),
    )
    ancestry = (
        normalized_config.get(DRACONIC_ANCESTRY_SUBCLASS_CONFIG_KEY)
        if normalized_config is not None
        else None
    )
    return ancestry if is_valid_draconic_ancestry(ancestry) else None


def resolve_draconic_lineage_state(data: object) -> dict[str, Any]:
    if not isinstance(data, dict):
        return {
            "ancestry": None,
            "damageType": None,
            "resistanceType": None,
            "hasElementalAffinity": False,
            "resistances": [],
        }

    if data.get("class") != "sorcerer" or data.get("subclass") != "draconic_bloodline":
        return {
            "ancestry": None,
            "damageType": None,
            "resistanceType": None,
            "hasElementalAffinity": False,
            "resistances": [],
        }

    ancestry = get_draconic_ancestry_from_data(data)
    damage_type = get_draconic_damage_type(ancestry)
    resistance_type = get_draconic_resistance_type(ancestry)
    level = int(data.get("level", 1) or 1)
    has_elemental_affinity = level >= 6 and damage_type is not None and resistance_type is not None

    return {
        "ancestry": ancestry,
        "ancestryLabel": get_draconic_ancestry_label(ancestry),
        "damageType": damage_type,
        "resistanceType": resistance_type,
        "hasElementalAffinity": has_elemental_affinity,
        "resistances": [resistance_type] if has_elemental_affinity and resistance_type else [],
    }


def resolve_elemental_affinity(data: object, spell_damage_type: object) -> dict[str, Any]:
    lineage = resolve_draconic_lineage_state(data)
    normalized_damage_type = (
        str(spell_damage_type).strip().lower()
        if isinstance(spell_damage_type, str) and spell_damage_type.strip()
        else None
    )
    charisma_score = 10
    if isinstance(data, dict):
        abilities = data.get("abilities")
        if isinstance(abilities, dict) and isinstance(abilities.get("charisma"), int):
            charisma_score = abilities["charisma"]
    eligible = bool(
        lineage["hasElementalAffinity"]
        and lineage["damageType"]
        and normalized_damage_type
        and lineage["damageType"] == normalized_damage_type
    )
    return {
        "eligible": eligible,
        "damageType": lineage["damageType"],
        "bonus": floor((charisma_score - 10) / 2) if eligible else None,
    }


def normalize_subclass_config(
    subclass: object,
    subclass_config: object,
) -> dict[str, str] | None:
    if not isinstance(subclass_config, dict):
        return None

    next_config: dict[str, str] = {}
    for raw_key, raw_value in subclass_config.items():
        if not isinstance(raw_key, str) or not isinstance(raw_value, str):
            continue
        value = raw_value.strip()
        if not value:
            continue
        key = (
            DRACONIC_ANCESTRY_SUBCLASS_CONFIG_KEY
            if raw_key == LEGACY_DRACONIC_ANCESTRY_SUBCLASS_CONFIG_KEY
            else raw_key
        )
        next_config[key] = value

    if subclass != "draconic_bloodline":
        next_config.pop(DRACONIC_ANCESTRY_SUBCLASS_CONFIG_KEY, None)

    return next_config or None


def validate_draconic_subclass_state(data: object) -> tuple[bool, str | None]:
    if not isinstance(data, dict):
        return True, None

    if data.get("subclass") != "draconic_bloodline":
        return True, None

    normalized_config = normalize_subclass_config(
        data.get("subclass"),
        data.get("subclassConfig"),
    )
    ancestry = (
        normalized_config.get(DRACONIC_ANCESTRY_SUBCLASS_CONFIG_KEY)
        if normalized_config is not None
        else None
    )

    if ancestry is None:
        return False, "draconicAncestry is required for Draconic Bloodline"

    if not is_valid_draconic_ancestry(ancestry):
        return False, "draconicAncestry is invalid for Draconic Bloodline"

    return True, None
