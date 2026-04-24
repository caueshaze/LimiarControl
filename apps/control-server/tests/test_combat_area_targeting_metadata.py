"""Tests for metadata-driven area spell targeting.

Verifies that _resolve_supported_area_spell_spec resolves dimensions from
explicit shape-specific fields (radius_meters, length_meters, side_meters)
and returns None when the expected field is absent.
"""
from __future__ import annotations

import unittest

from app.services.combat import CombatService


class MissingDimensionTests(unittest.TestCase):
    """Verify that spells with an area_shape but missing the corresponding
    explicit dimension field return None — no silent fallback."""

    def test_sphere_without_radius_meters_returns_none(self):
        ctx = {
            "area_shape": "sphere",
            "radius_meters": None,
            "range_meters": 45,
        }
        spec = CombatService._resolve_supported_area_spell_spec(ctx)
        self.assertIsNone(spec)

    def test_cone_without_length_meters_returns_none(self):
        ctx = {
            "area_shape": "cone",
            "length_meters": None,
            "range_meters": 0,
        }
        spec = CombatService._resolve_supported_area_spell_spec(ctx)
        self.assertIsNone(spec)

    def test_cube_without_side_meters_returns_none(self):
        ctx = {
            "area_shape": "cube",
            "side_meters": None,
            "range_meters": 0,
        }
        spec = CombatService._resolve_supported_area_spell_spec(ctx)
        self.assertIsNone(spec)

    def test_cylinder_without_radius_meters_returns_none(self):
        ctx = {
            "area_shape": "cylinder",
            "radius_meters": None,
            "range_meters": 18,
        }
        spec = CombatService._resolve_supported_area_spell_spec(ctx)
        self.assertIsNone(spec)

    def test_line_without_length_meters_returns_none(self):
        ctx = {
            "area_shape": "line",
            "length_meters": None,
            "range_meters": 0,
        }
        spec = CombatService._resolve_supported_area_spell_spec(ctx)
        self.assertIsNone(spec)

    def test_dimension_zero_returns_none(self):
        ctx = {
            "area_shape": "sphere",
            "radius_meters": 0,
            "range_meters": 45,
        }
        spec = CombatService._resolve_supported_area_spell_spec(ctx)
        self.assertIsNone(spec)

    def test_no_area_shape_returns_none(self):
        ctx = {
            "area_shape": None,
            "radius_meters": 6,
            "range_meters": 45,
        }
        spec = CombatService._resolve_supported_area_spell_spec(ctx)
        self.assertIsNone(spec)


class ExplicitDimensionTests(unittest.TestCase):
    """Tests for the explicit dimension fields (radius_meters, length_meters, side_meters)."""

    def test_sphere_explicit_radius_meters(self):
        ctx = {
            "area_shape": "sphere",
            "radius_meters": 6,
            "range_meters": 45,
        }
        spec = CombatService._resolve_supported_area_spell_spec(ctx)
        self.assertIsNotNone(spec)
        self.assertEqual(spec["shape"], "sphere")
        self.assertEqual(spec["size_meters"], 6)

    def test_cone_explicit_length_meters(self):
        ctx = {
            "area_shape": "cone",
            "length_meters": 9,
            "range_meters": 0,
        }
        spec = CombatService._resolve_supported_area_spell_spec(ctx)
        self.assertIsNotNone(spec)
        self.assertEqual(spec["shape"], "cone")
        self.assertEqual(spec["size_meters"], 9)

    def test_cube_explicit_side_meters(self):
        ctx = {
            "area_shape": "cube",
            "side_meters": 4,
            "range_meters": 0,
        }
        spec = CombatService._resolve_supported_area_spell_spec(ctx)
        self.assertIsNotNone(spec)
        self.assertEqual(spec["shape"], "cube")
        self.assertEqual(spec["size_meters"], 4)

    def test_cylinder_explicit_radius_meters(self):
        ctx = {
            "area_shape": "cylinder",
            "radius_meters": 3,
            "range_meters": 9,
        }
        spec = CombatService._resolve_supported_area_spell_spec(ctx)
        self.assertIsNotNone(spec)
        self.assertEqual(spec["shape"], "cylinder")
        self.assertEqual(spec["size_meters"], 3)

    def test_line_explicit_length_meters(self):
        ctx = {
            "area_shape": "line",
            "length_meters": 18,
            "range_meters": 0,
        }
        spec = CombatService._resolve_supported_area_spell_spec(ctx)
        self.assertIsNotNone(spec)
        self.assertEqual(spec["shape"], "line")
        self.assertEqual(spec["size_meters"], 18)

    def test_range_zero_passes_through(self):
        ctx = {
            "area_shape": "cone",
            "length_meters": 4.5,
            "range_meters": 0,
        }
        spec = CombatService._resolve_supported_area_spell_spec(ctx)
        self.assertIsNotNone(spec)
        self.assertEqual(spec["range_meters"], 0)

    def test_wrong_shape_field_returns_none(self):
        """If the wrong explicit field is set for the shape (side_meters on a
        sphere), the resolver returns None — no cross-field fallback."""
        ctx = {
            "area_shape": "sphere",
            "radius_meters": None,
            "side_meters": 4,
            "range_meters": 45,
        }
        spec = CombatService._resolve_supported_area_spell_spec(ctx)
        self.assertIsNone(spec)


class CanonicalSpellDimensionTests(unittest.TestCase):
    """Verify that _resolve_supported_area_spell_spec returns the correct
    size_meters for every canonical D&D spell in the seed catalog.

    These tests use the explicit fields only.
    Combined with test_unit_conversion.py they guarantee the full pipeline:

        seed value → _resolve_dimension_for_shape → meters_to_cells → sizeCells
    """

    def _ctx(self, shape: str, range_meters: float | None, **dims) -> dict:
        return {
            "area_shape": shape,
            "radius_meters": None,
            "length_meters": None,
            "side_meters": None,
            "range_meters": range_meters,
            **dims,
        }

    def test_burning_hands_cone_4_5m(self):
        ctx = self._ctx("cone", 0, length_meters=4.5)
        spec = CombatService._resolve_supported_area_spell_spec(ctx)
        self.assertIsNotNone(spec)
        self.assertEqual(spec["shape"], "cone")
        self.assertEqual(spec["size_meters"], 4.5)

    def test_thunderwave_cube_4_5m(self):
        ctx = self._ctx("cube", 0, side_meters=4.5)
        spec = CombatService._resolve_supported_area_spell_spec(ctx)
        self.assertIsNotNone(spec)
        self.assertEqual(spec["shape"], "cube")
        self.assertEqual(spec["size_meters"], 4.5)

    def test_fireball_sphere_6m_range_45m(self):
        ctx = self._ctx("sphere", 45, radius_meters=6.0)
        spec = CombatService._resolve_supported_area_spell_spec(ctx)
        self.assertIsNotNone(spec)
        self.assertEqual(spec["shape"], "sphere")
        self.assertEqual(spec["size_meters"], 6.0)
        self.assertEqual(spec["range_meters"], 45)

    def test_fog_cloud_sphere_6m_range_36m(self):
        ctx = self._ctx("sphere", 36, radius_meters=6.0)
        spec = CombatService._resolve_supported_area_spell_spec(ctx)
        self.assertIsNotNone(spec)
        self.assertEqual(spec["size_meters"], 6.0)
        self.assertEqual(spec["range_meters"], 36)

    def test_spike_growth_sphere_6m_range_45m(self):
        ctx = self._ctx("sphere", 45, radius_meters=6.0)
        spec = CombatService._resolve_supported_area_spell_spec(ctx)
        self.assertIsNotNone(spec)
        self.assertEqual(spec["size_meters"], 6.0)


class HailOfThornsGuardTests(unittest.TestCase):
    """Hail of Thorns has a 5-ft (1.5m) burst on weapon hit, but the area
    originates from the *hit target*, not from a freely chosen anchor cell.
    The spell must NOT be pushed through the generic AoE targeting pipeline
    (which requires an anchor cell selection by the player).

    Guard: as long as hail_of_thorns carries no area_shape in the spell
    context, _resolve_supported_area_spell_spec returns None and the cast
    falls through to the single-target path.
    """

    def _hail_ctx(self) -> dict:
        return {
            "target_type": "self",
            "area_shape": None,
            "radius_meters": None,
            "length_meters": None,
            "side_meters": None,
            "range_meters": 0,
            "spell_canonical_key": "hail_of_thorns",
        }

    def test_hail_of_thorns_no_area_shape_returns_none_spec(self):
        spec = CombatService._resolve_supported_area_spell_spec(self._hail_ctx())
        self.assertIsNone(
            spec,
            "hail_of_thorns must not produce an area spec — it has no area_shape "
            "in the catalog (AoE is auto-triggered on hit, not anchor-selected).",
        )

    def test_hail_of_thorns_accidental_area_shape_would_break(self):
        ctx = dict(self._hail_ctx())
        ctx["area_shape"] = "sphere"
        ctx["radius_meters"] = 1.5
        spec = CombatService._resolve_supported_area_spell_spec(ctx)
        self.assertIsNotNone(
            spec,
            "If area_shape is set, the resolver produces a spec and the combat "
            "pipeline demands an anchor cell — wrong behavior for hail_of_thorns.",
        )
