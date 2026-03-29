from __future__ import annotations

from app.services.class_progression import apply_level_up_stats, recompute_hit_points
from app.services.dragonborn_breath_weapon import apply_dragonborn_breath_weapon_canonical_state
from app.services.guardian_progression import apply_guardian_canonical_state
from app.services.sorcerer_progression import apply_sorcerer_canonical_state
from app.services.xp_thresholds import MAX_LEVEL, can_level_up, get_xp_for_next_level


class CharacterProgressionError(ValueError):
    pass


def _clone_sheet_data(data: dict | None) -> dict:
    return dict(data) if isinstance(data, dict) else {}


def grant_experience(data: dict | None, amount: int) -> dict:
    if amount < 1:
        raise CharacterProgressionError("Grant amount must be greater than zero")

    next_data = _clone_sheet_data(data)
    current_xp = int(next_data.get("experiencePoints", 0))
    next_data["experiencePoints"] = current_xp + amount
    return next_data


def request_level_up(data: dict | None) -> dict:
    next_data = _clone_sheet_data(data)
    current_level = int(next_data.get("level", 1))
    current_xp = int(next_data.get("experiencePoints", 0))

    if current_level >= MAX_LEVEL:
        raise CharacterProgressionError("Already at max level")
    if next_data.get("pendingLevelUp"):
        raise CharacterProgressionError("Level-up already requested")
    if not can_level_up(current_level, current_xp):
        raise CharacterProgressionError("Not enough XP to level up")

    next_data["pendingLevelUp"] = True
    return next_data


def approve_level_up(data: dict | None) -> dict:
    next_data = _clone_sheet_data(data)
    current_level = int(next_data.get("level", 1))
    current_xp = int(next_data.get("experiencePoints", 0))
    previous_constitution = _get_constitution_score(next_data)

    if not next_data.get("pendingLevelUp"):
        raise CharacterProgressionError("No pending level-up request")
    if current_level >= MAX_LEVEL:
        raise CharacterProgressionError("Already at max level")
    if not can_level_up(current_level, current_xp):
        raise CharacterProgressionError("Not enough XP to level up")

    new_level = current_level + 1
    next_data["level"] = new_level
    next_data["pendingLevelUp"] = False
    next_data = apply_level_up_stats(next_data, new_level)
    next_data = apply_guardian_canonical_state(next_data, previous_level=current_level)
    next_data = apply_sorcerer_canonical_state(next_data)
    next_data = apply_dragonborn_breath_weapon_canonical_state(next_data)
    if _get_constitution_score(next_data) != previous_constitution:
        next_data = recompute_hit_points(next_data, preserve_damage=True)
    return next_data


def deny_level_up(data: dict | None) -> dict:
    next_data = _clone_sheet_data(data)
    if not next_data.get("pendingLevelUp"):
        raise CharacterProgressionError("No pending level-up request")
    next_data["pendingLevelUp"] = False
    return next_data


def build_progression_snapshot(data: dict | None) -> dict[str, int | bool | None]:
    snapshot = _clone_sheet_data(data)
    current_level = int(snapshot.get("level", 1))
    current_xp = int(snapshot.get("experiencePoints", 0))
    return {
        "level": current_level,
        "experiencePoints": current_xp,
        "pendingLevelUp": bool(snapshot.get("pendingLevelUp", False)),
        "nextLevelThreshold": get_xp_for_next_level(current_level),
    }


def _get_constitution_score(data: dict) -> int:
    abilities = data.get("abilities")
    if not isinstance(abilities, dict):
        return 10
    value = abilities.get("constitution", 10)
    return int(value) if isinstance(value, int) else 10
