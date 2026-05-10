"""Lifecycle helpers for declarative spell effects.

Handles applicability (requires_unarmored → AC formula skipped) separately from
termination (target_dons_armor → effect permanently removed).
"""

from __future__ import annotations

_ARMOR_TYPES = {"light", "medium", "heavy"}


def _has_equipped_armor(state_json: dict) -> bool:
    armor = state_json.get("equippedArmor") or {}
    if not isinstance(armor, dict):
        return False
    armor_type = (armor.get("armorType") or "").strip().lower()
    return armor_type in _ARMOR_TYPES


def _effect_has_target_dons_armor_termination(effect: dict) -> bool:
    """Return True if a persisted effect carries a target_dons_armor termination rule."""
    if not isinstance(effect, dict):
        return False
    metadata = effect.get("metadata") or {}
    declarative = metadata.get("declarative_effect") or {}
    termination_conditions = declarative.get("termination_conditions") or []
    return any(
        isinstance(cond, dict) and cond.get("type") == "target_dons_armor"
        for cond in termination_conditions
    )


def terminate_armor_don_effects_from_state(state_json: dict) -> dict:
    """Remove persisted declarative effects that end when the target dons armor.

    Only removes effects when the state already reflects armor being equipped.
    Idempotent and non-destructive: returns state_json unchanged when no
    termination is needed.
    """
    if not _has_equipped_armor(state_json):
        return state_json

    effects = state_json.get("active_spell_effects")
    if not isinstance(effects, list) or not effects:
        return state_json

    surviving = [e for e in effects if not _effect_has_target_dons_armor_termination(e)]
    if len(surviving) == len(effects):
        return state_json

    data = dict(state_json)
    if surviving:
        data["active_spell_effects"] = surviving
    else:
        data.pop("active_spell_effects", None)
    return data


def find_armor_don_terminated_effect_ids(participant_effects: list[dict]) -> list[str]:
    """Return IDs of active combat effects that carry a target_dons_armor termination rule."""
    return [
        e["id"]
        for e in participant_effects
        if isinstance(e, dict)
        and isinstance(e.get("id"), str)
        and _effect_has_target_dons_armor_termination(e)
    ]


def remove_armor_don_effects_from_combat_participant(
    combat_state,
    player_user_id: str,
) -> bool:
    """Remove active combat effects with target_dons_armor termination from a player participant.

    Returns True if any effects were removed. Mutates combat_state.participants in place.
    """
    participant = next(
        (
            p for p in (combat_state.participants if combat_state else [])
            if p.get("kind") == "player" and p.get("ref_id") == player_user_id
        ),
        None,
    )
    if not participant:
        return False
    effects = participant.get("active_effects") or []
    terminated_ids = set(find_armor_don_terminated_effect_ids(effects))
    if not terminated_ids:
        return False
    participant["active_effects"] = [e for e in effects if e.get("id") not in terminated_ids]
    return True
