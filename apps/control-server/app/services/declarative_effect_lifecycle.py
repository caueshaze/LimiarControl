"""Lifecycle helpers for declarative spell effects.

Handles applicability (requires_unarmored → AC formula skipped) separately from
termination (target_dons_armor, target_takes_damage_from_caster_or_allies → effect
permanently removed).
"""

from __future__ import annotations

_ARMOR_TYPES = {"light", "medium", "heavy"}
_FRIENDLY_TEAMS = frozenset({"players", "allies"})


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


# ---------------------------------------------------------------------------
# Damage-break termination (target_takes_damage_from_caster_or_allies)
# ---------------------------------------------------------------------------

def _get_effect_termination_conditions(effect: dict) -> list[dict]:
    """Return termination_conditions for an effect, checking both storage locations.

    Automation-built effects (e.g. Animal Friendship charmed) store them directly
    in metadata.  Declarative effects store them inside metadata.declarative_effect.
    """
    if not isinstance(effect, dict):
        return []
    metadata = effect.get("metadata") or {}
    # Direct metadata (automation-built effects)
    direct = metadata.get("termination_conditions")
    if isinstance(direct, list):
        return direct
    # Nested inside declarative_effect (SpellDeclarativeEffect)
    declarative = metadata.get("declarative_effect") or {}
    nested = declarative.get("termination_conditions")
    return nested if isinstance(nested, list) else []


def _get_caster_participant_id_for_effect(effect: dict) -> str | None:
    """Return the participant ID of the spell's caster stored in effect metadata."""
    if not isinstance(effect, dict):
        return None
    metadata = effect.get("metadata") or {}
    # Standard key used by declarative effects and new automation effects
    caster_id = metadata.get("caster_participant_id")
    if isinstance(caster_id, str):
        return caster_id
    # Legacy key kept for old Animal Friendship effects in DB
    charmer_id = metadata.get("charmer_participant_id")
    return charmer_id if isinstance(charmer_id, str) else None


def _are_friendly_participants(p1: dict, p2: dict) -> bool:
    """Return True if p1 and p2 are on the same side (allies of each other)."""
    if p1.get("id") == p2.get("id"):
        return True
    t1, t2 = p1.get("team"), p2.get("team")
    if t1 == t2 and t1 is not None:
        return True
    return t1 in _FRIENDLY_TEAMS and t2 in _FRIENDLY_TEAMS


def _effect_has_damage_termination(effect: dict) -> bool:
    return any(
        isinstance(c, dict) and c.get("type") == "target_takes_damage_from_caster_or_allies"
        for c in _get_effect_termination_conditions(effect)
    )


def _find_participant_by_id(participants: list, participant_id: str | None) -> dict | None:
    if not participant_id:
        return None
    return next((p for p in participants if isinstance(p, dict) and p.get("id") == participant_id), None)


def find_damage_terminated_effect_ids(
    participants: list,
    target_participant: dict,
    attacker_participant_id: str,
) -> list[str]:
    """Return IDs of effects that should terminate because attacker is caster or ally.

    Only considers effects with `target_takes_damage_from_caster_or_allies` termination
    condition.
    """
    attacker = _find_participant_by_id(participants, attacker_participant_id)
    if attacker is None:
        return []

    terminated: list[str] = []
    for effect in (target_participant.get("active_effects") or []):
        if not isinstance(effect, dict) or not _effect_has_damage_termination(effect):
            continue
        effect_id = effect.get("id")
        if not isinstance(effect_id, str):
            continue
        caster_id = _get_caster_participant_id_for_effect(effect)
        caster = _find_participant_by_id(participants, caster_id)
        if caster is None:
            continue
        if _are_friendly_participants(attacker, caster):
            terminated.append(effect_id)
    return terminated


def remove_damage_terminated_effects_from_participant(
    state,
    target_participant: dict,
    attacker_participant_id: str,
) -> bool:
    """Remove effects from target_participant that break on damage from caster/allies.

    Mutates target_participant["active_effects"] in place.
    Returns True if any effects were removed.
    """
    participants = state.participants if state is not None else []
    terminated_ids = set(
        find_damage_terminated_effect_ids(participants, target_participant, attacker_participant_id)
    )
    if not terminated_ids:
        return False
    surviving = [e for e in (target_participant.get("active_effects") or []) if e.get("id") not in terminated_ids]
    target_participant["active_effects"] = surviving
    return True


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
