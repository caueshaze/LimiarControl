from __future__ import annotations

from typing import Any

SLEEP_KEY = "sleep"


def _metadata(effect: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(effect, dict):
        return {}
    metadata = effect.get("metadata")
    return metadata if isinstance(metadata, dict) else {}


def is_sleep_unconscious_effect(effect: dict[str, Any] | None) -> bool:
    """True for an `unconscious` condition created by the Sleep spell."""
    if not isinstance(effect, dict):
        return False
    if effect.get("kind") != "condition":
        return False
    if str(effect.get("condition_type") or "").strip().lower() != "unconscious":
        return False
    return str(_metadata(effect).get("source_spell_key") or "").strip().lower() == SLEEP_KEY


def find_sleep_unconscious_effects(
    participant: dict | None,
    *,
    source_effect_id: str | None = None,
) -> list[dict]:
    """Return the participant's Sleep `unconscious` conditions.

    When `source_effect_id` is provided, only conditions from that cast instance
    are returned.
    """
    if not isinstance(participant, dict):
        return []
    matches: list[dict] = []
    for effect in participant.get("active_effects") or []:
        if not is_sleep_unconscious_effect(effect):
            continue
        if isinstance(source_effect_id, str) and source_effect_id.strip():
            if _metadata(effect).get("source_effect_id") != source_effect_id.strip():
                continue
        matches.append(effect)
    return matches


def remove_sleep_unconscious_on_damage(participant: dict | None, amount: int) -> list[dict]:
    """Wake a Sleep sleeper that takes damage.

    Removes Sleep `unconscious` conditions when `amount > 0`. `unconscious` from
    any other source is left untouched. Returns the removed effects.
    """
    if not isinstance(participant, dict) or amount <= 0:
        return []
    effects = participant.get("active_effects") or []
    removed: list[dict] = []
    kept: list[dict] = []
    for effect in effects:
        if is_sleep_unconscious_effect(effect):
            removed.append(effect)
        else:
            kept.append(effect)
    if removed:
        participant["active_effects"] = kept
    return removed


def remove_sleep_unconscious_instance(participant: dict | None, effect_id: str) -> bool:
    """Remove a single Sleep `unconscious` condition by effect id (wake action)."""
    if not isinstance(participant, dict) or not effect_id:
        return False
    effects = participant.get("active_effects") or []
    kept = [
        effect
        for effect in effects
        if not (is_sleep_unconscious_effect(effect) and effect.get("id") == effect_id)
    ]
    if len(kept) == len(effects):
        return False
    participant["active_effects"] = kept
    return True
