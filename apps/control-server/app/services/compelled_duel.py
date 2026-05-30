"""Shared helpers for the Compelled Duel spell.

Compelled Duel places a single concentration effect on the *target* (the
compelled creature). The effect carries the caster identity so the engine
derives the caster's concentration from it — no separate caster marker exists.

The spell ends when:
  * the caster attacks any other creature, or casts a hostile spell on a
    creature other than the target;
  * a creature friendly to the caster damages the target or casts a harmful
    spell on it;
  * the caster ends their turn more than 9 m from the target;
  * the target dies;
  * the caster's concentration ends (handled by the concentration machinery).

These pure functions operate on a ``CombatState`` and its ``participants`` list
so they can be reused across the attack pipeline, the damage pipeline, the
spell-commit paths, and the turn lifecycle. Bonds are keyed by participant
``ref_id`` (stored in metadata as ``duel_caster_ref_id``/``duel_target_ref_id``),
consistent with ``local_distances`` and the Warding Bond helpers.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm.attributes import flag_modified

COMPELLED_DUEL_KEY = "compelled_duel"
MAX_DUEL_DISTANCE_METERS = 9.0
_FRIENDLY_TEAMS = {"players", "allies"}


def _effect_metadata(effect: Any) -> dict:
    if not isinstance(effect, dict):
        return {}
    metadata = effect.get("metadata")
    return metadata if isinstance(metadata, dict) else {}


def _is_compelled_duel_effect(effect: Any) -> bool:
    if not isinstance(effect, dict) or effect.get("kind") != "spell_effect":
        return False
    return _effect_metadata(effect).get("source_spell_key") == COMPELLED_DUEL_KEY


def find_compelled_duel_effect_on_target(participant: dict | None) -> dict | None:
    """Return the active Compelled Duel effect carried by a compelled target."""
    if not isinstance(participant, dict):
        return None
    for effect in participant.get("active_effects") or []:
        if _is_compelled_duel_effect(effect):
            return effect
    return None


def _participant_by_ref(state, ref_id: str | None) -> dict | None:
    if not ref_id:
        return None
    for participant in state.participants or []:
        if isinstance(participant, dict) and participant.get("ref_id") == ref_id:
            return participant
    return None


def _team(participant: dict | None) -> str:
    if not isinstance(participant, dict):
        return ""
    return str(participant.get("team") or "").strip().lower()


def _are_friendly(a: dict | None, b: dict | None) -> bool:
    """True if a and b are on the same side (both friendly, or both enemies)."""
    ta, tb = _team(a), _team(b)
    if not ta or not tb:
        return False
    if ta in _FRIENDLY_TEAMS and tb in _FRIENDLY_TEAMS:
        return True
    return ta == "enemies" and tb == "enemies"


def remove_compelled_duels_involving(state, ref_ids) -> list[dict]:
    """Remove every Compelled Duel effect whose bond involves any of ``ref_ids``."""
    ids = {rid for rid in ref_ids if rid}
    if not ids:
        return []
    removed: list[dict] = []
    changed = False
    for participant in state.participants or []:
        if not isinstance(participant, dict):
            continue
        effects = participant.get("active_effects")
        if not isinstance(effects, list) or not effects:
            continue
        kept: list[dict] = []
        for effect in effects:
            metadata = _effect_metadata(effect)
            if _is_compelled_duel_effect(effect) and (
                {metadata.get("duel_caster_ref_id"), metadata.get("duel_target_ref_id")} & ids
            ):
                removed.append(effect)
                continue
            kept.append(effect)
        if len(kept) != len(effects):
            participant["active_effects"] = kept
            changed = True
    if changed:
        flag_modified(state, "participants")
    return removed


def _duel_caster_ref_for_target(state, target_ref: str) -> str | None:
    target = _participant_by_ref(state, target_ref)
    effect = find_compelled_duel_effect_on_target(target)
    if effect is None:
        return None
    return _effect_metadata(effect).get("duel_caster_ref_id")


def break_compelled_duel_if_caster_attacks_other(state, attacker_ref, attacked_ref) -> list[dict]:
    """End duels cast by ``attacker_ref`` when they attack/target a creature
    other than their own duel target."""
    if not attacker_ref:
        return []
    to_break: set[str] = set()
    for participant in state.participants or []:
        effect = find_compelled_duel_effect_on_target(participant)
        if effect is None:
            continue
        metadata = _effect_metadata(effect)
        if metadata.get("duel_caster_ref_id") != attacker_ref:
            continue
        if metadata.get("duel_target_ref_id") != attacked_ref:
            to_break.add(metadata.get("duel_target_ref_id"))
    if not to_break:
        return []
    return remove_compelled_duels_involving(state, {attacker_ref, *to_break})


def break_compelled_duel_if_ally_harms_target(state, actor_ref, target_ref) -> list[dict]:
    """End the duel on ``target_ref`` if ``actor_ref`` is friendly to the duel
    caster (and is not the caster). Covers ally damage and ally harmful spells."""
    if not actor_ref or not target_ref or actor_ref == target_ref:
        return []
    caster_ref = _duel_caster_ref_for_target(state, target_ref)
    if not caster_ref or actor_ref == caster_ref:
        return []
    actor = _participant_by_ref(state, actor_ref)
    caster = _participant_by_ref(state, caster_ref)
    if not _are_friendly(actor, caster):
        return []
    return remove_compelled_duels_involving(state, {caster_ref, target_ref})


def break_compelled_duel_on_target_defeated(state, target_ref) -> list[dict]:
    """End the duel when the compelled target is reduced to 0 HP / defeated."""
    if not target_ref:
        return []
    caster_ref = _duel_caster_ref_for_target(state, target_ref)
    if not caster_ref:
        return []
    return remove_compelled_duels_involving(state, {caster_ref, target_ref})


def break_compelled_duels_exceeding_distance(state, caster_ref) -> list[dict]:
    """End duels cast by ``caster_ref`` when caster and target are >9 m apart.

    Distance is read from ``state.local_distances``; an unconfigured distance
    (``None``) never breaks the duel.
    """
    if not caster_ref:
        return []
    from .combat_service.combat_targeting_local import _get_local_distance

    to_break: set[str] = set()
    for participant in state.participants or []:
        effect = find_compelled_duel_effect_on_target(participant)
        if effect is None:
            continue
        metadata = _effect_metadata(effect)
        if metadata.get("duel_caster_ref_id") != caster_ref:
            continue
        target_ref = metadata.get("duel_target_ref_id")
        distance = _get_local_distance(state, caster_ref, target_ref)
        if distance is not None and distance > MAX_DUEL_DISTANCE_METERS:
            to_break.add(target_ref)
    if not to_break:
        return []
    return remove_compelled_duels_involving(state, {caster_ref, *to_break})
