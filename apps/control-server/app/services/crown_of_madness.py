from __future__ import annotations

from typing import Any

CROWN_OF_MADNESS_KEY = "crown_of_madness"


def _metadata(effect: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(effect, dict):
        return {}
    metadata = effect.get("metadata")
    return metadata if isinstance(metadata, dict) else {}


def _is_crown_of_madness_effect(effect: dict[str, Any] | None) -> bool:
    if not isinstance(effect, dict):
        return False
    if effect.get("kind") != "spell_effect":
        return False
    return str(_metadata(effect).get("source_spell_key") or "").strip().lower() == CROWN_OF_MADNESS_KEY


def find_crown_of_madness_effect_on_target(participant: dict | None) -> dict | None:
    if not isinstance(participant, dict):
        return None
    for effect in participant.get("active_effects") or []:
        if _is_crown_of_madness_effect(effect):
            return effect
    return None


def mark_crown_of_madness_forced_attack_pending(participant: dict | None) -> bool:
    effect = find_crown_of_madness_effect_on_target(participant)
    if effect is None:
        return False
    metadata = _metadata(effect)
    metadata["forced_attack_pending"] = True
    metadata["forced_attack_resolved"] = False
    return True


def mark_crown_of_madness_forced_attack_resolved(
    participant: dict | None,
    *,
    skipped: bool,
) -> bool:
    effect = find_crown_of_madness_effect_on_target(participant)
    if effect is None:
        return False
    metadata = _metadata(effect)
    metadata["forced_attack_pending"] = False
    metadata["forced_attack_resolved"] = True
    metadata["forced_attack_skipped"] = skipped
    return True


def get_crown_of_madness_effects_for_caster(
    state,
    *,
    caster_participant_id: str,
) -> list[tuple[dict, dict]]:
    matches: list[tuple[dict, dict]] = []
    for participant in state.participants or []:
        for effect in participant.get("active_effects") or []:
            if not _is_crown_of_madness_effect(effect):
                continue
            if effect.get("source_participant_id") != caster_participant_id:
                continue
            matches.append((participant, effect))
    return matches


def remove_crown_of_madness_instance(
    state,
    *,
    concentration_group: str | None = None,
    source_effect_id: str | None = None,
) -> list[dict]:
    """Remove a Crown of Madness instance and linked charmed condition effects.

    Matching is instance-aware:
    - by concentration_group when provided;
    - by crown spell effect id when source_effect_id is provided.
    """
    if not concentration_group and not source_effect_id:
        return []

    removed: list[dict] = []
    for participant in state.participants or []:
        kept: list[dict] = []
        effects = participant.get("active_effects") or []
        for effect in effects:
            metadata = _metadata(effect)
            is_crown = _is_crown_of_madness_effect(effect)
            is_charmed_from_crown = (
                effect.get("kind") == "condition"
                and effect.get("condition_type") == "charmed"
                and str(metadata.get("source_spell_key") or "").strip().lower() == CROWN_OF_MADNESS_KEY
            )
            if not is_crown and not is_charmed_from_crown:
                kept.append(effect)
                continue

            matches_group = (
                isinstance(concentration_group, str)
                and concentration_group
                and metadata.get("concentration_group") == concentration_group
            )
            matches_effect = False
            if isinstance(source_effect_id, str) and source_effect_id:
                if is_crown and effect.get("id") == source_effect_id:
                    matches_effect = True
                elif metadata.get("source_effect_id") == source_effect_id:
                    matches_effect = True

            if matches_group or matches_effect:
                removed.append(
                    {
                        **effect,
                        "target_participant_id": participant.get("id"),
                        "target_display_name": participant.get("display_name", ""),
                    }
                )
                continue

            kept.append(effect)
        participant["active_effects"] = kept

    return removed
