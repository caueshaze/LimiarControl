"""Out-of-combat spell casting: eligibility, effect creation, and slot spending.

Effects created here must match the canonical shape used by the combat path
(see spell_declarative_effects.py / concentration.py) so that
derive_active_concentration, the UI, and restore_persisted_effects all work
correctly.
"""

from __future__ import annotations

from datetime import datetime, timezone
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

    return True, None


# ---------------------------------------------------------------------------
# Effect building
# ---------------------------------------------------------------------------

def build_persisted_effects(
    *,
    spell,               # CampaignSpell
    caster_user_id: str,
    variant_key: str | None,
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
            "target_player_user_id": caster_user_id,
        }

        # Merge params into metadata (matches the else-branch in combat path)
        if kind == "spell_effect":
            metadata = {**metadata, **params}

        if effect_type in {"advantage_on_checks", "disadvantage_on_checks"}:
            metadata["against"] = params.get("against") or "any"

        results.append({
            "id": str(uuid4()),
            "source_participant_id": None,
            "kind": kind,
            "condition_type": None,
            "numeric_value": numeric_value,
            "duration_type": "until_long_rest",
            "remaining_rounds": None,
            "expires_on": None,
            "expires_at_participant_id": None,
            "created_at": created_at,
            "metadata": metadata,
            "display_label": spell_name if not variant_label else f"{spell_name} — {variant_label}",
        })

    return results


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


_SKIP_EFFECT_TYPES = {"grant_temp_hp"}


def _resolve_kind_and_value(effect_type: str, params: dict) -> tuple[str | None, int | None]:
    """Return (kind, numeric_value) or (None, None) to skip this effect."""
    if effect_type in _SKIP_EFFECT_TYPES:
        return None, None
    if effect_type == "modify_stat":
        stat = params.get("stat", "")
        return stat, int(params.get("value", 0))
    return "spell_effect", None
