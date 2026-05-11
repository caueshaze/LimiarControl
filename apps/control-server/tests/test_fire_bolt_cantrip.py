"""Tests for Fire Bolt (Raio de Fogo) cantrip scaling (issue #309).

Covers:
- Seed: fire_bolt has correct fields and damage_dice cantripScaling
- damage_dice scaling: 1d10 → 2d10 → 3d10 → 4d10 at levels 1/5/11/17
- cantrip_instance_count is always None (single-roll, not multi-beam)
- damage_dice vs effect_instances distinction (Fire Bolt vs Eldritch Blast)
- Regressions: Acid Splash and Eldritch Blast scaling unchanged
"""

from __future__ import annotations

import json
import unittest

from app.services.combat_service.spell_dice_math import CombatSpellDiceMathMixin


FIRE_BOLT_SCALING = {
    "scalingMode": "character_level",
    "scalingEffectType": "damage_dice",
    "thresholds": [
        {"characterLevel": 1, "damage": {"dice": "1d10"}},
        {"characterLevel": 5, "damage": {"dice": "2d10"}},
        {"characterLevel": 11, "damage": {"dice": "3d10"}},
        {"characterLevel": 17, "damage": {"dice": "4d10"}},
    ],
}

ELDRITCH_BLAST_SCALING = {
    "scalingMode": "character_level",
    "scalingEffectType": "effect_instances",
    "thresholds": [
        {"characterLevel": 1, "instances": 1, "instanceDamage": {"dice": "1d10"}},
        {"characterLevel": 5, "instances": 2, "instanceDamage": {"dice": "1d10"}},
        {"characterLevel": 11, "instances": 3, "instanceDamage": {"dice": "1d10"}},
        {"characterLevel": 17, "instances": 4, "instanceDamage": {"dice": "1d10"}},
    ],
}

ACID_SPLASH_SCALING = {
    "scalingMode": "character_level",
    "scalingEffectType": "damage_dice",
    "thresholds": [
        {"characterLevel": 1, "damage": {"dice": "1d6"}},
        {"characterLevel": 5, "damage": {"dice": "2d6"}},
        {"characterLevel": 11, "damage": {"dice": "3d6"}},
        {"characterLevel": 17, "damage": {"dice": "4d6"}},
    ],
}


def _apply(spell_level, caster_level, effect_dice, cantrip_scaling):
    return CombatSpellDiceMathMixin._apply_character_level_cantrip_scaling(
        spell_level=spell_level,
        caster_level=caster_level,
        effect_dice=effect_dice,
        cantrip_scaling=cantrip_scaling,
    )


# ---------------------------------------------------------------------------
# Seed tests
# ---------------------------------------------------------------------------

class FireBoltSeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app.services.seed_paths import resolve_base_seed_path
        seed_path = resolve_base_seed_path(__file__, "base_spells.seed.json")
        with open(seed_path) as f:
            raw = json.load(f)
        spells = raw["spells"] if isinstance(raw, dict) else raw
        cls.entry = next(
            (s for s in spells if isinstance(s, dict) and s.get("canonicalKey") == "fire_bolt"),
            None,
        )

    def test_entry_exists(self):
        self.assertIsNotNone(self.entry, "fire_bolt not found in seed")

    def test_level_is_0(self):
        self.assertEqual(self.entry["level"], 0)

    def test_school_is_evocation(self):
        self.assertEqual(self.entry["school"], "evocation")

    def test_casting_time_is_action(self):
        self.assertEqual(self.entry["castingTimeType"], "action")

    def test_range_is_36_meters(self):
        self.assertEqual(self.entry["rangeMeters"], 36)

    def test_range_text_is_120ft(self):
        self.assertEqual(self.entry["rangeText"], "120 ft")

    def test_duration_instantaneous(self):
        self.assertEqual(self.entry["duration"], "Instantaneous")

    def test_no_concentration(self):
        self.assertFalse(self.entry["concentration"])

    def test_damage_dice_1d10(self):
        self.assertEqual(self.entry["damageDice"], "1d10")

    def test_damage_type_fire(self):
        self.assertEqual(self.entry["damageType"], "Fire")

    def test_attack_type_ranged_spell(self):
        self.assertEqual(self.entry["attackType"], "ranged_spell")

    def test_name_pt_raio_de_fogo(self):
        self.assertEqual(self.entry.get("namePt"), "Raio de Fogo")

    def test_no_upcast(self):
        self.assertIsNone(self.entry.get("upcast"))

    def test_no_upcast_json(self):
        self.assertIsNone(self.entry.get("upcastJson"))

    def test_no_upcast_snake_case(self):
        self.assertIsNone(self.entry.get("upcast_json"))

    def test_no_double_scaling(self):
        """Cantrip must not have both cantripScaling and any upcast field — no double scaling."""
        has_cantrip_scaling = self.entry.get("cantripScaling") is not None
        has_any_upcast = any(
            self.entry.get(k) is not None
            for k in ("upcast", "upcastJson", "upcast_json")
        )
        self.assertTrue(has_cantrip_scaling, "cantripScaling should be present")
        self.assertFalse(has_any_upcast, "cantrip must not have any upcast field")

    def test_cantrip_scaling_present(self):
        self.assertIsNotNone(self.entry.get("cantripScaling"))

    def test_cantrip_scaling_mode_character_level(self):
        cs = self.entry["cantripScaling"]
        self.assertEqual(cs["scalingMode"], "character_level")

    def test_cantrip_scaling_effect_type_damage_dice(self):
        cs = self.entry["cantripScaling"]
        self.assertEqual(cs["scalingEffectType"], "damage_dice")

    def test_cantrip_scaling_has_4_thresholds(self):
        cs = self.entry["cantripScaling"]
        self.assertEqual(len(cs["thresholds"]), 4)

    def test_cantrip_scaling_threshold_level5_is_2d10(self):
        thresholds = self.entry["cantripScaling"]["thresholds"]
        t5 = next(t for t in thresholds if t["characterLevel"] == 5)
        self.assertEqual(t5["damage"]["dice"], "2d10")

    def test_cantrip_scaling_threshold_level11_is_3d10(self):
        thresholds = self.entry["cantripScaling"]["thresholds"]
        t11 = next(t for t in thresholds if t["characterLevel"] == 11)
        self.assertEqual(t11["damage"]["dice"], "3d10")

    def test_cantrip_scaling_threshold_level17_is_4d10(self):
        thresholds = self.entry["cantripScaling"]["thresholds"]
        t17 = next(t for t in thresholds if t["characterLevel"] == 17)
        self.assertEqual(t17["damage"]["dice"], "4d10")


# ---------------------------------------------------------------------------
# Cantrip scaling dice math tests
# ---------------------------------------------------------------------------

class FireBoltCantripScalingTests(unittest.TestCase):
    def _apply(self, caster_level):
        return _apply(0, caster_level, "1d10", FIRE_BOLT_SCALING)

    def test_level_1_gives_1d10(self):
        self.assertEqual(self._apply(1)["effect_dice"], "1d10")

    def test_level_4_gives_1d10(self):
        self.assertEqual(self._apply(4)["effect_dice"], "1d10")

    def test_level_5_gives_2d10(self):
        self.assertEqual(self._apply(5)["effect_dice"], "2d10")

    def test_level_10_gives_2d10(self):
        self.assertEqual(self._apply(10)["effect_dice"], "2d10")

    def test_level_11_gives_3d10(self):
        self.assertEqual(self._apply(11)["effect_dice"], "3d10")

    def test_level_16_gives_3d10(self):
        self.assertEqual(self._apply(16)["effect_dice"], "3d10")

    def test_level_17_gives_4d10(self):
        self.assertEqual(self._apply(17)["effect_dice"], "4d10")

    def test_level_20_gives_4d10(self):
        self.assertEqual(self._apply(20)["effect_dice"], "4d10")

    def test_cantrip_instance_count_always_none(self):
        """damage_dice type never returns instance metadata — single-roll semantic."""
        for level in [1, 5, 11, 17]:
            result = self._apply(level)
            self.assertIsNone(result["cantrip_instance_count"],
                              f"expected None at level {level}, got {result['cantrip_instance_count']}")

    def test_cantrip_instance_dice_always_none(self):
        for level in [1, 5, 11, 17]:
            result = self._apply(level)
            self.assertIsNone(result["cantrip_instance_dice"])

    def test_not_applied_to_leveled_spell(self):
        result = _apply(1, 5, "1d10", FIRE_BOLT_SCALING)
        self.assertEqual(result["effect_dice"], "1d10")

    def test_not_applied_when_caster_level_none(self):
        result = _apply(0, None, "1d10", FIRE_BOLT_SCALING)
        self.assertEqual(result["effect_dice"], "1d10")


# ---------------------------------------------------------------------------
# damage_dice vs effect_instances distinction
# ---------------------------------------------------------------------------

class FireBoltScalingTypeTests(unittest.TestCase):
    """Verify the semantic difference between Fire Bolt (damage_dice) and Eldritch Blast (effect_instances)."""

    def test_fire_bolt_level5_single_roll_no_instances(self):
        result = _apply(0, 5, "1d10", FIRE_BOLT_SCALING)
        self.assertEqual(result["effect_dice"], "2d10")
        self.assertIsNone(result["cantrip_instance_count"])   # single roll
        self.assertIsNone(result["cantrip_instance_dice"])

    def test_eldritch_blast_level5_two_instances(self):
        result = _apply(0, 5, "1d10", ELDRITCH_BLAST_SCALING)
        self.assertEqual(result["effect_dice"], "2d10")
        self.assertEqual(result["cantrip_instance_count"], 2)   # two separate rolls
        self.assertEqual(result["cantrip_instance_dice"], "1d10")

    def test_both_produce_same_aggregate_dice_at_level5(self):
        fb = _apply(0, 5, "1d10", FIRE_BOLT_SCALING)
        eb = _apply(0, 5, "1d10", ELDRITCH_BLAST_SCALING)
        self.assertEqual(fb["effect_dice"], eb["effect_dice"])  # same aggregate: "2d10"

    def test_only_effect_instances_populates_instance_count(self):
        fb = _apply(0, 11, "1d10", FIRE_BOLT_SCALING)
        eb = _apply(0, 11, "1d10", ELDRITCH_BLAST_SCALING)
        self.assertIsNone(fb["cantrip_instance_count"])
        self.assertEqual(eb["cantrip_instance_count"], 3)


# ---------------------------------------------------------------------------
# Regression tests
# ---------------------------------------------------------------------------

class FireBoltRegressionTests(unittest.TestCase):
    def test_acid_splash_damage_dice_level5_still_2d6(self):
        result = _apply(0, 5, "1d6", ACID_SPLASH_SCALING)
        self.assertEqual(result["effect_dice"], "2d6")
        self.assertIsNone(result["cantrip_instance_count"])

    def test_acid_splash_damage_dice_level17_still_4d6(self):
        result = _apply(0, 17, "1d6", ACID_SPLASH_SCALING)
        self.assertEqual(result["effect_dice"], "4d6")

    def test_eldritch_blast_instances_level17_still_4(self):
        result = _apply(0, 17, "1d10", ELDRITCH_BLAST_SCALING)
        self.assertEqual(result["cantrip_instance_count"], 4)
        self.assertEqual(result["effect_dice"], "4d10")

    def test_fire_bolt_scaling_does_not_affect_leveled_spells(self):
        result = _apply(1, 17, "1d10", FIRE_BOLT_SCALING)
        self.assertEqual(result["effect_dice"], "1d10")

    def test_no_scaling_returns_original_dice(self):
        result = _apply(0, 17, "1d10", None)
        self.assertEqual(result["effect_dice"], "1d10")
        self.assertIsNone(result["cantrip_instance_count"])


if __name__ == "__main__":
    unittest.main()
