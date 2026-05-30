"""Shared helpers for the Warding Bond spell.

Warding Bond links a caster and a target with two paired effects that share a
``bond_group``. The mechanical effect lives on the target ("target" role); a
marker lives on the caster ("caster" role). The bond is torn down as a unit when

  * the spell is recast on either connected creature,
  * the caster drops to 0 HP,
  * caster and target separate by more than 18 m.

These pure functions operate on a ``CombatState`` and its ``participants`` list
so they can be reused across the automation handler, the damage pipeline, and
the turn lifecycle without depending on a particular mixin's MRO.

Bonds are keyed by participant ``ref_id`` (stored in the effect metadata under
``bond_caster_participant_id`` / ``bond_target_participant_id``). A player's
``ref_id`` equals their ``player_user_id``, so an out-of-combat cast can store
the same identifiers and the bond resolves seamlessly once combat restores the
persisted effects onto the matching participants — no id rewrite needed.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm.attributes import flag_modified

WARDING_BOND_KEY = "warding_bond"
MAX_BOND_DISTANCE_METERS = 18.0


def _effect_metadata(effect: Any) -> dict:
    if not isinstance(effect, dict):
        return {}
    metadata = effect.get("metadata")
    return metadata if isinstance(metadata, dict) else {}


def _is_warding_bond_effect(effect: Any) -> bool:
    if not isinstance(effect, dict) or effect.get("kind") != "spell_effect":
        return False
    return _effect_metadata(effect).get("source_spell_key") == WARDING_BOND_KEY


def find_target_role_effect(participant: dict | None) -> dict | None:
    """Return the active target-role Warding Bond effect on a participant."""
    if not isinstance(participant, dict):
        return None
    for effect in participant.get("active_effects") or []:
        if _is_warding_bond_effect(effect) and _effect_metadata(effect).get("warding_bond_role") == "target":
            return effect
    return None


def _participant_by_ref(state, ref_id: str | None) -> dict | None:
    if not ref_id:
        return None
    for participant in state.participants or []:
        if isinstance(participant, dict) and participant.get("ref_id") == ref_id:
            return participant
    return None


def remove_warding_bonds_involving_participants(
    state,
    participant_ids,
) -> list[dict]:
    """Remove every Warding Bond effect (both roles, on every participant) whose
    bond involves any of ``participant_ids``. Returns the removed effects."""
    ids = {pid for pid in participant_ids if pid}
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
            if _is_warding_bond_effect(effect) and (
                {metadata.get("bond_caster_participant_id"), metadata.get("bond_target_participant_id")} & ids
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


def break_warding_bonds_for_caster(state, caster_ref_id: str | None) -> list[dict]:
    """Tear down every bond cast by ``caster_ref_id`` (caster at 0 HP)."""
    caster = _participant_by_ref(state, caster_ref_id)
    if caster is None:
        # Even without the participant present, purge by ref so stale target
        # effects referencing this caster do not linger.
        return remove_warding_bonds_involving_participants(state, [caster_ref_id])
    bond_ids: set[str] = set()
    for effect in caster.get("active_effects") or []:
        metadata = _effect_metadata(effect)
        if _is_warding_bond_effect(effect) and metadata.get("warding_bond_role") == "caster":
            bond_ids.add(metadata.get("bond_caster_participant_id"))
            bond_ids.add(metadata.get("bond_target_participant_id"))
    bond_ids.discard(None)
    if not bond_ids:
        return []
    return remove_warding_bonds_involving_participants(state, bond_ids)


def break_warding_bonds_exceeding_distance(state) -> list[dict]:
    """Break any bond whose caster and target are more than 18 m apart.

    Distance is read from ``state.local_distances``; an unconfigured distance
    (``None``) never breaks the bond.
    """
    from .combat_service.combat_targeting_local import _get_local_distance

    to_break: list[set[str]] = []
    seen_groups: set[str] = set()
    for participant in state.participants or []:
        if not isinstance(participant, dict):
            continue
        for effect in participant.get("active_effects") or []:
            metadata = _effect_metadata(effect)
            if not _is_warding_bond_effect(effect) or metadata.get("warding_bond_role") != "target":
                continue
            group = metadata.get("bond_group")
            if group in seen_groups:
                continue
            seen_groups.add(group)
            caster_ref = metadata.get("bond_caster_participant_id")
            target_ref = metadata.get("bond_target_participant_id")
            if _participant_by_ref(state, caster_ref) is None or _participant_by_ref(state, target_ref) is None:
                continue
            distance = _get_local_distance(state, caster_ref, target_ref)
            if distance is not None and distance > MAX_BOND_DISTANCE_METERS:
                to_break.append(
                    {
                        metadata.get("bond_caster_participant_id"),
                        metadata.get("bond_target_participant_id"),
                    }
                )
    removed: list[dict] = []
    for ids in to_break:
        removed.extend(remove_warding_bonds_involving_participants(state, ids))
    return removed
