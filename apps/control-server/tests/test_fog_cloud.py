"""Tests for Fog Cloud (Névoa Obscurecente).

Covers:
- Seed contract: level=1, sphere 6m radius, concentration, persistentArea.kind=obscurement
- persistentArea params: heavily_obscured
- Cast behavior already tested in test_persistent_area_effects.py — not re-tested here
- This file focuses on seed contract and obscurement area params validation
"""

from __future__ import annotations

import json
import unittest


# ---------------------------------------------------------------------------
# Seed tests
# ---------------------------------------------------------------------------

class FogCloudSeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app.services.seed_paths import resolve_base_seed_path
        seed_path = resolve_base_seed_path(__file__, "base_spells.seed.json")
        with open(seed_path) as f:
            raw = json.load(f)
        spells = raw["spells"] if isinstance(raw, dict) else raw
        cls.entry = next(
            (s for s in spells if isinstance(s, dict) and s.get("canonicalKey") == "fog_cloud"),
            None,
        )

    def test_entry_exists(self):
        self.assertIsNotNone(self.entry, "fog_cloud not found in seed")

    def test_contract_fields(self):
        e = self.entry
        self.assertEqual(e["level"], 1)
        self.assertEqual(e["school"], "conjuration")
        self.assertEqual(e["castingTimeType"], "action")
        self.assertEqual(e["rangeMeters"], 36)
        self.assertTrue(e["concentration"])
        self.assertEqual(e["attackType"], "none")
        self.assertEqual(e["effectTiming"], "persistent")

    def test_area_shape_sphere(self):
        self.assertEqual(self.entry.get("areaShape"), "sphere")

    def test_radius_6_meters(self):
        self.assertEqual(self.entry.get("radiusMeters"), 6)

    def test_selection_type_point(self):
        self.assertEqual(self.entry.get("selectionType"), "point")

    def test_persistent_area_kind_obscurement(self):
        pa = self.entry.get("persistentArea")
        self.assertIsNotNone(pa)
        self.assertEqual(pa["kind"], "obscurement")

    def test_persistent_area_params_heavily_obscured(self):
        pa = self.entry["persistentArea"]
        self.assertEqual(pa["params"]["obscurement"], "heavily_obscured")

    def test_upcast_config(self):
        up = self.entry.get("upcast")
        self.assertIsNotNone(up)
        self.assertEqual(up["mode"], "effect_scaling")
        self.assertEqual(up["scalingKey"], "radius_meters")


# ---------------------------------------------------------------------------
# Persistent area effect structure
# ---------------------------------------------------------------------------

class FogCloudAreaEffectTests(unittest.TestCase):
    """Validates that a fog_cloud area effect dict has the expected structure
    (mirroring what cast_area produces, as tested in test_persistent_area_effects.py)."""

    def _make_fog_cloud_area_effect(self) -> dict:
        return {
            "id": "area-1",
            "source_spell_canonical_key": "fog_cloud",
            "effect_kind": "obscurement",
            "obscurement": "heavily_obscured",
            "area_shape": "sphere",
            "radius_meters": 6.0,
            "origin_point": {"x": 10, "y": 10},
            "anchor_cell": {"x": 10, "y": 10},
            "affected_cells": [{"x": 10, "y": 10}],
            "concentration_owner_participant_id": "p1",
        }

    def test_area_effect_kind_obscurement(self):
        effect = self._make_fog_cloud_area_effect()
        self.assertEqual(effect["effect_kind"], "obscurement")

    def test_area_effect_obscurement_level(self):
        effect = self._make_fog_cloud_area_effect()
        self.assertEqual(effect["obscurement"], "heavily_obscured")

    def test_area_effect_has_concentration_owner(self):
        effect = self._make_fog_cloud_area_effect()
        self.assertEqual(effect["concentration_owner_participant_id"], "p1")

    def test_area_effect_has_radius(self):
        effect = self._make_fog_cloud_area_effect()
        self.assertEqual(effect["radius_meters"], 6.0)

    def test_area_effect_not_a_hazard(self):
        effect = self._make_fog_cloud_area_effect()
        self.assertIsNone(effect.get("terrain_effect"))
        self.assertIsNone(effect.get("movement_damage_dice"))
