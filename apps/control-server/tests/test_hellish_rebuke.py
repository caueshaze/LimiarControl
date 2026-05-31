from __future__ import annotations

import json
from pathlib import Path

from app.services.combat_service.spells.spell_context_resolve import SpellContextResolveMixin
from app.services.spell_targeting_semantics import resolve_spell_targeting_semantics


def _seed_entry() -> dict:
    seed_path = Path(__file__).resolve().parents[3] / "Base" / "base_spells.seed.json"
    payload = json.loads(seed_path.read_text(encoding="utf-8"))
    spells = payload.get("spells") or []
    for spell in spells:
        if spell.get("canonicalKey") == "hellish_rebuke":
            return spell
    raise AssertionError("hellish_rebuke not found in seed")


def test_hellish_rebuke_seed_contract():
    entry = _seed_entry()
    assert entry["level"] == 1
    assert entry["school"] == "evocation"
    assert "Warlock" in entry["classesJson"]
    assert entry["castingTimeType"] == "reaction"
    assert entry["castingTime"] == "1 reaction"
    assert entry["rangeMeters"] == 18
    assert entry["durationSeconds"] == 0
    assert entry["concentration"] is False
    assert entry["ritual"] is False
    assert entry["resolutionType"] == "damage"
    assert entry["attackType"] == "save"
    assert entry["savingThrowAbility"] == "DEX"
    assert entry["saveSuccessOutcome"] == "half_damage"
    assert entry["damageDice"] == "2d10"
    assert entry["damageType"] == "fire"
    assert entry["outOfCombatCastable"] is False



def test_hellish_rebuke_targeting_semantics_override():
    semantics = resolve_spell_targeting_semantics({"canonicalKey": "hellish_rebuke"}).to_dict()
    assert semantics == {
        "selection_type": "reaction_source",
        "origin_type": "damaged_caster",
        "target_anchor": "damage_source",
        "attack_type": "save",
        "range_kind": "distance",
        "effect_timing": "reaction",
    }



def test_hellish_rebuke_context_metadata():
    utility = SpellContextResolveMixin.UTILITY_SPELL_CONTEXT_META["hellish_rebuke"]
    reaction = utility["reaction"]
    assert reaction["trigger"] == "damaged_by_visible_creature_within_range"
    assert reaction["consumesReaction"] is True
    assert reaction["requiresVisibleSource"] is True
    assert reaction["rangeMeters"] == 18
    save = utility["save"]
    assert save["ability"] == "dexterity"
    assert save["effect"] == "half_damage"
    damage = utility["damage"]
    assert damage["dice"] == "2d10"
    assert damage["type"] == "fire"
    assert damage["upcastDicePerSlotAboveBase"] == "1d10"
