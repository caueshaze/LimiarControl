"""D&D 5e class progression tables and level-up stat computation."""

from __future__ import annotations

from math import floor

from app.services.sorcerer_progression import DRACONIC_BLOODLINE_SUBCLASS_ID

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
# Frontend counterpart (TypeScript):
#   apps/control-web/src/entities/dnd-base/spellProgression.ts

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

# ── Cantrip progression (PHB) ─────────────────────────────────────────────────
# Frontend counterpart: apps/control-web/src/entities/dnd-base/spellProgression.ts (CANTRIPS_BY_CLASS)
_CANTRIPS_BY_CLASS: dict[str, dict[int, int]] = {
    "bard":     {1:2,2:2,3:2,4:3,5:3,6:3,7:3,8:3,9:3,10:4,11:4,12:4,13:4,14:4,15:4,16:4,17:4,18:4,19:4,20:4},
    "cleric":   {1:3,2:3,3:3,4:4,5:4,6:4,7:4,8:4,9:4,10:5,11:5,12:5,13:5,14:5,15:5,16:5,17:5,18:5,19:5,20:5},
    "druid":    {1:2,2:2,3:2,4:3,5:3,6:3,7:3,8:3,9:3,10:4,11:4,12:4,13:4,14:4,15:4,16:4,17:4,18:4,19:4,20:4},
    "sorcerer": {1:4,2:4,3:4,4:5,5:5,6:5,7:5,8:5,9:5,10:6,11:6,12:6,13:6,14:6,15:6,16:6,17:6,18:6,19:6,20:6},
    "warlock":  {1:2,2:2,3:2,4:3,5:3,6:3,7:3,8:3,9:3,10:4,11:4,12:4,13:4,14:4,15:4,16:4,17:4,18:4,19:4,20:4},
    "wizard":   {1:3,2:3,3:3,4:4,5:4,6:4,7:4,8:4,9:4,10:5,11:5,12:5,13:5,14:5,15:5,16:5,17:5,18:5,19:5,20:5},
}

# ── Leveled spells known — known-spell casters only (PHB) ─────────────────────
# Frontend counterpart: apps/control-web/src/entities/dnd-base/spellProgression.ts (LEVELED_SPELLS_KNOWN_BY_CLASS)
# Prepared casters (cleric, druid, paladin, wizard) are NOT in this table.
_LEVELED_SPELLS_KNOWN_BY_CLASS: dict[str, dict[int, int]] = {
    "bard":     {1:4,2:5,3:6,4:7,5:8,6:9,7:10,8:11,9:12,10:14,11:15,12:15,13:16,14:18,15:19,16:19,17:20,18:22,19:22,20:22},
    "ranger":   {1:0,2:2,3:3,4:3,5:4,6:4,7:5,8:5,9:6,10:6,11:7,12:7,13:8,14:8,15:9,16:9,17:10,18:10,19:11,20:11},
    "sorcerer": {1:2,2:3,3:4,4:5,5:6,6:7,7:8,8:9,9:10,10:11,11:12,12:12,13:13,14:13,15:14,16:14,17:15,18:15,19:15,20:15},
    "warlock":  {1:2,2:3,3:4,4:5,5:6,6:7,7:8,8:9,9:10,10:10,11:11,12:11,13:12,14:12,15:13,16:13,17:14,18:14,19:15,20:15},
}

# ── Spellcasting type by class ─────────────────────────────────────────────────
# "known"    — knows a fixed list of spells (bard, ranger, sorcerer, warlock)
# "prepared" — prepares from full class list using level + modifier (cleric, druid, paladin)
# "spellbook"— wizard: maintains a spellbook, prepares from it each day
_SPELLCASTING_TYPE_BY_CLASS: dict[str, str] = {
    "bard":     "known",
    "cleric":   "prepared",
    "druid":    "prepared",
    "paladin":  "prepared",
    "ranger":   "known",
    "sorcerer": "known",
    "warlock":  "known",
    "wizard":   "spellbook",
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


def get_class_spell_progression(class_id: str, level: int) -> dict | None:
    """Return pure class spell progression data for a given class and character level.

    Returns None for non-caster classes.
    Does NOT include prepared spell counts (those depend on character ability scores).

    Keys:
      className         — normalized class id
      level             — clamped character level (1–20)
      slots             — {slot_level: count}, empty dict if no slots yet
      maxSpellLevel     — highest slot level with count > 0 (0 if none)
      cantrips          — cantrip count at this level, or 0 for non-cantrip classes
      leveledSpellsKnown — spells known count for known-spell classes, None for prepared/spellbook
      spellcastingType  — "known" | "prepared" | "spellbook", or None for non-casters
    """
    normalized = _normalize_class(class_id)
    slots = get_spell_slots_for_class_level(normalized, level)
    if slots is None:
        return None

    clamped_level = max(1, min(level, 20))
    max_spell_level = max(slots.keys(), default=0)
    cantrips = _CANTRIPS_BY_CLASS.get(normalized, {}).get(clamped_level, 0)
    leveled_known_table = _LEVELED_SPELLS_KNOWN_BY_CLASS.get(normalized)
    leveled_spells_known = leveled_known_table.get(clamped_level) if leveled_known_table else None
    spellcasting_type = _SPELLCASTING_TYPE_BY_CLASS.get(normalized)

    return {
        "className": normalized,
        "level": clamped_level,
        "slots": slots,
        "maxSpellLevel": max_spell_level,
        "cantrips": cantrips,
        "leveledSpellsKnown": leveled_spells_known,
        "spellcastingType": spellcasting_type,
    }


def get_hp_gain_per_level(class_id: str, constitution_score: int = 10) -> int:
    """HP gained on level-up using fixed average hit die + Constitution modifier."""
    sides = CLASS_HIT_DICE.get(_normalize_class(class_id), 8)
    return _HP_AVERAGE_BY_DIE.get(sides, 5) + _ability_modifier(constitution_score)


def _normalize_subclass(subclass_id: object) -> str:
    return str(subclass_id or "").strip().lower()


def _draconic_resilience_bonus_for_level(
    class_id: str,
    level: int,
    *,
    subclass_id: object = None,
) -> int:
    normalized_class = _normalize_class(class_id)
    normalized_subclass = _normalize_subclass(subclass_id)
    if normalized_class != "sorcerer" or normalized_subclass != DRACONIC_BLOODLINE_SUBCLASS_ID:
        return 0
    return max(0, int(level))


def _build_max_hp_breakdown(
    *,
    class_id: str,
    level: int,
    constitution_score: int,
    subclass_id: object = None,
) -> dict[str, int]:
    normalized_class = _normalize_class(class_id)
    sides = CLASS_HIT_DICE.get(normalized_class, 8)
    clamped_level = max(0, int(level))
    if clamped_level <= 0:
        return {
            "baseClassHp": 0,
            "constitutionBonus": 0,
            "draconicResilienceBonus": 0,
            "total": 0,
        }

    constitution_modifier = _ability_modifier(constitution_score)
    base_class_hp = sides + (max(0, clamped_level - 1) * _HP_AVERAGE_BY_DIE.get(sides, 5))
    constitution_bonus = clamped_level * constitution_modifier
    draconic_resilience_bonus = _draconic_resilience_bonus_for_level(
        normalized_class,
        clamped_level,
        subclass_id=subclass_id,
    )
    return {
        "baseClassHp": base_class_hp,
        "constitutionBonus": constitution_bonus,
        "draconicResilienceBonus": draconic_resilience_bonus,
        "total": max(1, base_class_hp + constitution_bonus + draconic_resilience_bonus),
    }


def compute_max_hp_for_level(
    class_id: str,
    level: int,
    constitution_score: int = 10,
    *,
    subclass_id: object = None,
) -> int:
    """Compute canonical max HP for a single-class character at a given level."""
    breakdown = _build_max_hp_breakdown(
        class_id=class_id,
        level=level,
        constitution_score=constitution_score,
        subclass_id=subclass_id,
    )
    return breakdown["total"]


def recompute_hit_points(data: dict, *, preserve_damage: bool = True) -> dict:
    """Recompute HP from class, level and Constitution using the canonical formula."""
    next_data = dict(data)
    current_max_hp = int(next_data.get("maxHP") or 0)
    current_hp = int(next_data.get("currentHP") or 0)
    class_id = next_data.get("class", "")
    level = int(next_data.get("level", 1) or 1)
    constitution_score = _get_constitution_score(next_data)
    subclass_id = next_data.get("subclass")
    new_max_hp = compute_max_hp_for_level(
        class_id,
        level,
        constitution_score,
        subclass_id=subclass_id,
    )

    if preserve_damage:
        damage_taken = max(0, current_max_hp - current_hp)
        next_current_hp = max(0, min(new_max_hp, new_max_hp - damage_taken))
    else:
        next_current_hp = new_max_hp

    next_data["maxHP"] = new_max_hp
    next_data["currentHP"] = next_current_hp
    next_data["maxHpBreakdown"] = _build_max_hp_breakdown(
        class_id=class_id,
        level=level,
        constitution_score=constitution_score,
        subclass_id=subclass_id,
    )
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
    hp_gain += _draconic_resilience_bonus_for_level(
        class_id,
        1,
        subclass_id=next_data.get("subclass"),
    )
    current_max_hp = int(next_data.get("maxHP") or 0)
    current_hp = int(next_data.get("currentHP") or 0)
    next_data["maxHP"] = max(0, current_max_hp + hp_gain)
    next_data["currentHP"] = max(0, min(next_data["maxHP"], current_hp + hp_gain))
    next_data["maxHpBreakdown"] = _build_max_hp_breakdown(
        class_id=class_id,
        level=new_level,
        constitution_score=_get_constitution_score(next_data),
        subclass_id=next_data.get("subclass"),
    )

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
