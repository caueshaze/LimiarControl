"""Tests for Sacred Flame (issue #353).

Covers:
- Seed/catalog contract (DEX save, save success = none, radiant, no cover benefit)
- Cantrip scaling by character level (1d8/2d8/3d8/4d8)
- Save semantics: success => 0 damage (never half unless explicitly half_damage)
- Mechanical no-cover behavior via resolve_cover_save_dc
"""

from __future__ import annotations

import json
import unittest

from app.services.combat import CombatService
from app.services.combat_service.cover_modifiers import resolve_cover_save_dc
from app.services.combat_service.spell_dice_math import CombatSpellDiceMathMixin


class SacredFlameSeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app.services.seed_paths import resolve_base_seed_path

        seed_path = resolve_base_seed_path(__file__, "base_spells.seed.json")
        with open(seed_path) as f:
            raw = json.load(f)
        spells = raw["spells"] if isinstance(raw, dict) else raw
        cls.entry = next(
            (s for s in spells if isinstance(s, dict) and s.get("canonicalKey") == "sacred_flame"),
            None,
        )

    def test_entry_exists(self):
        self.assertIsNotNone(self.entry, "sacred_flame not found in seed")

    def test_contract_fields(self):
        self.assertEqual(self.entry["level"], 0)
        self.assertEqual(self.entry["school"], "evocation")
        self.assertEqual(self.entry["castingTimeType"], "action")
        self.assertEqual(self.entry["rangeMeters"], 18)
        self.assertEqual(self.entry["savingThrow"], "DEX")
        self.assertEqual(self.entry["saveSuccessOutcome"], "none")
        self.assertEqual(self.entry["damageDice"], "1d8")
        self.assertEqual(self.entry["damageType"], "Radiant")
        self.assertEqual(self.entry["coverAppliesToSave"], "none")
        self.assertFalse(self.entry["concentration"])

    def test_no_upcast_slot_path(self):
        self.assertIsNone(self.entry.get("upcast"))
        self.assertIsNone(self.entry.get("upcastJson"))
        self.assertIsNone(self.entry.get("upcast_json"))

    def test_cantrip_scaling_present(self):
        cs = self.entry.get("cantripScaling")
        self.assertIsNotNone(cs)
        self.assertEqual(cs["scalingMode"], "character_level")
        self.assertEqual(cs["scalingEffectType"], "damage_dice")

    def test_cantrip_scaling_thresholds(self):
        thresholds = self.entry["cantripScaling"]["thresholds"]
        t1 = next(t for t in thresholds if t["characterLevel"] == 1)
        t5 = next(t for t in thresholds if t["characterLevel"] == 5)
        t11 = next(t for t in thresholds if t["characterLevel"] == 11)
        t17 = next(t for t in thresholds if t["characterLevel"] == 17)
        self.assertEqual(t1["damage"]["dice"], "1d8")
        self.assertEqual(t5["damage"]["dice"], "2d8")
        self.assertEqual(t11["damage"]["dice"], "3d8")
        self.assertEqual(t17["damage"]["dice"], "4d8")


class SacredFlameCantripScalingTests(unittest.TestCase):
    SCALING = {
        "scalingMode": "character_level",
        "scalingEffectType": "damage_dice",
        "thresholds": [
            {"characterLevel": 1, "damage": {"dice": "1d8"}},
            {"characterLevel": 5, "damage": {"dice": "2d8"}},
            {"characterLevel": 11, "damage": {"dice": "3d8"}},
            {"characterLevel": 17, "damage": {"dice": "4d8"}},
        ],
    }

    def _apply(self, caster_level: int, *, spell_level: int = 0):
        return CombatSpellDiceMathMixin._apply_character_level_cantrip_scaling(
            spell_level=spell_level,
            caster_level=caster_level,
            effect_dice="1d8",
            cantrip_scaling=self.SCALING,
        )

    def test_scales_by_character_level(self):
        self.assertEqual(self._apply(1)["effect_dice"], "1d8")
        self.assertEqual(self._apply(5)["effect_dice"], "2d8")
        self.assertEqual(self._apply(11)["effect_dice"], "3d8")
        self.assertEqual(self._apply(17)["effect_dice"], "4d8")

    def test_not_slot_based_no_upcast(self):
        # Leveled spell must not use cantrip scaling even with high caster level.
        self.assertEqual(self._apply(17, spell_level=1)["effect_dice"], "1d8")


class SacredFlameSaveOutcomeTests(unittest.TestCase):
    def test_failed_save_takes_full_damage(self):
        self.assertEqual(
            CombatService._resolve_save_damage_amount(
                7,
                is_saved=False,
                save_success_outcome="none",
            ),
            7,
        )

    def test_successful_save_deals_zero_damage_for_none(self):
        self.assertEqual(
            CombatService._resolve_save_damage_amount(
                7,
                is_saved=True,
                save_success_outcome="none",
            ),
            0,
        )

    def test_successful_save_is_not_half_damage_for_none(self):
        # Guardrail explicit: Sacred Flame semantics are save-success => 0, never half.
        self.assertNotEqual(
            CombatService._resolve_save_damage_amount(
                7,
                is_saved=True,
                save_success_outcome="none",
            ),
            3,
        )


class SacredFlameCoverBehaviorTests(unittest.TestCase):
    def test_cover_none_keeps_dc_even_with_cover(self):
        effective, modifier = resolve_cover_save_dc(15, "threeQuarters", "none", "dexterity")
        self.assertEqual(effective, 15)
        self.assertEqual(modifier, 0)

    def test_cover_none_matches_no_cover_scenario(self):
        effective_with_cover, _ = resolve_cover_save_dc(15, "half", "none", "dexterity")
        effective_without_cover, _ = resolve_cover_save_dc(15, "none", "none", "dexterity")
        self.assertEqual(effective_with_cover, effective_without_cover)

    def test_physical_cover_spell_still_reduces_dc_regression(self):
        effective, modifier = resolve_cover_save_dc(15, "half", "physical", "dexterity")
        self.assertEqual(effective, 13)
        self.assertEqual(modifier, 2)


if __name__ == "__main__":
    unittest.main()
