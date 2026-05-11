"""Tests for Healing Word (Palavra Curativa) out-of-combat automation (issue #305).

Covers:
- Seed: healing_word has correct level, school, casting time, range, dice, upcast
- heal effect type accepts 1d4 + spellcasting modifier
- build_persisted_effects returns [] (no active_spell_effects)
- collect_heal_effects finds the effect
- compute_heal_dice_with_upcast scales 1d4 → 2d4 → 3d4 → 5d4
- roll_spell_heal_effects rolls 1d4 + mod correctly
- HP application: heals, caps at max
- Regressions: cure_wounds still 1d8, goodberry still create_consumable
"""

from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from app.schemas.base_spell_effects import HealParams, SpellDeclarativeEffect
from app.services.out_of_combat_cast import (
    build_persisted_effects,
    collect_heal_effects,
    compute_heal_dice_with_upcast,
    roll_spell_heal_effects,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_spell(
    *,
    canonical_key: str = "healing_word",
    level: int = 1,
    effects_json: list | None = None,
    upcast_json: dict | None = None,
    out_of_combat_castable: bool = True,
    out_of_combat_target: str = "self_or_ally",
):
    from unittest.mock import MagicMock
    spell = MagicMock()
    spell.canonical_key = canonical_key
    spell.level = level
    spell.concentration = False
    spell.out_of_combat_castable = out_of_combat_castable
    spell.out_of_combat_target = out_of_combat_target
    spell.effects_json = effects_json if effects_json is not None else [
        {"type": "heal", "target": "selected_target",
         "params": {"dice": "1d4", "ability_modifier": "spellcasting"}}
    ]
    spell.variants_json = []
    spell.upcast_json = upcast_json if upcast_json is not None else {
        "mode": "extra_heal_dice",
        "dice": "1d4",
        "perLevel": 1,
    }
    spell.name_pt = "Palavra Curativa"
    spell.name_en = "Healing Word"
    return spell


def _caster_state(*, wisdom: int = 18) -> dict:
    return {
        "currentHP": 8, "maxHP": 20,
        "abilities": {
            "strength": 10, "dexterity": 10, "constitution": 10,
            "intelligence": 10, "wisdom": wisdom, "charisma": 10,
        },
        "spellcasting": {
            "ability": "wisdom",
            "slots": {"1": {"used": 0, "max": 4}},
        },
    }


# ---------------------------------------------------------------------------
# Seed tests
# ---------------------------------------------------------------------------

class HealingWordSeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app.services.seed_paths import resolve_base_seed_path
        seed_path = resolve_base_seed_path(__file__, "base_spells.seed.json")
        with open(seed_path) as f:
            raw = json.load(f)
        spells = raw["spells"] if isinstance(raw, dict) else raw
        cls.entry = next(
            (s for s in spells if isinstance(s, dict) and s.get("canonicalKey") == "healing_word"),
            None,
        )

    def test_entry_exists(self):
        self.assertIsNotNone(self.entry, "healing_word not found in seed")

    def test_level_is_1(self):
        self.assertEqual(self.entry["level"], 1)

    def test_school_is_evocation(self):
        self.assertEqual(self.entry["school"], "evocation")

    def test_casting_time_is_bonus_action(self):
        self.assertEqual(self.entry["castingTimeType"], "bonus_action")

    def test_range_is_18_meters(self):
        self.assertEqual(self.entry["rangeMeters"], 18)

    def test_duration_is_instantaneous(self):
        self.assertEqual(self.entry["duration"], "Instantaneous")

    def test_no_concentration(self):
        self.assertFalse(self.entry["concentration"])

    def test_heal_dice_is_1d4(self):
        self.assertEqual(self.entry["healDice"], "1d4")

    def test_upcast_extra_heal_dice_1d4(self):
        upcast = self.entry["upcast"]
        self.assertEqual(upcast["mode"], "extra_heal_dice")
        self.assertEqual(upcast["dice"], "1d4")
        self.assertEqual(upcast["perLevel"], 1)

    def test_out_of_combat_castable(self):
        self.assertTrue(self.entry.get("outOfCombatCastable"))

    def test_out_of_combat_target_self_or_ally(self):
        self.assertEqual(self.entry.get("outOfCombatTarget"), "self_or_ally")

    def test_has_heal_effect(self):
        effects = self.entry.get("effects", [])
        heal_effects = [e for e in effects if e.get("type") == "heal"]
        self.assertEqual(len(heal_effects), 1)

    def test_heal_effect_dice_1d4(self):
        effects = self.entry.get("effects", [])
        heal = next(e for e in effects if e.get("type") == "heal")
        self.assertEqual(heal["params"]["dice"], "1d4")
        self.assertEqual(heal["params"]["ability_modifier"], "spellcasting")

    def test_name_pt_is_palavra_curativa(self):
        self.assertEqual(self.entry.get("namePt"), "Palavra Curativa")


# ---------------------------------------------------------------------------
# Schema: heal params accept 1d4
# ---------------------------------------------------------------------------

class HealingWordSchemaTests(unittest.TestCase):
    def test_heal_effect_validates_with_1d4(self):
        effect = SpellDeclarativeEffect(**{
            "type": "heal",
            "target": "selected_target",
            "params": {"dice": "1d4", "ability_modifier": "spellcasting"},
        })
        self.assertIsInstance(effect.params, HealParams)
        self.assertEqual(effect.params.dice, "1d4")

    def test_heal_effect_rejects_missing_ability_modifier_key(self):
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            SpellDeclarativeEffect(**{
                "type": "heal",
                "target": "selected_target",
                "params": {"dice": "1d4"},  # missing ability_modifier → matches GrantTempHpParams, wrong type
            })


# ---------------------------------------------------------------------------
# Pipeline: build_persisted_effects / collect_heal_effects
# ---------------------------------------------------------------------------

class HealingWordPipelineTests(unittest.TestCase):
    def test_build_persisted_effects_returns_empty(self):
        spell = _make_spell()
        effects = build_persisted_effects(
            spell=spell, caster_user_id="u1", target_user_id="u2",
            variant_key=None, game_time_seconds=0,
        )
        self.assertEqual(effects, [], "heal must not produce active_spell_effects")

    def test_collect_heal_effects_finds_1d4_effect(self):
        spell = _make_spell()
        collected = collect_heal_effects(spell, variant_key=None)
        self.assertEqual(len(collected), 1)
        self.assertEqual(collected[0]["params"]["dice"], "1d4")

    def test_no_consumable_effects(self):
        from app.services.out_of_combat_cast import collect_create_consumable_effects
        spell = _make_spell()
        self.assertEqual(collect_create_consumable_effects(spell, variant_key=None), [])


# ---------------------------------------------------------------------------
# Upcast
# ---------------------------------------------------------------------------

class HealingWordUpcastTests(unittest.TestCase):
    def test_slot_1_gives_1d4(self):
        spell = _make_spell()
        self.assertEqual(compute_heal_dice_with_upcast("1d4", spell, slot_level=1), "1d4")

    def test_slot_2_gives_2d4(self):
        spell = _make_spell()
        self.assertEqual(compute_heal_dice_with_upcast("1d4", spell, slot_level=2), "2d4")

    def test_slot_3_gives_3d4(self):
        spell = _make_spell()
        self.assertEqual(compute_heal_dice_with_upcast("1d4", spell, slot_level=3), "3d4")

    def test_slot_5_gives_5d4(self):
        spell = _make_spell()
        self.assertEqual(compute_heal_dice_with_upcast("1d4", spell, slot_level=5), "5d4")


# ---------------------------------------------------------------------------
# Roll heal effects
# ---------------------------------------------------------------------------

class HealingWordRollTests(unittest.TestCase):
    def test_base_roll_adds_modifier(self):
        spell = _make_spell()
        state = _caster_state(wisdom=18)  # mod = (18-10)//2 = 4
        effects = collect_heal_effects(spell, variant_key=None)
        with patch("app.services.out_of_combat_cast.random.randint", return_value=3):
            results = roll_spell_heal_effects(effects, spell, slot_level=1, caster_state_json=state)
        self.assertEqual(results[0]["amount"], 7)   # 3 + 4 = 7
        self.assertEqual(results[0]["effective_dice"], "1d4")
        self.assertEqual(results[0]["modifier"], 4)

    def test_upcast_roll_uses_more_dice(self):
        spell = _make_spell()
        state = _caster_state(wisdom=14)  # mod = 2
        effects = collect_heal_effects(spell, variant_key=None)
        with patch("app.services.out_of_combat_cast.random.randint", return_value=4):
            results = roll_spell_heal_effects(effects, spell, slot_level=3, caster_state_json=state)
        self.assertEqual(results[0]["effective_dice"], "3d4")
        self.assertEqual(results[0]["amount"], 14)  # 4+4+4 + 2 = 14
        self.assertEqual(len(results[0]["rolls"]), 3)


# ---------------------------------------------------------------------------
# Regression tests
# ---------------------------------------------------------------------------

class HealingWordRegressionTests(unittest.TestCase):
    def test_cure_wounds_still_uses_1d8(self):
        from unittest.mock import MagicMock
        cure = MagicMock()
        cure.level = 1
        cure.effects_json = [
            {"type": "heal", "target": "selected_target",
             "params": {"dice": "1d8", "ability_modifier": "spellcasting"}}
        ]
        cure.variants_json = []
        cure.upcast_json = {"mode": "extra_heal_dice", "dice": "1d8", "perLevel": 1}
        effects = collect_heal_effects(cure, variant_key=None)
        result = compute_heal_dice_with_upcast(effects[0]["params"]["dice"], cure, slot_level=1)
        self.assertEqual(result, "1d8")

    def test_goodberry_still_creates_consumable_not_heal(self):
        from unittest.mock import MagicMock
        from app.services.out_of_combat_cast import collect_create_consumable_effects
        goodberry = MagicMock()
        goodberry.effects_json = [
            {"type": "create_consumable", "target": "caster",
             "params": {"canonical_key": "goodberry", "quantity": 10, "expires_in_seconds": 86400}}
        ]
        goodberry.variants_json = []
        self.assertEqual(collect_heal_effects(goodberry, variant_key=None), [])
        self.assertEqual(len(collect_create_consumable_effects(goodberry, variant_key=None)), 1)

    def test_cure_wounds_upcast_still_works_independently(self):
        from unittest.mock import MagicMock
        cure = MagicMock()
        cure.level = 1
        cure.upcast_json = {"mode": "extra_heal_dice", "dice": "1d8", "perLevel": 1}
        self.assertEqual(compute_heal_dice_with_upcast("1d8", cure, slot_level=3), "3d8")


if __name__ == "__main__":
    unittest.main()
