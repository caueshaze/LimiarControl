"""Cantrip scaling tests.

Covers:
  - damage_dice scalingEffectType (Acid Splash pattern)
  - effect_instances scalingEffectType (Eldritch Blast pattern)
  - Legacy "mode" field backward compatibility
  - Magic Missile upcast regression (no cantripScaling)
  - Dice math resolver for both effect types
"""

from __future__ import annotations

import unittest

from app.schemas.base_spell import BaseSpellCreate, SpellCantripScalingConfig
from app.models.base_spell import SpellSchool
from app.services.combat_service.spell_dice_math import CombatSpellDiceMathMixin


class CantripScalingSchemaTests(unittest.TestCase):
    def _make_cantrip(self, **overrides):
        defaults = {
            "canonicalKey": "acid_splash",
            "nameEn": "Acid Splash",
            "descriptionEn": "Hurl a bubble of acid.",
            "level": 0,
            "school": SpellSchool.CONJURATION,
            "resolutionType": "damage",
            "damageDice": "1d6",
            "damageType": "Acid",
            "savingThrow": "DEX",
            "saveSuccessOutcome": "none",
        }
        defaults.update(overrides)
        return BaseSpellCreate(**defaults)

    # --- damage_dice ---

    def test_damage_dice_type_accepted(self):
        spell = self._make_cantrip(
            cantripScaling={
                "scalingMode": "character_level",
                "scalingEffectType": "damage_dice",
                "thresholds": [
                    {"characterLevel": 1, "damage": {"dice": "1d6"}},
                    {"characterLevel": 5, "damage": {"dice": "2d6"}},
                    {"characterLevel": 11, "damage": {"dice": "3d6"}},
                    {"characterLevel": 17, "damage": {"dice": "4d6"}},
                ],
            }
        )
        cs = spell.cantripScaling
        self.assertIsInstance(cs, SpellCantripScalingConfig)
        self.assertEqual(cs.scalingMode, "character_level")
        self.assertEqual(cs.scalingEffectType, "damage_dice")
        self.assertEqual(len(cs.thresholds), 4)
        self.assertEqual(cs.thresholds[2].damage.dice, "3d6")

    def test_legacy_mode_field_normalizes_to_scaling_mode(self):
        spell = self._make_cantrip(
            cantripScaling={
                "mode": "character_level",
                "thresholds": [
                    {"characterLevel": 1, "damage": {"dice": "1d6"}},
                    {"characterLevel": 5, "damage": {"dice": "2d6"}},
                ],
            }
        )
        cs = spell.cantripScaling
        self.assertEqual(cs.scalingMode, "character_level")
        self.assertEqual(cs.scalingEffectType, "damage_dice")

    def test_damage_dice_threshold_missing_damage_raises(self):
        with self.assertRaises(ValueError):
            self._make_cantrip(
                cantripScaling={
                    "scalingMode": "character_level",
                    "scalingEffectType": "damage_dice",
                    "thresholds": [
                        {"characterLevel": 1, "instances": 1, "instanceDamage": {"dice": "1d6"}},
                    ],
                }
            )

    # --- effect_instances ---

    def test_effect_instances_type_accepted(self):
        spell = self._make_cantrip(
            canonicalKey="eldritch_blast",
            nameEn="Eldritch Blast",
            descriptionEn="A beam of crackling energy.",
            damageDice="1d10",
            damageType="Force",
            savingThrow=None,
            saveSuccessOutcome=None,
            cantripScaling={
                "scalingMode": "character_level",
                "scalingEffectType": "effect_instances",
                "thresholds": [
                    {"characterLevel": 1, "instances": 1, "instanceDamage": {"dice": "1d10"}},
                    {"characterLevel": 5, "instances": 2, "instanceDamage": {"dice": "1d10"}},
                    {"characterLevel": 11, "instances": 3, "instanceDamage": {"dice": "1d10"}},
                    {"characterLevel": 17, "instances": 4, "instanceDamage": {"dice": "1d10"}},
                ],
            },
        )
        cs = spell.cantripScaling
        self.assertIsInstance(cs, SpellCantripScalingConfig)
        self.assertEqual(cs.scalingEffectType, "effect_instances")
        self.assertEqual(cs.thresholds[1].instances, 2)
        self.assertEqual(cs.thresholds[1].instanceDamage.dice, "1d10")

    def test_effect_instances_inferred_when_scalingEffectType_absent(self):
        spell = self._make_cantrip(
            damageDice="1d10",
            cantripScaling={
                "scalingMode": "character_level",
                "thresholds": [
                    {"characterLevel": 1, "instances": 1, "instanceDamage": {"dice": "1d10"}},
                ],
            },
        )
        self.assertEqual(spell.cantripScaling.scalingEffectType, "effect_instances")

    def test_effect_instances_threshold_missing_fields_raises(self):
        with self.assertRaises(ValueError):
            self._make_cantrip(
                cantripScaling={
                    "scalingMode": "character_level",
                    "scalingEffectType": "effect_instances",
                    "thresholds": [
                        {"characterLevel": 1, "damage": {"dice": "1d10"}},
                    ],
                }
            )

    def test_effect_instances_instances_must_be_positive(self):
        with self.assertRaises(ValueError):
            self._make_cantrip(
                cantripScaling={
                    "scalingMode": "character_level",
                    "scalingEffectType": "effect_instances",
                    "thresholds": [
                        {"characterLevel": 1, "instances": 0, "instanceDamage": {"dice": "1d10"}},
                    ],
                }
            )

    # --- Threshold ordering ---

    def test_unsorted_thresholds_raise(self):
        with self.assertRaises(ValueError):
            self._make_cantrip(
                cantripScaling={
                    "scalingMode": "character_level",
                    "scalingEffectType": "damage_dice",
                    "thresholds": [
                        {"characterLevel": 5, "damage": {"dice": "2d6"}},
                        {"characterLevel": 1, "damage": {"dice": "1d6"}},
                    ],
                }
            )

    def test_duplicate_character_levels_raise(self):
        with self.assertRaises(ValueError):
            self._make_cantrip(
                cantripScaling={
                    "scalingMode": "character_level",
                    "scalingEffectType": "damage_dice",
                    "thresholds": [
                        {"characterLevel": 1, "damage": {"dice": "1d6"}},
                        {"characterLevel": 1, "damage": {"dice": "2d6"}},
                    ],
                }
            )


class CantripScalingDiceMathTests(unittest.TestCase):
    """Tests for _apply_character_level_cantrip_scaling."""

    def _apply(self, spell_level, caster_level, effect_dice, cantrip_scaling):
        result = CombatSpellDiceMathMixin._apply_character_level_cantrip_scaling(
            spell_level=spell_level,
            caster_level=caster_level,
            effect_dice=effect_dice,
            cantrip_scaling=cantrip_scaling,
        )
        return result["effect_dice"]

    def _apply_full(self, spell_level, caster_level, effect_dice, cantrip_scaling):
        return CombatSpellDiceMathMixin._apply_character_level_cantrip_scaling(
            spell_level=spell_level,
            caster_level=caster_level,
            effect_dice=effect_dice,
            cantrip_scaling=cantrip_scaling,
        )

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

    # Acid Splash

    def test_acid_splash_level_1_resolves_1d6(self):
        result = self._apply(0, 1, "1d6", self.ACID_SPLASH_SCALING)
        self.assertEqual(result, "1d6")

    def test_acid_splash_level_4_resolves_1d6(self):
        result = self._apply(0, 4, "1d6", self.ACID_SPLASH_SCALING)
        self.assertEqual(result, "1d6")

    def test_acid_splash_level_5_resolves_2d6(self):
        result = self._apply(0, 5, "1d6", self.ACID_SPLASH_SCALING)
        self.assertEqual(result, "2d6")

    def test_acid_splash_level_11_resolves_3d6(self):
        result = self._apply(0, 11, "1d6", self.ACID_SPLASH_SCALING)
        self.assertEqual(result, "3d6")

    def test_acid_splash_level_17_resolves_4d6(self):
        result = self._apply(0, 17, "1d6", self.ACID_SPLASH_SCALING)
        self.assertEqual(result, "4d6")

    def test_acid_splash_level_20_resolves_4d6(self):
        result = self._apply(0, 20, "1d6", self.ACID_SPLASH_SCALING)
        self.assertEqual(result, "4d6")

    def test_acid_splash_does_not_use_upcast(self):
        result = self._apply(0, 5, "1d6", self.ACID_SPLASH_SCALING)
        self.assertNotEqual(result, "1d6")

    # Eldritch Blast

    def test_eldritch_blast_level_1_aggregate_1d10(self):
        result = self._apply(0, 1, "1d10", self.ELDRITCH_BLAST_SCALING)
        self.assertEqual(result, "1d10")

    def test_eldritch_blast_level_5_aggregate_2d10(self):
        result = self._apply(0, 5, "1d10", self.ELDRITCH_BLAST_SCALING)
        self.assertEqual(result, "2d10")

    def test_eldritch_blast_level_11_aggregate_3d10(self):
        result = self._apply(0, 11, "1d10", self.ELDRITCH_BLAST_SCALING)
        self.assertEqual(result, "3d10")

    def test_eldritch_blast_level_17_aggregate_4d10(self):
        result = self._apply(0, 17, "1d10", self.ELDRITCH_BLAST_SCALING)
        self.assertEqual(result, "4d10")

    def test_cantrip_scaling_not_applied_to_leveled_spell(self):
        result = self._apply(1, 5, "1d6", self.ACID_SPLASH_SCALING)
        self.assertEqual(result, "1d6")

    def test_cantrip_scaling_not_applied_when_caster_level_none(self):
        result = self._apply(0, None, "1d6", self.ACID_SPLASH_SCALING)
        self.assertEqual(result, "1d6")

    # get_structured_cantrip_scaling normalization

    def test_get_structured_normalizes_legacy_mode(self):
        raw = {
            "mode": "character_level",
            "thresholds": [
                {"characterLevel": 1, "damage": {"dice": "1d6"}},
            ],
        }
        result = CombatSpellDiceMathMixin._get_structured_cantrip_scaling(raw)
        self.assertIsNotNone(result)
        self.assertEqual(result["scalingMode"], "character_level")
        self.assertEqual(result["scalingEffectType"], "damage_dice")

    # --- cantrip_instance_count / cantrip_instance_dice in return dict ---

    def test_eldritch_blast_level_1_instance_count_is_1(self):
        result = self._apply_full(0, 1, "1d10", self.ELDRITCH_BLAST_SCALING)
        self.assertEqual(result["cantrip_instance_count"], 1)
        self.assertEqual(result["cantrip_instance_dice"], "1d10")

    def test_eldritch_blast_level_5_instance_count_is_2(self):
        result = self._apply_full(0, 5, "1d10", self.ELDRITCH_BLAST_SCALING)
        self.assertEqual(result["cantrip_instance_count"], 2)
        self.assertEqual(result["cantrip_instance_dice"], "1d10")

    def test_eldritch_blast_level_11_instance_count_is_3(self):
        result = self._apply_full(0, 11, "1d10", self.ELDRITCH_BLAST_SCALING)
        self.assertEqual(result["cantrip_instance_count"], 3)

    def test_eldritch_blast_level_17_instance_count_is_4(self):
        result = self._apply_full(0, 17, "1d10", self.ELDRITCH_BLAST_SCALING)
        self.assertEqual(result["cantrip_instance_count"], 4)

    def test_acid_splash_has_no_instance_metadata(self):
        result = self._apply_full(0, 5, "1d6", self.ACID_SPLASH_SCALING)
        self.assertIsNone(result["cantrip_instance_count"])
        self.assertIsNone(result["cantrip_instance_dice"])

    def test_no_scaling_returns_none_instance_metadata(self):
        result = self._apply_full(0, 5, "1d6", None)
        self.assertIsNone(result["cantrip_instance_count"])
        self.assertIsNone(result["cantrip_instance_dice"])

    def test_leveled_spell_returns_none_instance_metadata(self):
        result = self._apply_full(1, 5, "1d10", self.ELDRITCH_BLAST_SCALING)
        self.assertIsNone(result["cantrip_instance_count"])
        self.assertIsNone(result["cantrip_instance_dice"])

    # --- effectInstanceCount resolution logic ---

    def test_effect_instance_count_cantrip_effect_instances(self):
        """Cantrip effect_instances: effectInstanceCount = cantrip_instance_count."""
        result = self._apply_full(0, 5, "1d10", self.ELDRITCH_BLAST_SCALING)
        cantrip_instance_count = result["cantrip_instance_count"]
        cantrip_instance_dice = result["cantrip_instance_dice"]
        # Mirrors _build_spell_context_response logic
        effect_instance_count = cantrip_instance_count if cantrip_instance_count is not None else 1
        effect_instance_dice = cantrip_instance_dice
        self.assertEqual(effect_instance_count, 2)
        self.assertEqual(effect_instance_dice, "1d10")

    def test_effect_instance_count_upcast_instances(self):
        """Leveled upcast with additional_effect_instances: effectInstanceCount = base + added."""
        structured = CombatSpellDiceMathMixin._get_structured_spell_upcast({
            "mode": "additional_effect_instances",
            "dice": "1d4+1",
            "perLevel": 1,
            "baseEffectInstances": 3,
        })
        upcast_result = CombatSpellDiceMathMixin._apply_structured_spell_upcast(
            spell_level=1,
            slot_level=3,
            effect_kind="damage",
            effect_dice="3d4+3",
            effect_bonus=3,
            upcast=structured,
        )
        base = structured["baseEffectInstances"]
        added = upcast_result["upcast_added_instances"]
        effect_instance_count = base + added
        effect_instance_dice = structured["dice"]
        self.assertEqual(effect_instance_count, 5)
        self.assertEqual(effect_instance_dice, "1d4+1")

    def test_effect_instance_count_no_instances_defaults_to_1(self):
        """Non-instance spell: effectInstanceCount = 1, effectInstanceDice = None."""
        result = self._apply_full(0, 5, "3d8", self.ACID_SPLASH_SCALING)
        cantrip_instance_count = result["cantrip_instance_count"]
        effect_instance_count = cantrip_instance_count if cantrip_instance_count is not None else 1
        self.assertEqual(effect_instance_count, 1)
        self.assertIsNone(result["cantrip_instance_dice"])

    # --- get_structured_cantrip_scaling normalization ---

    def test_get_structured_preserves_effect_instances(self):
        raw = {
            "scalingMode": "character_level",
            "scalingEffectType": "effect_instances",
            "thresholds": [
                {"characterLevel": 1, "instances": 1, "instanceDamage": {"dice": "1d10"}},
                {"characterLevel": 5, "instances": 2, "instanceDamage": {"dice": "1d10"}},
            ],
        }
        result = CombatSpellDiceMathMixin._get_structured_cantrip_scaling(raw)
        self.assertIsNotNone(result)
        self.assertEqual(result["scalingEffectType"], "effect_instances")
        self.assertEqual(result["thresholds"][1]["instances"], 2)


class EffectInstanceCountTests(unittest.TestCase):
    """Tests for effectInstanceCount derivation for leveled instance-upcast spells.

    Covers the Magic Missile contract:
      - slot 1: effectInstanceCount = 3, effectInstanceDice = "1d4+1"
      - slot 2: effectInstanceCount = 4, upcast_added_instances = 1
      - slot 3: effectInstanceCount = 5, upcast_added_instances = 2
    """

    MM_RAW_UPCAST = {
        "mode": "additional_effect_instances",
        "dice": "1d4+1",
        "perLevel": 1,
        "baseEffectInstances": 3,
    }

    def _structured(self, raw=None):
        return CombatSpellDiceMathMixin._get_structured_spell_upcast(raw or self.MM_RAW_UPCAST)

    def _apply_upcast(self, slot_level, structured=None):
        return CombatSpellDiceMathMixin._apply_structured_spell_upcast(
            spell_level=1,
            slot_level=slot_level,
            effect_kind="damage",
            effect_dice="3d4+3",
            effect_bonus=3,
            upcast=structured or self._structured(),
        )

    def _effect_instance_count(self, structured, upcast_result):
        """Mirror the effectInstanceCount logic in _build_spell_context_response."""
        base = structured.get("baseEffectInstances") if isinstance(structured, dict) else None
        added = upcast_result.get("upcast_added_instances", 0)
        return (base + added) if base is not None else 1

    # --- get_structured passes through baseEffectInstances ---

    def test_get_structured_passes_base_effect_instances(self):
        structured = self._structured()
        self.assertEqual(structured["baseEffectInstances"], 3)
        self.assertEqual(structured["dice"], "1d4+1")

    def test_get_structured_without_base_effect_instances_omits_key(self):
        raw = {"mode": "additional_effect_instances", "dice": "1d6", "perLevel": 1}
        structured = CombatSpellDiceMathMixin._get_structured_spell_upcast(raw)
        self.assertNotIn("baseEffectInstances", structured)

    # --- Magic Missile slot 1 (no upcast) ---

    def test_magic_missile_slot_1_instance_count(self):
        structured = self._structured()
        upcast_result = self._apply_upcast(1, structured)
        self.assertEqual(self._effect_instance_count(structured, upcast_result), 3)
        self.assertEqual(upcast_result["upcast_added_instances"], 0)

    def test_magic_missile_slot_1_instance_dice(self):
        self.assertEqual(self._structured()["dice"], "1d4+1")

    def test_magic_missile_slot_1_aggregate_dice_unchanged(self):
        upcast_result = self._apply_upcast(1)
        self.assertEqual(upcast_result["effect_dice"], "3d4+3")
        self.assertFalse(upcast_result["upcast_applied"])

    # --- Magic Missile slot 2 ---

    def test_magic_missile_slot_2_instance_count(self):
        structured = self._structured()
        upcast_result = self._apply_upcast(2, structured)
        self.assertEqual(self._effect_instance_count(structured, upcast_result), 4)
        self.assertEqual(upcast_result["upcast_added_instances"], 1)

    def test_magic_missile_slot_2_aggregate_dice(self):
        upcast_result = self._apply_upcast(2)
        self.assertEqual(upcast_result["effect_dice"], "4d4+4")

    # --- Magic Missile slot 3 ---

    def test_magic_missile_slot_3_instance_count(self):
        structured = self._structured()
        upcast_result = self._apply_upcast(3, structured)
        self.assertEqual(self._effect_instance_count(structured, upcast_result), 5)
        self.assertEqual(upcast_result["upcast_added_instances"], 2)

    def test_magic_missile_slot_3_aggregate_dice(self):
        upcast_result = self._apply_upcast(3)
        self.assertEqual(upcast_result["effect_dice"], "5d4+5")

    def test_magic_missile_slot_3_instance_effect_dice(self):
        upcast_result = self._apply_upcast(3)
        self.assertEqual(upcast_result["upcast_instance_effect_dice"], "1d4+1")

    # --- Spells without baseEffectInstances fall back to 1 ---

    def test_spell_without_base_instances_falls_back_to_1(self):
        raw = {"mode": "additional_effect_instances", "dice": "1d6", "perLevel": 1}
        structured = CombatSpellDiceMathMixin._get_structured_spell_upcast(raw)
        upcast_result = CombatSpellDiceMathMixin._apply_structured_spell_upcast(
            spell_level=1, slot_level=3, effect_kind="damage",
            effect_dice="1d6", effect_bonus=0, upcast=structured,
        )
        self.assertEqual(self._effect_instance_count(structured, upcast_result), 1)

    # --- Schema validation ---

    def test_base_effect_instances_only_for_instance_mode(self):
        with self.assertRaises(ValueError):
            BaseSpellCreate(
                canonicalKey="fireball",
                nameEn="Fireball",
                descriptionEn="A bright streak flashes from your pointing finger.",
                level=3,
                school=SpellSchool.EVOCATION,
                resolutionType="damage",
                damageDice="8d6",
                damageType="Fire",
                savingThrow="DEX",
                saveSuccessOutcome="half_damage",
                upcast={
                    "mode": "extra_damage_dice",
                    "dice": "1d6",
                    "perLevel": 1,
                    "baseEffectInstances": 1,
                },
            )


class MagicMissileRegressionTests(unittest.TestCase):
    """Magic Missile must keep using upcast, not cantripScaling."""

    def test_magic_missile_has_no_cantrip_scaling(self):
        spell = BaseSpellCreate(
            canonicalKey="magic_missile",
            nameEn="Magic Missile",
            descriptionEn="Three glowing darts of magical force.",
            level=1,
            school=SpellSchool.EVOCATION,
            resolutionType="damage",
            damageDice="3d4+3",
            damageType="Force",
            upcast={
                "mode": "additional_effect_instances",
                "dice": "1d4+1",
                "perLevel": 1,
                "baseEffectInstances": 3,
            },
        )
        self.assertIsNone(spell.cantripScaling)
        self.assertIsNotNone(spell.upcast)
        self.assertEqual(spell.upcast.mode, "additional_effect_instances")
        self.assertEqual(spell.upcast.baseEffectInstances, 3)

    def test_magic_missile_upcast_slot_3_adds_2_instances(self):
        result = CombatSpellDiceMathMixin._apply_structured_spell_upcast(
            spell_level=1,
            slot_level=3,
            effect_kind="damage",
            effect_dice="3d4+3",
            effect_bonus=3,
            upcast={
                "mode": "additional_effect_instances",
                "dice": "1d4+1",
                "perLevel": 1,
                "baseEffectInstances": 3,
            },
        )
        # 2 extra levels → 2 extra instances, aggregate adds 2d4+2
        self.assertEqual(result["upcast_added_instances"], 2)
        self.assertEqual(result["upcast_instance_effect_dice"], "1d4+1")
        self.assertTrue(result["upcast_applied"])


if __name__ == "__main__":
    unittest.main()
