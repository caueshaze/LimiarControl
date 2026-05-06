"""Spell preparation logic for prepared and spellbook casters.

The long-rest flow seeds a pending preparation prompt at rest start, tracks
whether the player completed it during that rest, and falls back to the old
post-rest prompt when needed.
"""

from __future__ import annotations

from datetime import datetime, timezone

# Classes that use prepared spellcasting (including spellbook, which is a variant of prepared).
_PREPARED_CASTER_CLASSES: set[str] = {"cleric", "druid", "paladin", "wizard"}

# Half-casters use half their character level for spell slot / preparation scaling.
_HALF_CASTER_CLASSES: set[str] = {"paladin", "ranger"}

_PENDING_SPELL_PREPARATION_KEY = "pending_spell_preparation"
_LONG_REST_COMPLETION_MARKER_KEY = "spell_preparation_completed_during_long_rest"


def _normalize_class(class_id: str | None) -> str | None:
    if not isinstance(class_id, str):
        return None
    normalized = class_id.strip().lower()
    return normalized if normalized else None


def _ability_modifier(score: int) -> int:
    return (score - 10) // 2


def compute_prepared_spell_limit(
    class_id: str,
    character_level: int,
    ability_modifier: int,
) -> int:
    """Return the maximum number of leveled spells a prepared caster can prepare.

    Formula: caster_level + ability_modifier, minimum 1.
    Half-casters (e.g. Paladin) use floor(level / 2).
    Full casters use full character level.
    """
    normalized = _normalize_class(class_id)
    if normalized in _HALF_CASTER_CLASSES:
        caster_level = max(1, character_level // 2)
    else:
        caster_level = character_level
    return max(1, caster_level + ability_modifier)


def create_pending_spell_preparation(
    data: dict,
    *,
    available_during_rest: bool = False,
) -> dict | None:
    """Build a pending_spell_preparation dict if the character is eligible.

    Returns None for non-casters, known-spell casters, or characters without
    a valid spellcasting block.
    """
    class_id = data.get("class")
    level = data.get("level")
    spellcasting = data.get("spellcasting")

    if not class_id or not level or not isinstance(spellcasting, dict):
        return None

    normalized = _normalize_class(class_id)
    if normalized not in _PREPARED_CASTER_CLASSES:
        return None

    ability = spellcasting.get("ability")
    spells = spellcasting.get("spells", [])
    if not ability or not spells:
        return None

    abilities = data.get("abilities", {})
    score = 10
    if isinstance(abilities, dict):
        raw_score = abilities.get(ability)
        if isinstance(raw_score, int):
            score = raw_score

    modifier = _ability_modifier(score)
    prepared_limit = compute_prepared_spell_limit(normalized, int(level), modifier)

    # Current prepared spell IDs (leveled spells only; cantrips excluded from limit).
    current_prepared = [
        s.get("id")
        for s in spells
        if isinstance(s, dict)
        and s.get("prepared") is True
        and s.get("level", 0) > 0
    ]

    return {
        "source": "long_rest",
        "class_key": normalized,
        "prepared_limit": prepared_limit,
        "current_prepared_spell_ids": current_prepared,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "available_during_rest": available_during_rest,
    }


def apply_prepared_spells(data: dict, prepared_spell_ids: list[str]) -> dict:
    """Update spellcasting.spells[].prepared flags and clear pending state.

    Cantrips are always set to prepared=True.
    Leveled spells are prepared only if their id is in prepared_spell_ids.
    """
    next_data = dict(data)
    spellcasting = next_data.get("spellcasting")
    if not isinstance(spellcasting, dict):
        next_data.pop("pending_spell_preparation", None)
        return next_data

    spells = list(spellcasting.get("spells", []))
    prepared_set = set(prepared_spell_ids)

    for spell in spells:
        if not isinstance(spell, dict):
            continue
        if spell.get("level", 0) == 0:
            spell["prepared"] = True
        else:
            spell["prepared"] = spell.get("id") in prepared_set

    next_data["spellcasting"] = {**spellcasting, "spells": spells}
    next_data.pop("pending_spell_preparation", None)
    return next_data


def seed_long_rest_spell_preparation(data: dict) -> dict:
    """Replace any stale pending spell prep with the active long-rest prompt."""
    next_data = dict(data)
    next_data.pop(_LONG_REST_COMPLETION_MARKER_KEY, None)
    next_data.pop(_PENDING_SPELL_PREPARATION_KEY, None)

    pending = create_pending_spell_preparation(next_data, available_during_rest=True)
    if pending:
        next_data[_PENDING_SPELL_PREPARATION_KEY] = pending
    return next_data


def apply_prepared_spells_with_long_rest_tracking(
    data: dict,
    prepared_spell_ids: list[str],
) -> dict:
    """Apply prepared spells and mark that the player finished the long-rest prompt."""
    next_data = apply_prepared_spells(data, prepared_spell_ids)
    pending = data.get(_PENDING_SPELL_PREPARATION_KEY)
    if (
        data.get("restState") == "long_rest"
        and isinstance(pending, dict)
        and pending.get("available_during_rest") is True
    ):
        next_data[_LONG_REST_COMPLETION_MARKER_KEY] = True
    return next_data


def settle_long_rest_spell_preparation(data: dict) -> dict:
    """Finalize the long-rest spell preparation prompt after the rest ends."""
    next_data = dict(data)
    pending = next_data.get(_PENDING_SPELL_PREPARATION_KEY)
    completed_during_rest = bool(next_data.get(_LONG_REST_COMPLETION_MARKER_KEY))

    if not isinstance(pending, dict) and not completed_during_rest:
        pending = create_pending_spell_preparation(next_data, available_during_rest=False)
        if pending:
            next_data[_PENDING_SPELL_PREPARATION_KEY] = pending

    next_data.pop(_LONG_REST_COMPLETION_MARKER_KEY, None)
    return next_data
