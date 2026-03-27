from __future__ import annotations

import random
import re
from math import floor
from typing import Callable, Literal


RestState = Literal["exploration", "short_rest", "long_rest"]

_REST_STATES = {"exploration", "short_rest", "long_rest"}
_HIT_DIE_RE = re.compile(r"^d(\d+)$", re.IGNORECASE)


class SessionRestError(ValueError):
    pass


def normalize_rest_state(value: object) -> RestState:
    if isinstance(value, str) and value in _REST_STATES:
        return value
    return "exploration"


def ensure_rest_state(data: dict | None) -> dict:
    next_data = dict(data) if isinstance(data, dict) else {}
    next_data["restState"] = normalize_rest_state(next_data.get("restState"))
    return next_data


def start_rest(data: dict | None, rest_type: RestState) -> dict:
    if rest_type not in {"short_rest", "long_rest"}:
        raise SessionRestError("Invalid rest type")

    next_data = ensure_rest_state(data)
    current_state = normalize_rest_state(next_data.get("restState"))
    if current_state != "exploration":
        raise SessionRestError("A rest is already active")

    next_data["restState"] = rest_type
    return next_data


def end_rest(data: dict | None) -> tuple[dict, RestState]:
    next_data = ensure_rest_state(data)
    current_state = normalize_rest_state(next_data.get("restState"))
    if current_state == "exploration":
        raise SessionRestError("No rest is active")

    if current_state == "short_rest":
        next_data["restState"] = "exploration"
        # Wild Shape recharges on short rest
        next_data = _recharge_wild_shape_inline(next_data)
        return next_data, "short_rest"

    return apply_long_rest(next_data), "long_rest"


def use_hit_die(
    data: dict | None,
    *,
    roller: Callable[[int, int], int] | None = None,
) -> tuple[dict, dict]:
    next_data = ensure_rest_state(data)
    if normalize_rest_state(next_data.get("restState")) != "short_rest":
        raise SessionRestError("Hit Dice can only be used during a short rest")

    hit_dice_remaining = _safe_int(next_data.get("hitDiceRemaining"))
    hit_dice_total = _safe_int(next_data.get("hitDiceTotal"))
    if hit_dice_remaining <= 0:
        raise SessionRestError("No Hit Dice remaining")

    hit_die_type, sides = _parse_hit_die(next_data.get("hitDiceType"))
    roller_fn = roller or random.randint
    roll = roller_fn(1, sides)
    constitution_modifier = _constitution_modifier(next_data.get("abilities"))
    healing_rolled = max(0, roll + constitution_modifier)

    current_hp = _safe_int(next_data.get("currentHP"))
    max_hp = max(0, _safe_int(next_data.get("maxHP")))
    next_current_hp = min(max_hp, current_hp + healing_rolled)
    healing_applied = max(0, next_current_hp - current_hp)

    next_data["currentHP"] = next_current_hp
    next_data["hitDiceRemaining"] = hit_dice_remaining - 1

    return next_data, {
        "constitutionModifier": constitution_modifier,
        "currentHp": next_current_hp,
        "healingApplied": healing_applied,
        "healingRolled": healing_rolled,
        "hitDiceRemaining": hit_dice_remaining - 1,
        "hitDiceTotal": hit_dice_total,
        "hitDieType": hit_die_type,
        "maxHp": max_hp,
        "roll": roll,
    }


def _recharge_wild_shape_inline(data: dict) -> dict:
    """Restore Wild Shape uses. Inlined to avoid circular imports."""
    wild_shape = data.get("wildShape")
    if not isinstance(wild_shape, dict):
        return data
    try:
        level = int(data.get("level", 1))
    except (TypeError, ValueError):
        level = 1
    uses_max = wild_shape.get("usesMax")
    if not isinstance(uses_max, int):
        uses_max = 99 if level >= 20 else 2
    return {**data, "wildShape": {**wild_shape, "usesRemaining": uses_max}}


def _force_revert_wild_shape_inline(data: dict) -> dict:
    """Revert beast form and restore humanoid HP. Inlined to avoid circular imports."""
    wild_shape = data.get("wildShape")
    if not isinstance(wild_shape, dict) or not wild_shape.get("active"):
        return data
    saved_hp = wild_shape.get("savedHumanoidHP")
    try:
        saved_hp = int(saved_hp)
    except (TypeError, ValueError):
        saved_hp = 0
    try:
        max_hp = int(data.get("maxHP", 0))
    except (TypeError, ValueError):
        max_hp = 0
    restored_hp = min(saved_hp, max_hp)
    new_ws = {
        **wild_shape,
        "active": False,
        "formKey": None,
        "formCurrentHP": 0,
        "savedHumanoidHP": None,
    }
    return {**data, "wildShape": new_ws, "currentHP": restored_hp}


def apply_long_rest(data: dict | None) -> dict:
    next_data = ensure_rest_state(data)

    max_hp = max(0, _safe_int(next_data.get("maxHP")))
    hit_dice_total = max(0, _safe_int(next_data.get("hitDiceTotal")))
    hit_dice_remaining = max(0, _safe_int(next_data.get("hitDiceRemaining")))
    hit_dice_recovered = 0 if hit_dice_total <= 0 else max(1, floor(hit_dice_total / 2))

    next_data["currentHP"] = max_hp
    next_data["tempHP"] = 0
    next_data["hitDiceRemaining"] = min(hit_dice_total, hit_dice_remaining + hit_dice_recovered)
    next_data["deathSaves"] = {"successes": 0, "failures": 0}
    next_data["restState"] = "exploration"

    spellcasting = next_data.get("spellcasting")
    if isinstance(spellcasting, dict):
        slots = spellcasting.get("slots")
        if isinstance(slots, dict):
            next_slots: dict = {}
            for level, slot in slots.items():
                if isinstance(slot, dict):
                    next_slots[level] = {
                        "max": max(0, _safe_int(slot.get("max"))),
                        "used": 0,
                    }
                else:
                    next_slots[level] = slot
            next_data["spellcasting"] = {
                **spellcasting,
                "slots": next_slots,
            }

    # Wild Shape: force revert if active, then recharge uses
    next_data = _force_revert_wild_shape_inline(next_data)
    next_data = _recharge_wild_shape_inline(next_data)

    return next_data


def _constitution_modifier(abilities: object) -> int:
    if not isinstance(abilities, dict):
        return 0
    constitution = _safe_int(abilities.get("constitution"), 10)
    return floor((constitution - 10) / 2)


def _parse_hit_die(value: object) -> tuple[str, int]:
    if not isinstance(value, str):
        raise SessionRestError("Invalid hit die type")
    normalized = value.strip().lower()
    match = _HIT_DIE_RE.match(normalized)
    if not match:
        raise SessionRestError("Invalid hit die type")
    sides = int(match.group(1))
    if sides <= 0:
        raise SessionRestError("Invalid hit die type")
    return normalized, sides


def _safe_int(value: object, fallback: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback
