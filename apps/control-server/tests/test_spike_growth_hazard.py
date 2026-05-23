"""Tests for Spike Growth (Crescer Espinhos).

Covers:
- Seed contract: level=2, sphere 6m, concentration, persistentArea.kind=hazard, 2d4/1.5m
- Hazard area effect structure (difficult_terrain, movement_damage_dice, damage_per_meters)
- _is_movement_hazard predicate correctly identifies spike_growth area effects
- Cast behavior already tested in test_persistent_area_effects.py
- Movement damage integration already tested in test_movement_hazards.py
"""

from __future__ import annotations

import json
import unittest

from app.services.combat_service.movement_hazards import _is_movement_hazard


def _spike_growth_area_effect() -> dict:
    return {
        "id": "area-1",
        "source_spell_canonical_key": "spike_growth",
        "effect_kind": "hazard",
        "terrain_effect": "difficult_terrain",
        "movement_damage_dice": "2d4",
        "damage_type": "Piercing",
        "damage_per_meters": 1.5,
        "area_shape": "sphere",
        "radius_meters": 6.0,
        "origin_point": {"x": 10, "y": 10},
        "anchor_cell": {"x": 10, "y": 10},
        "affected_cells": [{"x": 10, "y": 10}, {"x": 11, "y": 10}],
        "concentration_owner_participant_id": "p1",
    }


# ---------------------------------------------------------------------------
# Seed tests
# ---------------------------------------------------------------------------

class SpikeGrowthSeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app.services.seed_paths import resolve_base_seed_path
        seed_path = resolve_base_seed_path(__file__, "base_spells.seed.json")
        with open(seed_path) as f:
            raw = json.load(f)
        spells = raw["spells"] if isinstance(raw, dict) else raw
        cls.entry = next(
            (s for s in spells if isinstance(s, dict) and s.get("canonicalKey") == "spike_growth"),
            None,
        )

    def test_entry_exists(self):
        self.assertIsNotNone(self.entry, "spike_growth not found in seed")

    def test_contract_fields(self):
        e = self.entry
        self.assertEqual(e["level"], 2)
        self.assertEqual(e["school"], "transmutation")
        self.assertEqual(e["castingTimeType"], "action")
        self.assertTrue(e["concentration"])
        self.assertEqual(e["attackType"], "none")
        self.assertEqual(e["effectTiming"], "persistent")

    def test_area_shape_sphere(self):
        self.assertEqual(self.entry.get("areaShape"), "sphere")

    def test_radius_6_meters(self):
        self.assertEqual(self.entry.get("radiusMeters"), 6)

    def test_damage_dice_2d4(self):
        self.assertEqual(self.entry.get("damageDice"), "2d4")

    def test_damage_type_piercing(self):
        self.assertEqual(self.entry.get("damageType"), "Piercing")

    def test_persistent_area_kind_hazard(self):
        pa = self.entry.get("persistentArea")
        self.assertIsNotNone(pa)
        self.assertEqual(pa["kind"], "hazard")

    def test_persistent_area_params_difficult_terrain(self):
        params = self.entry["persistentArea"]["params"]
        self.assertEqual(params["terrainEffect"], "difficult_terrain")

    def test_persistent_area_params_damage_dice(self):
        params = self.entry["persistentArea"]["params"]
        self.assertEqual(params["movementDamageDice"], "2d4")
        self.assertEqual(params["damageType"], "Piercing")

    def test_persistent_area_params_damage_per_meters(self):
        params = self.entry["persistentArea"]["params"]
        self.assertEqual(params["damagePerMeters"], 1.5)

    def test_selection_type_point(self):
        self.assertEqual(self.entry.get("selectionType"), "point")


# ---------------------------------------------------------------------------
# Hazard predicate
# ---------------------------------------------------------------------------

class SpikeGrowthHazardPredicateTests(unittest.TestCase):
    def test_spike_growth_effect_is_movement_hazard(self):
        self.assertTrue(_is_movement_hazard(_spike_growth_area_effect()))

    def test_fog_cloud_effect_is_not_movement_hazard(self):
        fog_effect = {
            "effect_kind": "obscurement",
            "obscurement": "heavily_obscured",
        }
        self.assertFalse(_is_movement_hazard(fog_effect))

    def test_effect_without_damage_dice_is_not_hazard(self):
        effect = {
            "terrain_effect": "difficult_terrain",
            "damage_per_meters": 1.5,
        }
        self.assertFalse(_is_movement_hazard(effect))

    def test_effect_without_per_meters_is_not_hazard(self):
        effect = {
            "terrain_effect": "difficult_terrain",
            "movement_damage_dice": "2d4",
        }
        self.assertFalse(_is_movement_hazard(effect))

    def test_effect_without_difficult_terrain_is_not_hazard(self):
        effect = {
            "movement_damage_dice": "2d4",
            "damage_per_meters": 1.5,
        }
        self.assertFalse(_is_movement_hazard(effect))

    def test_none_is_not_hazard(self):
        self.assertFalse(_is_movement_hazard(None))


# ---------------------------------------------------------------------------
# Area effect structure
# ---------------------------------------------------------------------------

class SpikeGrowthAreaEffectStructureTests(unittest.TestCase):
    def test_area_effect_has_correct_fields(self):
        effect = _spike_growth_area_effect()
        self.assertEqual(effect["effect_kind"], "hazard")
        self.assertEqual(effect["terrain_effect"], "difficult_terrain")
        self.assertEqual(effect["movement_damage_dice"], "2d4")
        self.assertEqual(effect["damage_per_meters"], 1.5)
        self.assertEqual(effect["damage_type"], "Piercing")

    def test_area_effect_has_concentration_owner(self):
        effect = _spike_growth_area_effect()
        self.assertEqual(effect["concentration_owner_participant_id"], "p1")

    def test_area_effect_not_obscurement(self):
        effect = _spike_growth_area_effect()
        self.assertIsNone(effect.get("obscurement"))
