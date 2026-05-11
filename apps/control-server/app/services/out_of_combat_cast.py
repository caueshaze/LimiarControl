"""Out-of-combat spell casting: eligibility, effect creation, and slot spending.

Effects created here must match the canonical shape used by the combat path
(see spell_declarative_effects.py / concentration.py) so that
derive_active_concentration, the UI, and restore_persisted_effects all work
correctly.
"""

from __future__ import annotations

import random
from datetime import datetime, timezone
from math import floor
from uuid import uuid4


# ---------------------------------------------------------------------------
# Eligibility
# ---------------------------------------------------------------------------

def check_out_of_combat_cast_eligibility(
    *,
    spell,                # CampaignSpell
    state_json: dict,
    slot_level: int | None,
    variant_key: str | None,
    out_of_combat_target: str | None = None,
    target_user_id: str | None = None,
    caster_user_id: str | None = None,
    target_state_json: dict | None = None,
) -> tuple[bool, str | None]:
    """Return (ok, rejection_reason).  ok=True means the cast may proceed."""
    if not spell.out_of_combat_castable:
        return False, "Spell is not castable outside combat"

    if _spell_requires_variant(spell):
        if not variant_key:
            return False, "variantKey is required for this spell"
        if not _get_variant(spell, variant_key):
            return False, f"Unknown variant key: {variant_key!r}"

    if not _has_resolvable_effects(spell, variant_key):
        return False, "Spell has no supported declarative effects"

    if spell.level > 0:
        if slot_level is None or slot_level < spell.level:
            return False, f"slotLevel must be >= {spell.level}"
        slot = (
            (state_json.get("spellcasting") or {})
            .get("slots", {})
            .get(str(slot_level), {})
        )
        if slot.get("used", 0) >= slot.get("max", 0):
            return False, f"No spell slot of level {slot_level} remaining"

    if (
        out_of_combat_target == "self"
        and target_user_id is not None
        and caster_user_id is not None
        and target_user_id != caster_user_id
    ):
        return False, "This spell can only target yourself"

    effective_target_state = target_state_json if target_state_json is not None else state_json
    effects = _resolve_effects(spell, variant_key)
    rejection = _check_requires_unarmored_eligibility(effects, effective_target_state)
    if rejection:
        return False, rejection

    return True, None


# ---------------------------------------------------------------------------
# Effect building
# ---------------------------------------------------------------------------

def build_persisted_effects(
    *,
    spell,               # CampaignSpell
    caster_user_id: str,
    target_user_id: str,
    variant_key: str | None,
    game_time_seconds: int,
) -> list[dict]:
    """Build the list of persisted effect dicts for an out-of-combat cast.

    The shape mirrors _build_active_effect() in concentration.py and the
    metadata built in _apply_single_declarative_effect() so that all
    existing helpers (derive_active_concentration, remove_persisted_effect,
    clear_persisted_concentration_effects, restore_persisted_effects) work
    without modification.
    """
    raw_effects = _resolve_effects(spell, variant_key)
    if not raw_effects:
        return []

    group_id = str(uuid4())
    variant = _get_variant(spell, variant_key) if variant_key else None
    variant_label = (variant.get("labelPt") or variant.get("labelEn")) if variant else None
    spell_name = spell.name_pt or spell.name_en
    created_at = datetime.now(timezone.utc).isoformat()

    results: list[dict] = []
    for raw_effect in raw_effects:
        effect_type = raw_effect.get("type", "")
        params = raw_effect.get("params") or {}

        kind, numeric_value = _resolve_kind_and_value(effect_type, params)
        if kind is None:
            # grant_temp_hp and other non-persistable types are skipped in v1
            continue

        metadata: dict = {
            "declarative_effect_group_id": group_id,
            "declarative_effect": raw_effect,
            "declarative_on_end_effects": [],
            "source_spell_key": spell.canonical_key,
            "source_spell_name": spell_name,
            "selected_variant_key": variant_key,
            "selected_variant_label": variant_label,
            "context_origin": "out_of_combat_cast",
            "concentration": bool(spell.concentration),
            "concentration_group": group_id if spell.concentration else None,
            "caster_player_user_id": caster_user_id,
            "target_player_user_id": target_user_id,
        }

        # Merge params into metadata (matches the else-branch in combat path)
        if kind == "spell_effect":
            metadata = {**metadata, **params}

        if effect_type in {"advantage_on_checks", "disadvantage_on_checks"}:
            metadata["against"] = params.get("against") or "any"

        ooc_duration = raw_effect.get("out_of_combat_duration")
        is_timed = (
            isinstance(ooc_duration, dict)
            and ooc_duration.get("type") == "timed"
            and isinstance(ooc_duration.get("seconds"), int)
            and ooc_duration.get("seconds") > 0
        )
        duration_type = "timed" if is_timed else "until_long_rest"
        created_at_game_time_seconds = game_time_seconds if is_timed else None
        expires_at_game_time_seconds = (
            game_time_seconds + ooc_duration["seconds"] if is_timed else None
        )

        results.append({
            "id": str(uuid4()),
            "source_participant_id": None,
            "kind": kind,
            "condition_type": None,
            "numeric_value": numeric_value,
            "duration_type": duration_type,
            "remaining_rounds": None,
            "expires_on": None,
            "expires_at_participant_id": None,
            "created_at_game_time_seconds": created_at_game_time_seconds,
            "expires_at_game_time_seconds": expires_at_game_time_seconds,
            "created_at": created_at,
            "metadata": metadata,
            "display_label": spell_name if not variant_label else f"{spell_name} — {variant_label}",
        })

    return results


def build_concentration_marker(
    *,
    spell,               # CampaignSpell
    caster_user_id: str,
    target_user_id: str,
    concentration_group: str,
    variant_key: str | None,
    duration_type: str = "until_long_rest",
    created_at_game_time_seconds: int | None = None,
    expires_at_game_time_seconds: int | None = None,
) -> dict:
    """Lightweight concentration marker placed on the CASTER state when targeting an ally.

    Has no ``metadata.declarative_effect`` so it never applies gameplay bonuses
    to the caster. ``derive_active_concentration`` reads it to show the caster
    their active concentration spell in the UI.
    """
    variant = _get_variant(spell, variant_key) if variant_key else None
    variant_label = (variant.get("labelPt") or variant.get("labelEn")) if variant else None
    spell_name = spell.name_pt or spell.name_en
    display_label = spell_name if not variant_label else f"{spell_name} — {variant_label}"

    return {
        "id": str(uuid4()),
        "source_participant_id": None,
        "kind": "spell_effect",
        "condition_type": None,
        "numeric_value": None,
        "duration_type": duration_type,
        "remaining_rounds": None,
        "expires_on": None,
        "expires_at_participant_id": None,
        "created_at_game_time_seconds": created_at_game_time_seconds,
        "expires_at_game_time_seconds": expires_at_game_time_seconds,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "metadata": {
            "concentration": True,
            "concentration_marker": True,
            "concentration_group": concentration_group,
            "source_spell_key": spell.canonical_key,
            "source_spell_name": spell_name,
            "selected_variant_key": variant_key,
            "selected_variant_label": variant_label,
            "context_origin": "out_of_combat_cast",
            "caster_player_user_id": caster_user_id,
            "target_player_user_id": target_user_id,
        },
        "display_label": display_label,
    }


# ---------------------------------------------------------------------------
# Slot spending
# ---------------------------------------------------------------------------

def consume_spell_slot(state_json: dict, slot_level: int) -> dict:
    """Return updated state_json with the slot decremented.

    Raises ValueError if the slot is not available.
    """
    data = dict(state_json)
    spellcasting = dict(data.get("spellcasting") or {})
    slots = dict(spellcasting.get("slots") or {})
    lvl_key = str(slot_level)
    slot_data = dict(slots.get(lvl_key) or {"used": 0, "max": 0})

    if slot_data.get("used", 0) >= slot_data.get("max", 0):
        raise ValueError(f"No spell slot of level {slot_level} remaining")

    slot_data["used"] = int(slot_data.get("used", 0)) + 1
    slots[lvl_key] = slot_data
    spellcasting["slots"] = slots
    data["spellcasting"] = spellcasting
    return data


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _spell_requires_variant(spell) -> bool:
    variants = spell.variants_json or []
    return any(v.get("effects") for v in variants)


def _get_variant(spell, variant_key: str) -> dict | None:
    for v in (spell.variants_json or []):
        if v.get("key") == variant_key:
            return v
    return None


def _resolve_effects(spell, variant_key: str | None) -> list[dict]:
    if variant_key:
        variant = _get_variant(spell, variant_key)
        if variant and variant.get("effects"):
            return variant["effects"]
    return spell.effects_json or []


def _has_resolvable_effects(spell, variant_key: str | None) -> bool:
    return bool(_resolve_effects(spell, variant_key))


def has_castable_effects(spell) -> bool:
    """True if the spell has any supported declarative effects (direct or via variants).

    Used by the eligible-list endpoint to exclude spells that would always be
    rejected at cast time due to having no persistable effects.
    """
    if spell.effects_json:
        return True
    variants = spell.variants_json or []
    return any(v.get("effects") for v in variants)


_SKIP_EFFECT_TYPES = {"grant_temp_hp", "create_consumable", "heal"}


def collect_create_consumable_effects(
    spell,
    variant_key: str | None,
) -> list[dict]:
    """Return only create_consumable effect dicts from the spell's effective effects list."""
    return [
        e for e in _resolve_effects(spell, variant_key)
        if isinstance(e, dict) and e.get("type") == "create_consumable"
    ]


def collect_heal_effects(
    spell,
    variant_key: str | None,
) -> list[dict]:
    """Return only heal effect dicts from the spell's effective effects list."""
    return [
        e for e in _resolve_effects(spell, variant_key)
        if isinstance(e, dict) and e.get("type") == "heal"
    ]


def compute_heal_dice_with_upcast(
    base_dice: str,
    spell,
    slot_level: int | None,
) -> str:
    """Scale base heal dice by upcast level using the spell's upcast_json config."""
    effective_slot = slot_level if isinstance(slot_level, int) else getattr(spell, "level", 1)
    spell_level = getattr(spell, "level", 1) or 1
    upcast = getattr(spell, "upcast_json", None) or {}
    mode = upcast.get("mode", "")
    per_level = int(upcast.get("perLevel", 0)) if isinstance(upcast.get("perLevel"), (int, float)) else 0

    if mode == "extra_heal_dice" and per_level > 0 and effective_slot > spell_level:
        extra_levels = effective_slot - spell_level
        extra_dice = extra_levels * per_level
        if "d" in base_dice:
            count_str, sides_str = base_dice.split("d", 1)
            try:
                total = int(count_str) + extra_dice
                return f"{total}d{sides_str}"
            except ValueError:
                pass
    return base_dice


def resolve_spellcasting_modifier(state_json: dict) -> int:
    """Return the caster's spellcasting ability modifier from state_json."""
    spellcasting = (state_json or {}).get("spellcasting") or {}
    precomputed = spellcasting.get("modifier")
    if isinstance(precomputed, int):
        return precomputed
    ability = spellcasting.get("ability")
    if isinstance(ability, str):
        abilities = (state_json or {}).get("abilities") or {}
        score = abilities.get(ability, 10)
        if isinstance(score, (int, float)):
            return floor((int(score) - 10) / 2)
    return 0


def roll_spell_heal_effects(
    heal_effects: list[dict],
    spell,
    slot_level: int | None,
    caster_state_json: dict,
) -> list[dict]:
    """Roll healing for each heal effect.

    Returns a list of dicts with keys: amount, target, effective_dice, rolls, modifier.
    """
    from app.services.healing_consumables_types import _parse_heal_dice

    results = []
    for he in heal_effects:
        params = he.get("params") or {}
        base_dice = params.get("dice") or ""
        effective_dice = compute_heal_dice_with_upcast(base_dice, spell, slot_level)
        spell_mod = (
            resolve_spellcasting_modifier(caster_state_json)
            if params.get("ability_modifier") == "spellcasting"
            else 0
        )
        count, sides, expr_mod = _parse_heal_dice(effective_dice)
        rolls = (
            [random.randint(1, sides) for _ in range(count)]
            if count > 0 and sides > 0
            else []
        )
        healing_amount = max(0, sum(rolls) + expr_mod + spell_mod)
        results.append({
            "amount": healing_amount,
            "target": he.get("target", "selected_target"),
            "effective_dice": effective_dice,
            "rolls": rolls,
            "modifier": spell_mod,
        })
    return results


def _resolve_kind_and_value(effect_type: str, params: dict) -> tuple[str | None, int | None]:
    """Return (kind, numeric_value) or (None, None) to skip this effect."""
    if effect_type in _SKIP_EFFECT_TYPES:
        return None, None
    if effect_type == "modify_stat":
        stat = params.get("stat", "")
        return stat, int(params.get("value", 0))
    return "spell_effect", None


_ARMOR_TYPES = {"light", "medium", "heavy"}


def _target_has_armor(target_state_json: dict) -> bool:
    armor = target_state_json.get("equippedArmor") or {}
    if not isinstance(armor, dict):
        return False
    armor_type = (armor.get("armorType") or "").strip().lower()
    return armor_type in _ARMOR_TYPES


def _check_requires_unarmored_eligibility(
    effects: list[dict],
    target_state_json: dict,
) -> str | None:
    """Return an error string if any effect requires unarmored and target has armor, else None."""
    for effect in effects:
        if not isinstance(effect, dict):
            continue
        params = effect.get("params") or {}
        if params.get("requires_unarmored") is True and _target_has_armor(target_state_json):
            return "Target is wearing armor and this spell requires an unarmored target"
    return None
