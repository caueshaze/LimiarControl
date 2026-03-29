from __future__ import annotations

from typing import Any

from app.services.draconic_ancestry import (
    DRACONIC_ANCESTRY_BY_ID,
    get_draconic_ancestry_label,
    get_draconic_breath_weapon_area_size,
    get_draconic_breath_weapon_save_type,
    get_draconic_breath_weapon_shape,
    get_draconic_damage_type,
    get_draconic_resistance_type,
    is_valid_draconic_ancestry,
)

DRAGONBORN_DRACONIC_ANCESTRY_RACE_CONFIG_KEY = "draconicAncestry"
LEGACY_DRAGONBORN_ANCESTRY_RACE_CONFIG_KEY = "dragonbornAncestry"
LEGACY_DRAGONBORN_DRAGON_ANCESTOR_RACE_CONFIG_KEY = "dragonAncestor"

DRAGONBORN_ANCESTRIES = DRACONIC_ANCESTRY_BY_ID


def is_valid_dragonborn_ancestry(value: object) -> bool:
    return is_valid_draconic_ancestry(value)


def get_dragonborn_damage_type(ancestry: str | None) -> str | None:
    return get_draconic_damage_type(ancestry)


def get_dragonborn_resistance_type(ancestry: str | None) -> str | None:
    return get_draconic_resistance_type(ancestry)


def get_dragonborn_breath_weapon_shape(ancestry: str | None) -> str | None:
    return get_draconic_breath_weapon_shape(ancestry)


def get_dragonborn_breath_weapon_save_type(ancestry: str | None) -> str | None:
    return get_draconic_breath_weapon_save_type(ancestry)


def get_dragonborn_breath_weapon_area_size(ancestry: str | None) -> str | None:
    return get_draconic_breath_weapon_area_size(ancestry)


def normalize_dragonborn_race_config(race_config: object) -> dict[str, str | None] | None:
    if not isinstance(race_config, dict):
        return {DRAGONBORN_DRACONIC_ANCESTRY_RACE_CONFIG_KEY: None}

    ancestry = (
        race_config.get(DRAGONBORN_DRACONIC_ANCESTRY_RACE_CONFIG_KEY)
        or race_config.get(LEGACY_DRAGONBORN_ANCESTRY_RACE_CONFIG_KEY)
        or race_config.get(LEGACY_DRAGONBORN_DRAGON_ANCESTOR_RACE_CONFIG_KEY)
    )
    return {
        DRAGONBORN_DRACONIC_ANCESTRY_RACE_CONFIG_KEY: ancestry if is_valid_dragonborn_ancestry(ancestry) else None,
    }


def get_dragonborn_ancestry_from_data(data: object) -> str | None:
    if not isinstance(data, dict) or data.get("race") != "dragonborn":
        return None
    normalized = normalize_dragonborn_race_config(data.get("raceConfig"))
    ancestry = normalized.get(DRAGONBORN_DRACONIC_ANCESTRY_RACE_CONFIG_KEY) if normalized else None
    return ancestry if is_valid_dragonborn_ancestry(ancestry) else None


def resolve_dragonborn_lineage_state(data: object) -> dict[str, Any]:
    if not isinstance(data, dict) or data.get("race") != "dragonborn":
        return {
            "ancestry": None,
            "ancestryLabel": None,
            "damageType": None,
            "resistanceType": None,
            "breathWeaponShape": None,
            "breathWeaponSaveType": None,
            "breathWeaponAreaSize": None,
            "resistances": [],
        }

    ancestry = get_dragonborn_ancestry_from_data(data)
    damage_type = get_dragonborn_damage_type(ancestry)
    resistance_type = get_dragonborn_resistance_type(ancestry)
    breath_weapon_shape = get_dragonborn_breath_weapon_shape(ancestry)
    breath_weapon_save_type = get_dragonborn_breath_weapon_save_type(ancestry)
    breath_weapon_area_size = get_dragonborn_breath_weapon_area_size(ancestry)

    return {
        "ancestry": ancestry,
        "ancestryLabel": get_draconic_ancestry_label(ancestry),
        "damageType": damage_type,
        "resistanceType": resistance_type,
        "breathWeaponShape": breath_weapon_shape,
        "breathWeaponSaveType": breath_weapon_save_type,
        "breathWeaponAreaSize": breath_weapon_area_size,
        "resistances": [resistance_type] if resistance_type else [],
    }
