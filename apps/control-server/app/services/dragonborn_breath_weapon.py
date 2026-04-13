from __future__ import annotations

from math import ceil, floor
from typing import Any

from app.services.dragonborn_ancestry import resolve_dragonborn_lineage_state


DRAGONBORN_BREATH_WEAPON_ACTION_ID = "dragonborn_breath_weapon"
DRAGONBORN_BREATH_WEAPON_RESOURCE_KEY = "dragonbornBreathWeapon"


def _safe_int(value: object, fallback: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _ability_modifier(score: int) -> int:
    return floor((score - 10) / 2)


def _get_proficiency_bonus(level: int) -> int:
    normalized_level = max(1, int(level))
    return ceil(normalized_level / 4) + 1


def compute_dragonborn_breath_weapon_damage_dice(level: int) -> str:
    normalized_level = max(1, int(level))
    if normalized_level >= 17:
        return "5d6"
    if normalized_level >= 11:
        return "4d6"
    if normalized_level >= 5:
        return "3d6"
    return "2d6"


def compute_dragonborn_breath_weapon_dc(
    data: dict | None,
    *,
    proficiency_bonus: int | None = None,
) -> int:
    payload = dict(data) if isinstance(data, dict) else {}
    level = _safe_int(payload.get("level"), 1)
    abilities = payload.get("abilities") if isinstance(payload.get("abilities"), dict) else {}
    constitution_score = _safe_int(abilities.get("constitution"), 10)
    prof_bonus = proficiency_bonus if isinstance(proficiency_bonus, int) else _get_proficiency_bonus(level)
    return 8 + prof_bonus + _ability_modifier(constitution_score)


def compute_dragonborn_breath_weapon_uses_max(_: int | None = None) -> int:
    return 1


def apply_dragonborn_breath_weapon_canonical_state(data: dict | None) -> dict:
    payload = dict(data) if isinstance(data, dict) else {}
    lineage = resolve_dragonborn_lineage_state(payload)
    class_resources = (
        dict(payload.get("classResources"))
        if isinstance(payload.get("classResources"), dict)
        else {}
    )

    if not lineage.get("ancestry"):
        class_resources.pop(DRAGONBORN_BREATH_WEAPON_RESOURCE_KEY, None)
        if class_resources:
            payload["classResources"] = class_resources
        else:
            payload.pop("classResources", None)
        return payload

    uses_max = compute_dragonborn_breath_weapon_uses_max(_safe_int(payload.get("level"), 1))
    existing = class_resources.get(DRAGONBORN_BREATH_WEAPON_RESOURCE_KEY)
    if isinstance(existing, dict):
        existing_remaining = _safe_int(existing.get("usesRemaining"), uses_max)
    else:
        existing_remaining = uses_max

    class_resources[DRAGONBORN_BREATH_WEAPON_RESOURCE_KEY] = {
        "usesMax": uses_max,
        "usesRemaining": max(0, min(existing_remaining, uses_max)),
    }
    payload["classResources"] = class_resources
    return payload


def resolve_dragonborn_breath_weapon_action_state(data: dict | None) -> dict[str, Any] | None:
    payload = apply_dragonborn_breath_weapon_canonical_state(data)
    lineage = resolve_dragonborn_lineage_state(payload)
    ancestry = lineage.get("ancestry")
    if not ancestry:
        return None

    class_resources = payload.get("classResources") if isinstance(payload.get("classResources"), dict) else {}
    resource = (
        class_resources.get(DRAGONBORN_BREATH_WEAPON_RESOURCE_KEY)
        if isinstance(class_resources, dict)
        else None
    )
    uses_max = _safe_int(resource.get("usesMax"), 1) if isinstance(resource, dict) else 1
    uses_remaining = _safe_int(resource.get("usesRemaining"), uses_max) if isinstance(resource, dict) else uses_max

    return {
        "actionId": DRAGONBORN_BREATH_WEAPON_ACTION_ID,
        "resourceKey": DRAGONBORN_BREATH_WEAPON_RESOURCE_KEY,
        "ancestry": ancestry,
        "ancestryLabel": lineage.get("ancestryLabel"),
        "damageType": lineage.get("damageType"),
        "saveType": lineage.get("breathWeaponSaveType"),
        "damageDice": compute_dragonborn_breath_weapon_damage_dice(_safe_int(payload.get("level"), 1)),
        "dc": compute_dragonborn_breath_weapon_dc(payload),
        "usesMax": uses_max,
        "usesRemaining": max(0, min(uses_remaining, uses_max)),
    }

