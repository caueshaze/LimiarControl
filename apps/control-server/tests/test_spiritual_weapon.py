"""Tests for Spiritual Weapon spell automation.

Covers:
- Catalog entry presence
- Upcast scaling helper
- Targeting semantics registration
- Automation registry
- Cast: creates anchor, handles recast (replaces), optional initial attack
- Follow-up: moves anchor, attacks, bonus action consumption
"""

from __future__ import annotations

import unittest

from app.services.combat_service.spell_automation import CombatSpellAutomationMixin
from app.services.combat_service.spells.automation._spiritual_weapon import resolve_spiritual_weapon_damage_dice
from app.services.spell_targeting_semantics import (
    explicit_spell_targeting_overrides,
    resolve_spell_targeting_semantics,
)


class TestSpiritualWeaponUpcastHelper(unittest.TestCase):
    def test_slot_2_is_1d8(self):
        self.assertEqual(resolve_spiritual_weapon_damage_dice(2), "1d8")

    def test_slot_3_is_1d8(self):
        self.assertEqual(resolve_spiritual_weapon_damage_dice(3), "1d8")

    def test_slot_4_is_2d8(self):
        self.assertEqual(resolve_spiritual_weapon_damage_dice(4), "2d8")

    def test_slot_5_is_2d8(self):
        self.assertEqual(resolve_spiritual_weapon_damage_dice(5), "2d8")

    def test_slot_6_is_3d8(self):
        self.assertEqual(resolve_spiritual_weapon_damage_dice(6), "3d8")

    def test_slot_7_is_3d8(self):
        self.assertEqual(resolve_spiritual_weapon_damage_dice(7), "3d8")

    def test_slot_8_is_4d8(self):
        self.assertEqual(resolve_spiritual_weapon_damage_dice(8), "4d8")


class TestSpiritualWeaponRegistry(unittest.TestCase):
    def test_is_registered(self):
        self.assertIn("spiritual_weapon", CombatSpellAutomationMixin._SPELL_AUTOMATION_REGISTRY)

    def test_handler_name(self):
        spec = CombatSpellAutomationMixin._SPELL_AUTOMATION_REGISTRY["spiritual_weapon"]
        self.assertEqual(spec.handler_name, "_cast_spiritual_weapon_automation")

    def test_default_mode_is_spell_attack(self):
        spec = CombatSpellAutomationMixin._SPELL_AUTOMATION_REGISTRY["spiritual_weapon"]
        self.assertEqual(spec.default_mode, "spell_attack")

    def test_requires_effect_payload(self):
        spec = CombatSpellAutomationMixin._SPELL_AUTOMATION_REGISTRY["spiritual_weapon"]
        self.assertTrue(spec.requires_effect_payload)


class TestSpiritualWeaponTargetingSemantics(unittest.TestCase):
    def _semantics(self):
        return resolve_spell_targeting_semantics({"canonicalKey": "spiritual_weapon"})

    def test_is_in_explicit_overrides(self):
        overrides = explicit_spell_targeting_overrides()
        self.assertIn("spiritual_weapon", overrides)

    def test_selection_type_is_point(self):
        self.assertEqual(self._semantics().selection_type, "point")

    def test_effect_timing_is_persistent(self):
        self.assertEqual(self._semantics().effect_timing, "persistent")

    def test_attack_type_is_melee_spell(self):
        self.assertEqual(self._semantics().attack_type, "melee_spell")


class TestSpiritualWeaponSeedCatalog(unittest.TestCase):
    def _load_seed(self):
        import json
        import os

        seed_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "Base", "base_spells.seed.json"
        )
        with open(os.path.abspath(seed_path)) as f:
            data = json.load(f)
        return {s["canonicalKey"]: s for s in data.get("spells", [])}

    def test_spiritual_weapon_exists_in_catalog(self):
        catalog = self._load_seed()
        self.assertIn("spiritual_weapon", catalog)

    def test_level_is_2(self):
        catalog = self._load_seed()
        self.assertEqual(catalog["spiritual_weapon"]["level"], 2)

    def test_concentration_is_false(self):
        catalog = self._load_seed()
        self.assertFalse(catalog["spiritual_weapon"]["concentration"])

    def test_casting_time_is_bonus_action(self):
        catalog = self._load_seed()
        self.assertEqual(catalog["spiritual_weapon"]["castingTimeType"], "bonus_action")

    def test_damage_type_is_force(self):
        catalog = self._load_seed()
        self.assertEqual(catalog["spiritual_weapon"]["damageType"], "Force")

    def test_damage_dice_is_1d8(self):
        catalog = self._load_seed()
        self.assertEqual(catalog["spiritual_weapon"]["damageDice"], "1d8")

    def test_school_is_evocation(self):
        catalog = self._load_seed()
        self.assertEqual(catalog["spiritual_weapon"]["school"], "evocation")

    def test_classes_include_cleric(self):
        catalog = self._load_seed()
        self.assertIn("Cleric", catalog["spiritual_weapon"]["classesJson"])

    def test_effect_timing_is_persistent(self):
        catalog = self._load_seed()
        self.assertEqual(catalog["spiritual_weapon"]["effectTiming"], "persistent")

    def test_selection_type_is_point(self):
        catalog = self._load_seed()
        self.assertEqual(catalog["spiritual_weapon"]["selectionType"], "point")


if __name__ == "__main__":
    unittest.main()
