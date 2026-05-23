"""Tests for Burning Hands (Mãos Flamejantes).

Covers:
- Seed contract: level=1, cone 4.5m, DEX save, half_damage on success, upcast +1d6/level
- Save semantics: success → half damage, failure → full damage
- Upcast damage dice scaling: slot 1=3d6, slot 2=4d6, slot 3=5d6
- Cover: coverAppliesToSave=physical → DC reduced by half/three-quarters cover
- Cone geometry validated in test_aoe_preview_contract.py; not re-tested here
"""

from __future__ import annotations

import json
import unittest

from app.services.combat import CombatService
from app.services.combat_service.cover_modifiers import resolve_cover_save_dc
from app.services.combat_service.spell_dice_math import CombatSpellDiceMathMixin


def _apply_upcast(base_dice: str, slot_level: int, spell_level: int = 1, upcast_config: dict | None = None):
    if upcast_config is None:
        upcast_config = {"mode": "extra_damage_dice", "dice": "1d6", "perLevel": 1}
    result = CombatSpellDiceMathMixin._apply_structured_spell_upcast(
        spell_level=spell_level,
        slot_level=slot_level,
        effect_kind="damage",
        effect_dice=base_dice,
        effect_bonus=0,
        upcast=upcast_config,
    )
    return result["effect_dice"]


# ---------------------------------------------------------------------------
# Seed tests
# ---------------------------------------------------------------------------

class BurningHandsSeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app.services.seed_paths import resolve_base_seed_path
        seed_path = resolve_base_seed_path(__file__, "base_spells.seed.json")
        with open(seed_path) as f:
            raw = json.load(f)
        spells = raw["spells"] if isinstance(raw, dict) else raw
        cls.entry = next(
            (s for s in spells if isinstance(s, dict) and s.get("canonicalKey") == "burning_hands"),
            None,
        )

    def test_entry_exists(self):
        self.assertIsNotNone(self.entry, "burning_hands not found in seed")

    def test_contract_fields(self):
        e = self.entry
        self.assertEqual(e["level"], 1)
        self.assertEqual(e["school"], "evocation")
        self.assertEqual(e["castingTimeType"], "action")
        self.assertEqual(e["savingThrow"], "DEX")
        self.assertEqual(e["saveSuccessOutcome"], "half_damage")
        self.assertEqual(e["damageDice"], "3d6")
        self.assertEqual(e["damageType"], "Fire")
        self.assertFalse(e["concentration"])

    def test_area_shape_cone(self):
        self.assertEqual(self.entry.get("areaShape"), "cone")

    def test_cone_length_meters(self):
        self.assertEqual(self.entry.get("lengthMeters"), 4.5)

    def test_cover_applies_to_save_physical(self):
        self.assertEqual(self.entry.get("coverAppliesToSave"), "physical")

    def test_upcast_config(self):
        up = self.entry.get("upcast")
        self.assertIsNotNone(up)
        self.assertEqual(up["mode"], "extra_damage_dice")
        self.assertEqual(up["dice"], "1d6")
        self.assertEqual(up["perLevel"], 1)

    def test_selection_type_direction(self):
        self.assertEqual(self.entry.get("selectionType"), "direction")

    def test_origin_type_caster(self):
        self.assertEqual(self.entry.get("originType"), "caster")


# ---------------------------------------------------------------------------
# Save outcome semantics
# ---------------------------------------------------------------------------

class BurningHandsSaveOutcomeTests(unittest.TestCase):
    def test_failed_save_takes_full_damage(self):
        self.assertEqual(
            CombatService._resolve_save_damage_amount(18, is_saved=False, save_success_outcome="half_damage"),
            18,
        )

    def test_successful_save_takes_half_damage(self):
        self.assertEqual(
            CombatService._resolve_save_damage_amount(18, is_saved=True, save_success_outcome="half_damage"),
            9,
        )

    def test_half_damage_rounds_down(self):
        self.assertEqual(
            CombatService._resolve_save_damage_amount(7, is_saved=True, save_success_outcome="half_damage"),
            3,
        )

    def test_not_zero_on_success(self):
        self.assertNotEqual(
            CombatService._resolve_save_damage_amount(12, is_saved=True, save_success_outcome="half_damage"),
            0,
        )


# ---------------------------------------------------------------------------
# Upcast damage scaling
# ---------------------------------------------------------------------------

class BurningHandsUpcastTests(unittest.TestCase):
    def test_slot_1_base_dice(self):
        result = _apply_upcast("3d6", slot_level=1)
        self.assertEqual(result, "3d6")

    def test_slot_2_adds_1d6(self):
        result = _apply_upcast("3d6", slot_level=2)
        self.assertEqual(result, "4d6")

    def test_slot_3_adds_2d6(self):
        result = _apply_upcast("3d6", slot_level=3)
        self.assertEqual(result, "5d6")

    def test_slot_4_adds_3d6(self):
        result = _apply_upcast("3d6", slot_level=4)
        self.assertEqual(result, "6d6")

    def test_slot_5_adds_4d6(self):
        result = _apply_upcast("3d6", slot_level=5)
        self.assertEqual(result, "7d6")


# ---------------------------------------------------------------------------
# Cover behavior
# ---------------------------------------------------------------------------

class BurningHandsCoverTests(unittest.TestCase):
    def test_half_cover_reduces_dc(self):
        effective, modifier = resolve_cover_save_dc(14, "half", "physical", "dexterity")
        self.assertLess(effective, 14)
        self.assertGreater(modifier, 0)

    def test_three_quarters_cover_reduces_dc_more(self):
        _, mod_half = resolve_cover_save_dc(14, "half", "physical", "dexterity")
        _, mod_3q = resolve_cover_save_dc(14, "threeQuarters", "physical", "dexterity")
        self.assertGreater(mod_3q, mod_half)

    def test_no_cover_keeps_full_dc(self):
        effective, modifier = resolve_cover_save_dc(14, None, "physical", "dexterity")
        self.assertEqual(effective, 14)
        self.assertEqual(modifier, 0)
