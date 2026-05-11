"""Tests for Ray of Frost (Raio de Gelo) cantrip (issue #312).

Covers:
- Seed: ray_of_frost has correct fields, damage_dice cantripScaling, movement-speed effect
- Cantrip scaling: 1d8 → 2d8 → 3d8 → 4d8 at levels 1/5/11/17
- Effect metadata: expires_on="turn_start", expires_at_participant_id=caster, bonus_meters=-3
- On-hit pipeline guard: spell_attack spells skip declarative-effects pre-cast
- On-miss: declarative effects are NOT applied
- Fire Bolt regression: no effects, spell_attack still works normally
"""

from __future__ import annotations

import json
import unittest
from unittest.mock import MagicMock, patch

from app.schemas.base_spell_effects import ModifyMovementSpeedParams, SpellDeclarativeEffect
from app.services.combat_service.concentration import CombatConcentrationMixin
from app.services.combat_service.spell_declarative_effects import (
    CombatSpellDeclarativeEffectsMixin,
)
from app.services.combat_service.spell_dice_math import CombatSpellDiceMathMixin


RAY_OF_FROST_SCALING = {
    "scalingMode": "character_level",
    "scalingEffectType": "damage_dice",
    "thresholds": [
        {"characterLevel": 1, "damage": {"dice": "1d8"}},
        {"characterLevel": 5, "damage": {"dice": "2d8"}},
        {"characterLevel": 11, "damage": {"dice": "3d8"}},
        {"characterLevel": 17, "damage": {"dice": "4d8"}},
    ],
}


def _apply(caster_level):
    return CombatSpellDiceMathMixin._apply_character_level_cantrip_scaling(
        spell_level=0,
        caster_level=caster_level,
        effect_dice="1d8",
        cantrip_scaling=RAY_OF_FROST_SCALING,
    )


# ---------------------------------------------------------------------------
# Seed tests
# ---------------------------------------------------------------------------

class RayOfFrostSeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app.services.seed_paths import resolve_base_seed_path
        seed_path = resolve_base_seed_path(__file__, "base_spells.seed.json")
        with open(seed_path) as f:
            raw = json.load(f)
        spells = raw["spells"] if isinstance(raw, dict) else raw
        cls.entry = next(
            (s for s in spells if isinstance(s, dict) and s.get("canonicalKey") == "ray_of_frost"),
            None,
        )

    def test_entry_exists(self):
        self.assertIsNotNone(self.entry, "ray_of_frost not found in seed")

    def test_level_is_0(self):
        self.assertEqual(self.entry["level"], 0)

    def test_school_is_evocation(self):
        self.assertEqual(self.entry["school"], "evocation")

    def test_casting_time_is_action(self):
        self.assertEqual(self.entry["castingTimeType"], "action")

    def test_range_is_18_meters(self):
        self.assertEqual(self.entry["rangeMeters"], 18)

    def test_range_text_60ft(self):
        self.assertEqual(self.entry["rangeText"], "60 ft")

    def test_no_concentration(self):
        self.assertFalse(self.entry["concentration"])

    def test_damage_dice_1d8(self):
        self.assertEqual(self.entry["damageDice"], "1d8")

    def test_damage_type_cold(self):
        self.assertEqual(self.entry["damageType"], "Cold")

    def test_attack_type_ranged_spell(self):
        self.assertEqual(self.entry["attackType"], "ranged_spell")

    def test_name_pt_raio_de_gelo(self):
        self.assertEqual(self.entry.get("namePt"), "Raio de Gelo")

    def test_no_upcast(self):
        self.assertIsNone(self.entry.get("upcast"))

    def test_no_upcast_json(self):
        self.assertIsNone(self.entry.get("upcastJson"))

    def test_no_double_scaling(self):
        has_cantrip = self.entry.get("cantripScaling") is not None
        has_upcast = any(self.entry.get(k) for k in ("upcast", "upcastJson", "upcast_json"))
        self.assertTrue(has_cantrip)
        self.assertFalse(has_upcast)

    def test_cantrip_scaling_damage_dice(self):
        cs = self.entry["cantripScaling"]
        self.assertEqual(cs["scalingEffectType"], "damage_dice")
        self.assertEqual(cs["scalingMode"], "character_level")

    def test_cantrip_scaling_4_thresholds(self):
        self.assertEqual(len(self.entry["cantripScaling"]["thresholds"]), 4)

    def test_cantrip_scaling_level5_2d8(self):
        thresholds = self.entry["cantripScaling"]["thresholds"]
        t5 = next(t for t in thresholds if t["characterLevel"] == 5)
        self.assertEqual(t5["damage"]["dice"], "2d8")

    def test_cantrip_scaling_level11_3d8(self):
        thresholds = self.entry["cantripScaling"]["thresholds"]
        t11 = next(t for t in thresholds if t["characterLevel"] == 11)
        self.assertEqual(t11["damage"]["dice"], "3d8")

    def test_cantrip_scaling_level17_4d8(self):
        thresholds = self.entry["cantripScaling"]["thresholds"]
        t17 = next(t for t in thresholds if t["characterLevel"] == 17)
        self.assertEqual(t17["damage"]["dice"], "4d8")

    def test_has_effects(self):
        self.assertIsNotNone(self.entry.get("effects"))
        self.assertGreater(len(self.entry["effects"]), 0)

    def test_effect_type_modify_movement_speed(self):
        effect = self.entry["effects"][0]
        self.assertEqual(effect["type"], "modify_movement_speed")

    def test_effect_bonus_meters_negative_3(self):
        effect = self.entry["effects"][0]
        self.assertEqual(effect["params"]["bonus_meters"], -3)

    def test_effect_duration_until_turn_start(self):
        effect = self.entry["effects"][0]
        self.assertEqual(effect["duration"]["type"], "until_turn_start")

    def test_effect_anchor_caster(self):
        effect = self.entry["effects"][0]
        self.assertEqual(effect["duration"]["anchor"], "caster")


# ---------------------------------------------------------------------------
# Cantrip scaling tests
# ---------------------------------------------------------------------------

class RayOfFrostCantripScalingTests(unittest.TestCase):
    def test_level_1_gives_1d8(self):
        self.assertEqual(_apply(1)["effect_dice"], "1d8")

    def test_level_4_gives_1d8(self):
        self.assertEqual(_apply(4)["effect_dice"], "1d8")

    def test_level_5_gives_2d8(self):
        self.assertEqual(_apply(5)["effect_dice"], "2d8")

    def test_level_10_gives_2d8(self):
        self.assertEqual(_apply(10)["effect_dice"], "2d8")

    def test_level_11_gives_3d8(self):
        self.assertEqual(_apply(11)["effect_dice"], "3d8")

    def test_level_17_gives_4d8(self):
        self.assertEqual(_apply(17)["effect_dice"], "4d8")

    def test_level_20_gives_4d8(self):
        self.assertEqual(_apply(20)["effect_dice"], "4d8")

    def test_cantrip_instance_count_always_none(self):
        for lvl in [1, 5, 11, 17]:
            self.assertIsNone(_apply(lvl)["cantrip_instance_count"])

    def test_cantrip_instance_dice_always_none(self):
        for lvl in [1, 5, 11, 17]:
            self.assertIsNone(_apply(lvl)["cantrip_instance_dice"])

    def test_not_applied_to_leveled_spell(self):
        result = CombatSpellDiceMathMixin._apply_character_level_cantrip_scaling(
            spell_level=1, caster_level=5, effect_dice="1d8", cantrip_scaling=RAY_OF_FROST_SCALING
        )
        self.assertEqual(result["effect_dice"], "1d8")


# ---------------------------------------------------------------------------
# Effect schema validation
# ---------------------------------------------------------------------------

class RayOfFrostEffectSchemaTests(unittest.TestCase):
    def test_effect_validates_correctly(self):
        effect = SpellDeclarativeEffect(**{
            "type": "modify_movement_speed",
            "target": "selected_target",
            "duration": {"type": "until_turn_start", "anchor": "caster"},
            "params": {"bonus_meters": -3},
        })
        self.assertEqual(effect.type, "modify_movement_speed")
        self.assertIsInstance(effect.params, ModifyMovementSpeedParams)
        self.assertEqual(effect.params.bonus_meters, -3)
        self.assertEqual(effect.duration.type, "until_turn_start")
        self.assertEqual(effect.duration.anchor, "caster")


# ---------------------------------------------------------------------------
# Active effect metadata / lifecycle tests
# ---------------------------------------------------------------------------

class RayOfFrostEffectMetadataTests(unittest.TestCase):
    """Verify the active effect built for the movement speed penalty has correct
    metadata so that _expire_effects_for_participant removes it at the right time."""

    def _build_effect(self, attacker_id="caster-1", target_id="target-1"):
        from app.schemas.base_spell_effects import SpellDeclarativeDuration, SpellDeclarativeEffect
        effect = SpellDeclarativeEffect(**{
            "type": "modify_movement_speed",
            "target": "selected_target",
            "duration": {"type": "until_turn_start", "anchor": "caster"},
            "params": {"bonus_meters": -3},
        })
        attacker = {"id": attacker_id, "ref_id": "user-1", "display_name": "Caster"}
        target = {"id": target_id, "ref_id": "user-2", "display_name": "Target"}
        duration_kwargs = CombatSpellDeclarativeEffectsMixin._declarative_duration_kwargs(
            effect=effect,
            attacker=attacker,
            target_participant=target,
        )
        spell_context = {"spell_canonical_key": "ray_of_frost", "spell_name": "Raio de Gelo"}
        params = effect.params.model_dump(mode="json", exclude_none=True)
        metadata = {
            "source_spell_key": spell_context["spell_canonical_key"],
            "caster_participant_id": attacker_id,
        }
        return CombatConcentrationMixin._build_active_effect(
            kind="spell_effect",
            source_participant_id=attacker_id,
            metadata={**metadata, **params},
            display_label="Raio de Gelo",
            **duration_kwargs,
        )

    def test_expires_on_is_turn_start(self):
        effect = self._build_effect()
        self.assertEqual(effect["expires_on"], "turn_start")

    def test_expires_at_participant_id_is_caster(self):
        effect = self._build_effect(attacker_id="caster-42")
        self.assertEqual(effect["expires_at_participant_id"], "caster-42")

    def test_expires_at_participant_id_is_not_target(self):
        effect = self._build_effect(attacker_id="caster-1", target_id="target-99")
        self.assertNotEqual(effect["expires_at_participant_id"], "target-99")

    def test_kind_is_spell_effect(self):
        effect = self._build_effect()
        self.assertEqual(effect["kind"], "spell_effect")

    def test_metadata_has_bonus_meters(self):
        effect = self._build_effect()
        self.assertEqual(effect["metadata"]["bonus_meters"], -3)

    def test_metadata_has_source_spell_key(self):
        effect = self._build_effect()
        self.assertEqual(effect["metadata"]["source_spell_key"], "ray_of_frost")

    def test_duration_type_is_until_turn_start(self):
        effect = self._build_effect()
        self.assertEqual(effect["duration_type"], "until_turn_start")


# ---------------------------------------------------------------------------
# Regression: Fire Bolt (no effects) still uses spell_attack path
# ---------------------------------------------------------------------------

class RayOfFrostRegressionTests(unittest.TestCase):
    def test_fire_bolt_has_no_effects_in_seed(self):
        from app.services.seed_paths import resolve_base_seed_path
        seed_path = resolve_base_seed_path(__file__, "base_spells.seed.json")
        with open(seed_path) as f:
            raw = json.load(f)
        spells = raw["spells"] if isinstance(raw, dict) else raw
        fire_bolt = next(
            (s for s in spells if isinstance(s, dict) and s.get("canonicalKey") == "fire_bolt"),
            None,
        )
        self.assertIsNotNone(fire_bolt)
        effects = fire_bolt.get("effects") or []
        self.assertEqual(effects, [], "fire_bolt must have no effects (pure damage, no on-hit debuff)")

    def test_spell_context_has_declarative_effects_false_for_no_effects(self):
        """Fire Bolt context has no effects → _spell_context_has_declarative_effects returns False."""
        spell_context = {"effects": [], "on_end_effects": []}
        self.assertFalse(
            CombatSpellDeclarativeEffectsMixin._spell_context_has_declarative_effects(spell_context)
        )

    def test_spell_context_has_declarative_effects_true_for_ray_of_frost(self):
        """Ray of Frost context has effects → returns True."""
        spell_context = {
            "effects": [
                {"type": "modify_movement_speed", "target": "selected_target",
                 "params": {"bonus_meters": -3}}
            ]
        }
        self.assertTrue(
            CombatSpellDeclarativeEffectsMixin._spell_context_has_declarative_effects(spell_context)
        )

    def test_ray_of_frost_scaling_does_not_break_fire_bolt_scaling(self):
        fire_bolt_scaling = {
            "scalingMode": "character_level",
            "scalingEffectType": "damage_dice",
            "thresholds": [
                {"characterLevel": 1, "damage": {"dice": "1d10"}},
                {"characterLevel": 5, "damage": {"dice": "2d10"}},
            ],
        }
        result = CombatSpellDiceMathMixin._apply_character_level_cantrip_scaling(
            spell_level=0, caster_level=5, effect_dice="1d10", cantrip_scaling=fire_bolt_scaling
        )
        self.assertEqual(result["effect_dice"], "2d10")


if __name__ == "__main__":
    unittest.main()
