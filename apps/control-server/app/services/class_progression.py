"""D&D 5e class progression tables and level-up stat computation."""

from __future__ import annotations

from math import floor

# ── Hit Dice by class ──────────────────────────────────────────────────────────

CLASS_HIT_DICE: dict[str, int] = {
    "barbarian": 12,
    "bard": 8,
    "cleric": 8,
    "druid": 8,
    "fighter": 10,
    "monk": 8,
    "paladin": 10,
    "ranger": 10,
    "rogue": 8,
    "sorcerer": 6,
    "warlock": 8,
    "wizard": 6,
}

# Average HP gained per level (PHB: floor(die/2) + 1)
_HP_AVERAGE_BY_DIE: dict[int, int] = {
    6: 4,
    8: 5,
    10: 6,
    12: 7,
}

# ── Spell Slot Tables (PHB) ────────────────────────────────────────────────────
# Format: {character_level: {slot_level: count}}
# Only non-zero slot counts are included per row.

_FULL_CASTER_SLOTS: dict[int, dict[int, int]] = {
    1:  {1: 2},
    2:  {1: 3},
    3:  {1: 4, 2: 2},
    4:  {1: 4, 2: 3},
    5:  {1: 4, 2: 3, 3: 2},
    6:  {1: 4, 2: 3, 3: 3},
    7:  {1: 4, 2: 3, 3: 3, 4: 1},
    8:  {1: 4, 2: 3, 3: 3, 4: 2},
    9:  {1: 4, 2: 3, 3: 3, 4: 3, 5: 1},
    10: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2},
    11: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1},
    12: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1},
    13: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1},
    14: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1},
    15: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1, 8: 1},
    16: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1, 8: 1},
    17: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1, 8: 1, 9: 1},
    18: {1: 4, 2: 3, 3: 3, 4: 3, 5: 3, 6: 1, 7: 1, 8: 1, 9: 1},
    19: {1: 4, 2: 3, 3: 3, 4: 3, 5: 3, 6: 2, 7: 1, 8: 1, 9: 1},
    20: {1: 4, 2: 3, 3: 3, 4: 3, 5: 3, 6: 2, 7: 2, 8: 1, 9: 1},
}

# Paladin / Ranger: half-caster, starts at class level 2 (PHB p.84, p.92)
_HALF_CASTER_SLOTS: dict[int, dict[int, int]] = {
    1:  {},
    2:  {1: 2},
    3:  {1: 3},
    4:  {1: 3},
    5:  {1: 4, 2: 2},
    6:  {1: 4, 2: 2},
    7:  {1: 4, 2: 3},
    8:  {1: 4, 2: 3},
    9:  {1: 4, 2: 3, 3: 2},
    10: {1: 4, 2: 3, 3: 2},
    11: {1: 4, 2: 3, 3: 3},
    12: {1: 4, 2: 3, 3: 3},
    13: {1: 4, 2: 3, 3: 3, 4: 1},
    14: {1: 4, 2: 3, 3: 3, 4: 1},
    15: {1: 4, 2: 3, 3: 3, 4: 2},
    16: {1: 4, 2: 3, 3: 3, 4: 2},
    17: {1: 4, 2: 3, 3: 3, 4: 3, 5: 1},
    18: {1: 4, 2: 3, 3: 3, 4: 3, 5: 1},
    19: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2},
    20: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2},
}

# Warlock: pact magic — all slots are at a single escalating level (PHB p.107)
# Format is {slot_level: count} for the character level key.
_WARLOCK_SLOTS: dict[int, dict[int, int]] = {
    1:  {1: 1},
    2:  {1: 2},
    3:  {2: 2},
    4:  {2: 2},
    5:  {3: 2},
    6:  {3: 2},
    7:  {4: 2},
    8:  {4: 2},
    9:  {5: 2},
    10: {5: 2},
    11: {5: 3},
    12: {5: 3},
    13: {5: 3},
    14: {5: 3},
    15: {5: 3},
    16: {5: 3},
    17: {5: 4},
    18: {5: 4},
    19: {5: 4},
    20: {5: 4},
}

# Classes not in this map are non-casters: no spell slots.
_CLASS_SLOT_TABLES: dict[str, dict[int, dict[int, int]]] = {
    "bard":     _FULL_CASTER_SLOTS,
    "cleric":   _FULL_CASTER_SLOTS,
    "druid":    _FULL_CASTER_SLOTS,
    "sorcerer": _FULL_CASTER_SLOTS,
    "wizard":   _FULL_CASTER_SLOTS,
    "paladin":  _HALF_CASTER_SLOTS,
    "ranger":   _HALF_CASTER_SLOTS,
    "warlock":  _WARLOCK_SLOTS,
}

_CLASS_MECHANICS_FAMILIES: dict[str, str] = {
    "guardian": "ranger",
}

# ── Public API ─────────────────────────────────────────────────────────────────


def get_spell_slots_for_class_level(class_id: str, level: int) -> dict[int, int] | None:
    """Return {slot_level: count} for the given class at the given character level.

    Returns None for non-caster classes (no spellcasting entry at all).
    Returns an empty dict for casters that have no slots yet at this level
    (e.g. paladin level 1).
    """
    table = _CLASS_SLOT_TABLES.get(_normalize_class(class_id))
    if table is None:
        return None
    return dict(table.get(max(1, min(level, 20)), {}))


def get_hp_gain_per_level(class_id: str, constitution_score: int = 10) -> int:
    """HP gained on level-up using fixed average hit die + Constitution modifier."""
    sides = CLASS_HIT_DICE.get(_normalize_class(class_id), 8)
    return _HP_AVERAGE_BY_DIE.get(sides, 5) + _ability_modifier(constitution_score)


def compute_max_hp_for_level(
    class_id: str,
    level: int,
    constitution_score: int = 10,
) -> int:
    """Compute canonical max HP for a single-class character at a given level."""
    normalized_class = _normalize_class(class_id)
    sides = CLASS_HIT_DICE.get(normalized_class, 8)
    level = max(0, int(level))
    if level <= 0:
        return 0

    constitution_modifier = _ability_modifier(constitution_score)
    average_per_level = _HP_AVERAGE_BY_DIE.get(sides, 5)
    extra_levels = max(0, level - 1)
    total = sides + constitution_modifier + (extra_levels * (average_per_level + constitution_modifier))
    return max(1, total)


def recompute_hit_points(data: dict, *, preserve_damage: bool = True) -> dict:
    """Recompute HP from class, level and Constitution using the canonical formula."""
    next_data = dict(data)
    current_max_hp = int(next_data.get("maxHP") or 0)
    current_hp = int(next_data.get("currentHP") or 0)
    new_max_hp = compute_max_hp_for_level(
        next_data.get("class", ""),
        int(next_data.get("level", 1) or 1),
        _get_constitution_score(next_data),
    )

    if preserve_damage:
        damage_taken = max(0, current_max_hp - current_hp)
        next_current_hp = max(0, min(new_max_hp, new_max_hp - damage_taken))
    else:
        next_current_hp = new_max_hp

    next_data["maxHP"] = new_max_hp
    next_data["currentHP"] = next_current_hp
    return next_data


def apply_level_up_stats(data: dict, new_level: int) -> dict:
    """Apply all stat changes for a level-up to *new_level*.

    Updates in-place on a shallow copy:
    - maxHP and currentHP (both gain the HP from the new level, including CON)
    - hitDiceTotal (= new_level) and hitDiceRemaining (+1, capped at total)
    - spellcasting.slots (max values from PHB table, used counts preserved)

    Non-caster classes are unaffected for the spell-slot block.
    """
    next_data = dict(data)
    class_id = _normalize_class(next_data.get("class"))

    # ── HP ────────────────────────────────────────────────────────────────────
    hp_gain = get_hp_gain_per_level(class_id, _get_constitution_score(next_data))
    current_max_hp = int(next_data.get("maxHP") or 0)
    current_hp = int(next_data.get("currentHP") or 0)
    next_data["maxHP"] = max(0, current_max_hp + hp_gain)
    next_data["currentHP"] = max(0, min(next_data["maxHP"], current_hp + hp_gain))

    # ── Hit Dice ──────────────────────────────────────────────────────────────
    old_remaining = int(next_data.get("hitDiceRemaining") or 0)
    next_data["hitDiceTotal"] = new_level
    next_data["hitDiceRemaining"] = min(old_remaining + 1, new_level)

    # ── Spell Slots ───────────────────────────────────────────────────────────
    new_slots = get_spell_slots_for_class_level(class_id, new_level)
    if new_slots is not None:
        next_data = _apply_spell_slots(next_data, new_slots)

    # ── Class Resources (druid Wild Shape, etc.) ───────────────────────────────
    if class_id == "druid":
        from app.services.wild_shape_service import init_class_resources_for_druid
        next_data = init_class_resources_for_druid(next_data, new_level)

    return next_data


# ── Internal helpers ───────────────────────────────────────────────────────────


def _normalize_class(value: object) -> str:
    normalized = str(value or "").strip().lower()
    return _CLASS_MECHANICS_FAMILIES.get(normalized, normalized)


def _get_constitution_score(data: dict) -> int:
    abilities = data.get("abilities")
    if not isinstance(abilities, dict):
        return 10
    value = abilities.get("constitution", 10)
    return int(value) if isinstance(value, int) else 10


def _ability_modifier(score: int) -> int:
    return floor((score - 10) / 2)


def _apply_spell_slots(data: dict, new_slots: dict[int, int]) -> dict:
    """Rebuild spellcasting.slots from the new max values, preserving used counts."""
    spellcasting = dict(data.get("spellcasting") or {})
    existing_slots: dict = dict(spellcasting.get("slots") or {})

    merged: dict = {}

    # Gather all slot levels that matter: both existing and new
    all_levels = set(range(1, 10))
    for key in existing_slots:
        try:
            all_levels.add(int(key))
        except (ValueError, TypeError):
            pass

    for slot_level in sorted(all_levels):
        key = str(slot_level)
        new_max = new_slots.get(slot_level, 0)
        old_slot = existing_slots.get(key)
        old_used = old_slot.get("used", 0) if isinstance(old_slot, dict) else 0

        # Only store this level if it currently has a max or had one previously.
        if new_max > 0 or old_slot is not None:
            merged[key] = {"max": new_max, "used": min(int(old_used), new_max)}

    spellcasting["slots"] = merged
    return {**data, "spellcasting": spellcasting}
