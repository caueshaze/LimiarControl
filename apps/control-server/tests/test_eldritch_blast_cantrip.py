"""Tests for Eldritch Blast (Raio Místico) cantrip.

Covers:
- Seed contract: level=0, attackType=ranged_spell, cantripScaling effect_instances
- effect_instances scaling: 1/2/3/4 beams at char levels 1/5/11/17
- cantrip_instance_count and cantrip_instance_dice populated (vs fire_bolt which leaves them None)
- Distinction: effect_instances produces independent beams, not a single bigger roll
"""

from __future__ import annotations

import json
import unittest

from app.services.combat_service.spell_dice_math import CombatSpellDiceMathMixin


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


def _apply(caster_level):
    return CombatSpellDiceMathMixin._apply_character_level_cantrip_scaling(
        spell_level=0,
        caster_level=caster_level,
        effect_dice="1d10",
        cantrip_scaling=ELDRITCH_BLAST_SCALING,
    )


# ---------------------------------------------------------------------------
# Seed tests
# ---------------------------------------------------------------------------

class EldritchBlastSeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app.services.seed_paths import resolve_base_seed_path
        seed_path = resolve_base_seed_path(__file__, "base_spells.seed.json")
        with open(seed_path) as f:
            raw = json.load(f)
        spells = raw["spells"] if isinstance(raw, dict) else raw
        cls.entry = next(
            (s for s in spells if isinstance(s, dict) and s.get("canonicalKey") == "eldritch_blast"),
            None,
        )

    def test_entry_exists(self):
        self.assertIsNotNone(self.entry, "eldritch_blast not found in seed")

    def test_contract_fields(self):
        e = self.entry
        self.assertEqual(e["level"], 0)
        self.assertEqual(e["school"], "evocation")
        self.assertEqual(e["castingTimeType"], "action")
        self.assertEqual(e["rangeMeters"], 36)
        self.assertEqual(e["attackType"], "ranged_spell")
        self.assertEqual(e["damageDice"], "1d10")
        self.assertEqual(e["damageType"], "Force")
        self.assertFalse(e["concentration"])

    def test_cantrip_scaling_is_effect_instances(self):
        cs = self.entry.get("cantripScaling")
        self.assertIsNotNone(cs)
        self.assertEqual(cs["scalingMode"], "character_level")
        self.assertEqual(cs["scalingEffectType"], "effect_instances")

    def test_cantrip_scaling_thresholds(self):
        thresholds = self.entry["cantripScaling"]["thresholds"]
        by_level = {t["characterLevel"]: t for t in thresholds}
        self.assertEqual(by_level[1]["instances"], 1)
        self.assertEqual(by_level[5]["instances"], 2)
        self.assertEqual(by_level[11]["instances"], 3)
        self.assertEqual(by_level[17]["instances"], 4)
        for t in thresholds:
            self.assertEqual(t["instanceDamage"]["dice"], "1d10")

    def test_no_upcast(self):
        self.assertIsNone(self.entry.get("upcast"))

    def test_no_double_scaling(self):
        has_cantrip_scaling = self.entry.get("cantripScaling") is not None
        has_any_upcast = any(self.entry.get(k) for k in ("upcast", "upcastJson", "upcast_json"))
        self.assertTrue(has_cantrip_scaling)
        self.assertFalse(has_any_upcast)


# ---------------------------------------------------------------------------
# Cantrip scaling: instance count
# ---------------------------------------------------------------------------

class EldritchBlastInstanceScalingTests(unittest.TestCase):
    def test_level_1_gives_1_instance(self):
        result = _apply(1)
        self.assertEqual(result["cantrip_instance_count"], 1)
        self.assertEqual(result["cantrip_instance_dice"], "1d10")

    def test_level_4_gives_1_instance(self):
        result = _apply(4)
        self.assertEqual(result["cantrip_instance_count"], 1)

    def test_level_5_gives_2_instances(self):
        result = _apply(5)
        self.assertEqual(result["cantrip_instance_count"], 2)
        self.assertEqual(result["cantrip_instance_dice"], "1d10")

    def test_level_10_gives_2_instances(self):
        result = _apply(10)
        self.assertEqual(result["cantrip_instance_count"], 2)

    def test_level_11_gives_3_instances(self):
        result = _apply(11)
        self.assertEqual(result["cantrip_instance_count"], 3)

    def test_level_16_gives_3_instances(self):
        result = _apply(16)
        self.assertEqual(result["cantrip_instance_count"], 3)

    def test_level_17_gives_4_instances(self):
        result = _apply(17)
        self.assertEqual(result["cantrip_instance_count"], 4)

    def test_level_20_gives_4_instances(self):
        result = _apply(20)
        self.assertEqual(result["cantrip_instance_count"], 4)

    def test_leveled_spell_does_not_cantrip_scale(self):
        result = CombatSpellDiceMathMixin._apply_character_level_cantrip_scaling(
            spell_level=1,
            caster_level=17,
            effect_dice="1d10",
            cantrip_scaling=ELDRITCH_BLAST_SCALING,
        )
        self.assertIsNone(result["cantrip_instance_count"])

    def test_none_caster_level_does_not_scale(self):
        result = CombatSpellDiceMathMixin._apply_character_level_cantrip_scaling(
            spell_level=0,
            caster_level=None,
            effect_dice="1d10",
            cantrip_scaling=ELDRITCH_BLAST_SCALING,
        )
        self.assertIsNone(result["cantrip_instance_count"])


# ---------------------------------------------------------------------------
# Distinction from fire_bolt (damage_dice)
# ---------------------------------------------------------------------------

class EldritchBlastVsFireBoltTests(unittest.TestCase):
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

    def _fire_bolt(self, level):
        return CombatSpellDiceMathMixin._apply_character_level_cantrip_scaling(
            spell_level=0, caster_level=level, effect_dice="1d10",
            cantrip_scaling=self.FIRE_BOLT_SCALING,
        )

    def test_fire_bolt_level5_no_instances(self):
        result = self._fire_bolt(5)
        self.assertIsNone(result["cantrip_instance_count"])
        self.assertIsNone(result["cantrip_instance_dice"])

    def test_eldritch_blast_level5_has_instances(self):
        result = _apply(5)
        self.assertEqual(result["cantrip_instance_count"], 2)
        self.assertEqual(result["cantrip_instance_dice"], "1d10")

    def test_instance_dice_is_always_single_beam(self):
        """Each beam is always 1d10, even at higher levels."""
        for level in [5, 11, 17]:
            result = _apply(level)
            self.assertEqual(result["cantrip_instance_dice"], "1d10")
