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
from typing import Callable
from uuid import uuid4
from app.services.spell_effect_factories import (
    SpellEffectBuildContext,
    build_barkskin_effect,
    build_blur_effect,
    build_jump_effect,
    build_protection_from_evil_and_good_effect,
    build_sanctuary_effect,
    build_shillelagh_effect,
    build_spider_climb_effect,
    build_warding_bond_effects,
)
from app.services.canonical_keys import normalize_canonical_key
from app.services.spell_keys import normalize_spell_key

OOC_NARRATIVE_UTILITY_SPELLS = {
    "detect_magic",
    "detect_poison_disease",
    "detect_evil_and_good",
    "druidcraft",
    "produce_flame",
    "thaumaturgy",
    "comprehend_languages",
    "purify_food_and_drink",
    "spare_the_dying",
}

OOC_FACTORY_EFFECT_SPELLS = {
    "jump",
    "spider_climb",
    "barkskin",
    "blur",
    "protection_from_evil_and_good",
    "sanctuary",
}

OOC_REMOVAL_UTILITY_SPELLS = {
    "lesser_restoration",
}

OOC_SPECIAL_INPUT_SPELLS = {
    "shillelagh",
}

# Warding Bond persists two linked effects across two creatures, so it does not
# fit the single-effect factory dispatch. It is handled by a dedicated route
# block; this set only exists so eligibility/listing treat it as castable.
OOC_LINKED_EFFECT_SPELLS = frozenset({"warding_bond"})

_THAUMATURGY_ALLOWED_EFFECTS = [
    "alter_eyes",
    "booming_voice",
    "flame_omen",
    "harmless_tremor",
    "instantaneous_sound",
    "open_or_close_unlocked_door",
]


_OOCFactory = Callable[[SpellEffectBuildContext], dict]
_OOC_PERSISTED_FACTORY_REGISTRY: dict[str, tuple[_OOCFactory, int, bool]] = {
    "barkskin": (build_barkskin_effect, 3600, True),
    "blur": (build_blur_effect, 60, True),
    "protection_from_evil_and_good": (build_protection_from_evil_and_good_effect, 600, True),
    "jump": (build_jump_effect, 60, False),
    "sanctuary": (build_sanctuary_effect, 60, False),
    "spider_climb": (build_spider_climb_effect, 3600, True),
}


def _is_ooc_utility_spell(canonical_key: str) -> bool:
    return (
        canonical_key in OOC_NARRATIVE_UTILITY_SPELLS
        or canonical_key in OOC_FACTORY_EFFECT_SPELLS
        or canonical_key in OOC_REMOVAL_UTILITY_SPELLS
        or canonical_key in OOC_SPECIAL_INPUT_SPELLS
        or canonical_key in OOC_LINKED_EFFECT_SPELLS
    )


def build_ooc_warding_bond_effects(
    *,
    spell,
    caster_user_id: str,
    target_user_id: str,
    game_time_seconds: int,
) -> tuple[dict, dict]:
    """Build the (target_effect, caster_marker) pair for an OOC Warding Bond cast.

    Bonds are keyed by ref_id; a player's ref_id is their user id, so the user
    ids are stored directly and the bond resolves once combat restores both
    effects. The target effect is placed on the target's state, the caster
    marker on the caster's state.
    """
    duration_seconds = _resolve_ooc_factory_duration_seconds(spell, 3600)
    bond_group = str(uuid4())
    target_effect, caster_effect = build_warding_bond_effects(
        SpellEffectBuildContext(
            spell_key="warding_bond",
            spell_name=spell.name_pt or spell.name_en,
            game_time_seconds=game_time_seconds,
            duration_seconds=duration_seconds,
            concentration=False,
            concentration_group=None,
            source_participant_id=None,
            owner_participant_id=target_user_id,
            created_by_participant_id=caster_user_id,
            context_origin="out_of_combat_cast",
            caster_user_id=caster_user_id,
            target_user_id=target_user_id,
            created_out_of_combat=True,
            extra_metadata={
                "bond_group": bond_group,
                "bond_caster_participant_id": caster_user_id,
                "bond_target_participant_id": target_user_id,
                "bond_caster_player_user_id": caster_user_id,
                "bond_target_player_user_id": target_user_id,
            },
        )
    )
    # The caster marker must be restored onto the CASTER, so its persisted
    # routing key points at the caster rather than the target.
    caster_effect["metadata"]["target_player_user_id"] = caster_user_id
    caster_effect["metadata"]["owner_participant_id"] = caster_user_id
    return target_effect, caster_effect


def _resolve_ooc_factory_duration_seconds(spell, fallback_seconds: int) -> int:
    duration_seconds = getattr(spell, "duration_seconds", None)
    if isinstance(duration_seconds, int) and duration_seconds > 0:
        return duration_seconds
    return fallback_seconds


def _build_ooc_factory_context(
    *,
    spell,
    spell_key: str,
    caster_user_id: str,
    target_user_id: str,
    game_time_seconds: int,
    duration_seconds: int,
    concentration: bool,
    concentration_group: str | None,
    spell_save_dc: int | None = None,
) -> SpellEffectBuildContext:
    spell_name = spell.name_pt or spell.name_en
    return SpellEffectBuildContext(
        spell_key=spell_key,
        spell_name=spell_name,
        game_time_seconds=game_time_seconds,
        duration_seconds=duration_seconds,
        concentration=concentration,
        concentration_group=concentration_group,
        source_participant_id=None,
        owner_participant_id=target_user_id,
        created_by_participant_id=caster_user_id,
        context_origin="out_of_combat_cast",
        caster_user_id=caster_user_id,
        target_user_id=target_user_id,
        created_out_of_combat=True,
        spell_save_dc=spell_save_dc,
    )


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
    weapon_item_id: str | None = None,
    weapon_canonical_key: str | None = None,
    weapon_name: str | None = None,
    spell_save_dc: int | None = None,
) -> list[dict]:
    """Build the list of persisted effect dicts for an out-of-combat cast.

    The shape mirrors _build_active_effect() in concentration.py and the
    metadata built in _apply_single_declarative_effect() so that all
    existing helpers (derive_active_concentration, remove_persisted_effect,
    clear_persisted_concentration_effects, restore_persisted_effects) work
    without modification.
    """
    raw_effects = _resolve_effects(spell, variant_key)
    canonical_key = normalize_spell_key(getattr(spell, "canonical_key", ""))
    if not raw_effects:
        if canonical_key == "purify_food_and_drink":
            return []
        if canonical_key == "spare_the_dying":
            return []
        if canonical_key == "detect_magic":
            spell_name = spell.name_pt or spell.name_en
            group_id = str(uuid4()) if spell.concentration else None
            return [{
                "id": str(uuid4()),
                "source_participant_id": None,
                "kind": "spell_effect",
                "condition_type": None,
                "numeric_value": None,
                "duration_type": "timed",
                "remaining_rounds": None,
                "expires_on": None,
                "expires_at_participant_id": None,
                "created_at_game_time_seconds": game_time_seconds,
                "expires_at_game_time_seconds": game_time_seconds + 600,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "metadata": {
                    "source_spell_key": "detect_magic",
                    "source_spell_name": spell_name,
                    "selected_variant_key": None,
                    "selected_variant_label": None,
                    "context_origin": "out_of_combat_cast",
                    "concentration": bool(spell.concentration),
                    "concentration_group": group_id,
                    "caster_player_user_id": caster_user_id,
                    "target_player_user_id": target_user_id,
                    "owner_participant_id": caster_user_id,
                    "created_by_participant_id": caster_user_id,
                    "mechanical": False,
                    "narrative": True,
                    "visible_to_all": True,
                    "utility": "detect_magic",
                    "radius_meters": 9,
                    "can_reveal_aura_with_action": True,
                    "reveals_magic_school": True,
                    "blocked_by": {
                        "stone_cm": 30,
                        "common_metal_cm": 2.5,
                        "lead_sheet": True,
                        "wood_or_earth_meters": 1,
                    },
                },
                "display_label": spell_name,
            }]
        if canonical_key == "detect_poison_disease":
            spell_name = spell.name_pt or spell.name_en
            group_id = str(uuid4()) if spell.concentration else None
            return [{
                "id": str(uuid4()),
                "source_participant_id": None,
                "kind": "spell_effect",
                "condition_type": None,
                "numeric_value": None,
                "duration_type": "timed",
                "remaining_rounds": None,
                "expires_on": None,
                "expires_at_participant_id": None,
                "created_at_game_time_seconds": game_time_seconds,
                "expires_at_game_time_seconds": game_time_seconds + 600,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "metadata": {
                    "source_spell_key": "detect_poison_disease",
                    "source_spell_name": spell_name,
                    "selected_variant_key": None,
                    "selected_variant_label": None,
                    "context_origin": "out_of_combat_cast",
                    "concentration": bool(spell.concentration),
                    "concentration_group": group_id,
                    "caster_player_user_id": caster_user_id,
                    "target_player_user_id": target_user_id,
                    "owner_participant_id": caster_user_id,
                    "created_by_participant_id": caster_user_id,
                    "mechanical": False,
                    "narrative": True,
                    "visible_to_all": True,
                    "utility": "detect_poison_disease",
                    "radius_meters": 9,
                    "detects_poisons": True,
                    "detects_poisonous_creatures": True,
                    "detects_diseases": True,
                    "can_identify_poison_or_disease_with_action": True,
                    "blocked_by": {
                        "stone_cm": 30,
                        "common_metal_cm": 2.5,
                        "lead_sheet": True,
                        "wood_or_earth_meters": 1,
                    },
                },
                "display_label": spell_name,
            }]
        if canonical_key == "detect_evil_and_good":
            spell_name = spell.name_pt or spell.name_en
            group_id = str(uuid4()) if spell.concentration else None
            return [{
                "id": str(uuid4()),
                "source_participant_id": None,
                "kind": "spell_effect",
                "condition_type": None,
                "numeric_value": None,
                "duration_type": "timed",
                "remaining_rounds": None,
                "expires_on": None,
                "expires_at_participant_id": None,
                "created_at_game_time_seconds": game_time_seconds,
                "expires_at_game_time_seconds": game_time_seconds + 600,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "metadata": {
                    "source_spell_key": "detect_evil_and_good",
                    "source_spell_name": spell_name,
                    "selected_variant_key": None,
                    "selected_variant_label": None,
                    "context_origin": "out_of_combat_cast",
                    "concentration": bool(spell.concentration),
                    "concentration_group": group_id,
                    "caster_player_user_id": caster_user_id,
                    "target_player_user_id": target_user_id,
                    "owner_participant_id": caster_user_id,
                    "created_by_participant_id": caster_user_id,
                    "mechanical": False,
                    "narrative": True,
                    "visible_to_all": True,
                    "utility": "detect_evil_and_good",
                    "radius_meters": 9,
                    "detects_creature_types": [
                        "aberration", "celestial", "elemental",
                        "fey", "fiend", "undead",
                    ],
                    "detects_consecrated_or_desecrated": True,
                    "blocked_by": {
                        "stone_cm": 30,
                        "common_metal_cm": 2.5,
                        "lead_sheet": True,
                        "wood_or_earth_meters": 1,
                    },
                },
                "display_label": spell_name,
            }]
        if canonical_key == "produce_flame":
            spell_name = spell.name_pt or spell.name_en
            damage_dice = getattr(spell, "damage_dice", None) or "1d8"
            return [{
                "id": str(uuid4()),
                "source_participant_id": None,
                "kind": "spell_effect",
                "condition_type": None,
                "numeric_value": None,
                "duration_type": "timed",
                "remaining_rounds": None,
                "expires_on": None,
                "expires_at_participant_id": None,
                "created_at_game_time_seconds": game_time_seconds,
                "expires_at_game_time_seconds": game_time_seconds + 600,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "metadata": {
                    "source_spell_key": "produce_flame",
                    "source_spell_name": spell_name,
                    "selected_variant_key": None,
                    "selected_variant_label": None,
                    "context_origin": "out_of_combat_cast",
                    "concentration": False,
                    "caster_player_user_id": caster_user_id,
                    "target_player_user_id": target_user_id,
                    "owner_participant_id": caster_user_id,
                    "created_by_participant_id": caster_user_id,
                    "mechanical": True,
                    "narrative": True,
                    "visual": True,
                    "visible_to_all": True,
                    "utility": "produce_flame",
                    "creates_light": True,
                    "bright_light_meters": 3,
                    "dim_light_meters": 3,
                    "can_throw": True,
                    "throw_range_meters": 9,
                    "throw_attack_type": "ranged_spell",
                    "damage_dice": damage_dice,
                    "damage_type": "Fire",
                    "resolved_at_character_level": None,
                },
                "display_label": spell_name,
            }]
        if canonical_key == "druidcraft":
            spell_name = spell.name_pt or spell.name_en
            return [{
                "id": str(uuid4()),
                "source_participant_id": None,
                "kind": "spell_effect",
                "condition_type": None,
                "numeric_value": None,
                "duration_type": "timed",
                "remaining_rounds": None,
                "expires_on": None,
                "expires_at_participant_id": None,
                "created_at_game_time_seconds": game_time_seconds,
                "expires_at_game_time_seconds": game_time_seconds + 3600,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "metadata": {
                    "source_spell_key": "druidcraft",
                    "source_spell_name": spell_name,
                    "selected_variant_key": None,
                    "selected_variant_label": None,
                    "context_origin": "out_of_combat_cast",
                    "concentration": False,
                    "caster_player_user_id": caster_user_id,
                    "target_player_user_id": target_user_id,
                    "owner_participant_id": caster_user_id,
                    "created_by_participant_id": caster_user_id,
                    "mechanical": False,
                    "narrative": True,
                    "visible_to_all": True,
                    "utility": "druidcraft",
                    "spell_level": 0,
                    "allowed_effects": [
                        "weather_prediction",
                        "minor_natural_sensory_effect",
                        "plant_bloom",
                        "harmless_natural_effect",
                        "ignite_or_extinguish_small_flame",
                    ],
                },
                "display_label": spell_name,
            }]
        if canonical_key == "thaumaturgy":
            spell_name = spell.name_pt or spell.name_en
            return [{
                "id": str(uuid4()),
                "source_participant_id": None,
                "kind": "spell_effect",
                "condition_type": None,
                "numeric_value": None,
                "duration_type": "timed",
                "remaining_rounds": None,
                "expires_on": None,
                "expires_at_participant_id": None,
                "created_at_game_time_seconds": game_time_seconds,
                "expires_at_game_time_seconds": game_time_seconds + 60,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "metadata": {
                    "source_spell_key": "thaumaturgy",
                    "source_spell_name": spell_name,
                    "selected_variant_key": None,
                    "context_origin": "out_of_combat_cast",
                    "concentration": False,
                    "caster_player_user_id": caster_user_id,
                    "target_player_user_id": target_user_id,
                    "owner_participant_id": caster_user_id,
                    "created_by_participant_id": caster_user_id,
                    "mechanical": False,
                    "narrative": True,
                    "visible_to_all": True,
                    "utility": "thaumaturgy",
                    "spell_level": 0,
                    "allowed_effects": _THAUMATURGY_ALLOWED_EFFECTS,
                },
                "display_label": spell_name,
            }]
        if canonical_key == "comprehend_languages":
            spell_name = spell.name_pt or spell.name_en
            return [{
                "id": str(uuid4()),
                "source_participant_id": None,
                "kind": "spell_effect",
                "condition_type": None,
                "numeric_value": None,
                "duration_type": "timed",
                "remaining_rounds": None,
                "expires_on": None,
                "expires_at_participant_id": None,
                "created_at_game_time_seconds": game_time_seconds,
                "expires_at_game_time_seconds": game_time_seconds + 3600,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "metadata": {
                    "source_spell_key": "comprehend_languages",
                    "source_spell_name": spell_name,
                    "context_origin": "out_of_combat_cast",
                    "concentration": False,
                    "caster_player_user_id": caster_user_id,
                    "target_player_user_id": target_user_id,
                    "owner_participant_id": caster_user_id,
                    "created_by_participant_id": caster_user_id,
                    "mechanical": False,
                    "narrative": True,
                    "visible_to_all": True,
                    "utility": "comprehend_languages",
                    "spell_level": 1,
                    "duration_seconds": 3600,
                    "understands_spoken_languages": True,
                    "understands_written_languages": True,
                    "requires_touch_for_written_text": True,
                    "literal_meaning_only": True,
                    "deciphers_secret_messages": False,
                },
                "display_label": spell_name,
            }]
        if canonical_key == "shillelagh":
            # Intentionally outside generic dispatch: requires validated weapon input context.
            if (
                not isinstance(weapon_item_id, str)
                or not weapon_item_id.strip()
                or not isinstance(weapon_canonical_key, str)
                or not weapon_canonical_key.strip()
            ):
                return []
            normalized_weapon_key = normalize_canonical_key(weapon_canonical_key)
            spell_name = spell.name_pt or spell.name_en
            return [
                build_shillelagh_effect(
                    SpellEffectBuildContext(
                        spell_key="shillelagh",
                        spell_name=spell_name,
                        game_time_seconds=game_time_seconds,
                        duration_seconds=60,
                        concentration=False,
                        concentration_group=None,
                        source_participant_id=None,
                        owner_participant_id=caster_user_id,
                        created_by_participant_id=caster_user_id,
                        context_origin="out_of_combat_cast",
                        caster_user_id=caster_user_id,
                        target_user_id=target_user_id,
                        created_out_of_combat=True,
                        extra_metadata={
                            "weapon_item_id": weapon_item_id.strip(),
                            "weapon_key": normalized_weapon_key,
                            "weapon_canonical_key": normalized_weapon_key,
                            "weapon_name": weapon_name,
                        },
                    )
                )
            ]
        factory_entry = _OOC_PERSISTED_FACTORY_REGISTRY.get(canonical_key)
        if factory_entry:
            factory, duration_fallback_seconds, concentration_required = factory_entry
            if canonical_key == "sanctuary":
                if not isinstance(spell_save_dc, int) or spell_save_dc <= 0:
                    raise ValueError(
                        "Santuário requer uma CD de conjuração válida "
                        "(verifique o estado de magia do conjurador)."
                    )
            duration_seconds = _resolve_ooc_factory_duration_seconds(
                spell, duration_fallback_seconds
            )
            concentration_group = (
                str(uuid4()) if concentration_required and bool(spell.concentration) else None
            )
            return [
                factory(
                    _build_ooc_factory_context(
                        spell=spell,
                        spell_key=canonical_key,
                        caster_user_id=caster_user_id,
                        target_user_id=target_user_id,
                        game_time_seconds=game_time_seconds,
                        duration_seconds=duration_seconds,
                        concentration=concentration_required,
                        concentration_group=concentration_group,
                        spell_save_dc=spell_save_dc,
                    )
                )
            ]
        # Removal-only utilities (e.g., lesser_restoration) do not create
        # persisted spell effects in OOC flow.
        if canonical_key in OOC_REMOVAL_UTILITY_SPELLS:
            return []
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
        raw_seconds = ooc_duration.get("seconds") if isinstance(ooc_duration, dict) else None
        is_timed = (
            isinstance(ooc_duration, dict)
            and ooc_duration.get("type") == "timed"
            and isinstance(raw_seconds, int)
            and raw_seconds > 0
        )
        ooc_seconds = raw_seconds if isinstance(raw_seconds, int) else 0
        duration_type = "timed" if is_timed else "until_long_rest"
        created_at_game_time_seconds = game_time_seconds if is_timed else None
        expires_at_game_time_seconds = (
            game_time_seconds + ooc_seconds if is_timed else None
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
    canonical_key = normalize_spell_key(getattr(spell, "canonical_key", ""))
    if _is_ooc_utility_spell(canonical_key):
        return True
    return bool(_resolve_effects(spell, variant_key))


def has_castable_effects(spell) -> bool:
    """True if the spell has any supported declarative effects (direct or via variants).

    Used by the eligible-list endpoint to exclude spells that would always be
    rejected at cast time due to having no persistable effects.
    """
    canonical_key = normalize_spell_key(getattr(spell, "canonical_key", ""))
    if _is_ooc_utility_spell(canonical_key):
        return True
    if spell.effects_json:
        return True
    variants = spell.variants_json or []
    return any(v.get("effects") for v in variants)


_SKIP_EFFECT_TYPES = {"grant_temp_hp", "create_consumable", "heal"}


def build_healing_preview(
    spell,
    caster_state_json: dict,
) -> dict | None:
    """Return a structured healing preview for spells with heal effects, or None.

    The dict contains enough data for the frontend to compute the upcast formula
    without re-implementing the upcast algorithm.
    """
    heal_effects = collect_heal_effects(spell, None)
    if not heal_effects:
        return None

    params = (heal_effects[0].get("params") or {})
    base_dice: str = params.get("dice") or ""
    modifier = (
        resolve_spellcasting_modifier(caster_state_json)
        if params.get("ability_modifier") == "spellcasting"
        else 0
    )

    base_count = 1
    die_sides = 8
    if "d" in base_dice:
        parts = base_dice.split("d", 1)
        try:
            base_count = int(parts[0])
            die_sides = int(parts[1])
        except (ValueError, IndexError):
            pass

    upcast = getattr(spell, "upcast_json", None) or {}
    upcast_per_level = 0
    if upcast.get("mode") == "extra_heal_dice":
        raw_per = upcast.get("perLevel")
        if isinstance(raw_per, (int, float)):
            upcast_per_level = int(raw_per)

    def _formula(count: int) -> str:
        dice_str = f"{count}d{die_sides}"
        if modifier > 0:
            return f"{dice_str} + {modifier}"
        if modifier < 0:
            return f"{dice_str} - {abs(modifier)}"
        return dice_str

    return {
        "base_formula": _formula(base_count),
        "base_dice": base_dice,
        "base_count": base_count,
        "die_sides": die_sides,
        "modifier": modifier,
        "upcast_per_level": upcast_per_level,
    }


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


def collect_temp_hp_effects(
    spell,
    variant_key: str | None,
) -> list[dict]:
    """Return only grant_temp_hp effect dicts from the spell's effective effects list."""
    return [
        e for e in _resolve_effects(spell, variant_key)
        if isinstance(e, dict) and e.get("type") == "grant_temp_hp"
    ]


def compute_temp_hp_upcast_bonus(
    spell,
    slot_level: int | None,
) -> int:
    """Compute the flat upcast bonus for grant_temp_hp via the canonical combat pipeline."""
    from app.services.combat_service.spell_dice_math import CombatSpellDiceMathMixin

    spell_level = getattr(spell, "level", 1) or 1
    raw_upcast = getattr(spell, "upcast_json", None)
    structured = CombatSpellDiceMathMixin._get_structured_spell_upcast(raw_upcast)
    if not structured or structured.get("mode") != "extra_temp_hp":
        return 0
    effective_slot = slot_level if isinstance(slot_level, int) else spell_level
    result = CombatSpellDiceMathMixin._apply_structured_spell_upcast(
        spell_level=spell_level,
        slot_level=effective_slot,
        effect_kind=None,
        effect_dice=None,
        effect_bonus=0,
        upcast=structured,
    )
    effect_bonus = result.get("effect_bonus") or 0
    return int(effect_bonus) if isinstance(effect_bonus, (int, float, str)) else 0


def roll_spell_temp_hp_effects(
    temp_hp_effects: list[dict],
    spell,
    slot_level: int | None,
) -> list[dict]:
    """Roll temp HP for each grant_temp_hp effect.

    Returns a list of dicts with keys: amount, target, base_dice, upcast_bonus.
    Uses the same canonical math as the combat upcast pipeline.
    """
    from app.services.combat_service.exceptions import _roll_dice_expression as _roll

    upcast_bonus = compute_temp_hp_upcast_bonus(spell, slot_level)

    results = []
    for effect in temp_hp_effects:
        params = effect.get("params") or {}
        base_dice = params.get("dice") or "1d4"
        rolled = _roll(base_dice) + upcast_bonus
        results.append({
            "amount": rolled,
            "target": effect.get("target", "caster"),
            "base_dice": base_dice,
            "upcast_bonus": upcast_bonus,
        })
    return results


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
