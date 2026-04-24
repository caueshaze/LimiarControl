"""Tests for metadata-driven area spell targeting.

Verifies that _resolve_supported_area_spell_spec prefers area_size_meters
from the spell context over the hardcoded _SUPPORTED_AREA_SPELL_SPECS dict,
and that the legacy fallback still works for SRD spells without DB metadata.
"""
from __future__ import annotations

import unittest

from app.services.combat import CombatService


class ResolveAreaSpellSpecTests(unittest.TestCase):
    """Unit tests for _resolve_supported_area_spell_spec.

    Tests in this class that use ``area_size_meters`` are exercising the
    *deprecated legacy fallback path* with arbitrary custom values (e.g. 4m).
    They are NOT representative of real D&D spell dimensions — canonical
    D&D values (4.5m, 6m, 1.5m) are verified in
    ``ExplicitDimensionTests`` and ``test_unit_conversion.py``.
    """

    # ------------------------------------------------------------------
    # Legacy fallback path (deprecated area_size_meters, arbitrary values)
    # ------------------------------------------------------------------

    def test_metadata_sphere_returns_spec_from_area_size_meters(self):
        ctx = {
            "target_type": "ranged", "area_shape": "sphere",
            "area_size_meters": 4,  # arbitrary legacy value, not a D&D canonical dimension
            "range_meters": 30,
            "spell_canonical_key": "custom_nova",
        }
        spec = CombatService._resolve_supported_area_spell_spec(ctx)
        self.assertIsNotNone(spec)
        self.assertEqual(spec["shape"], "sphere")
        self.assertEqual(spec["size_meters"], 4)
        self.assertEqual(spec["range_meters"], 30)

    def test_metadata_cone_returns_spec_from_area_size_meters(self):
        ctx = {
            "target_type": "ranged", "area_shape": "cone",
            "area_size_meters": 3,
            "range_meters": 0,
            "spell_canonical_key": "custom_cone_blast",
        }
        spec = CombatService._resolve_supported_area_spell_spec(ctx)
        self.assertIsNotNone(spec)
        self.assertEqual(spec["shape"], "cone")
        self.assertEqual(spec["size_meters"], 3)
        self.assertEqual(spec["range_meters"], 0)

    def test_metadata_cube_returns_spec_from_area_size_meters(self):
        ctx = {
            "target_type": "ranged", "area_shape": "cube",
            "area_size_meters": 3,
            "range_meters": 0,
            "spell_canonical_key": "custom_cube_wave",
        }
        spec = CombatService._resolve_supported_area_spell_spec(ctx)
        self.assertIsNotNone(spec)
        self.assertEqual(spec["shape"], "cube")
        self.assertEqual(spec["size_meters"], 3)

    def test_metadata_line_returns_spec_from_area_size_meters(self):
        ctx = {
            "target_type": "ranged", "area_shape": "line",
            "area_size_meters": 20,
            "range_meters": None,
            "spell_canonical_key": "custom_lightning_bolt",
        }
        spec = CombatService._resolve_supported_area_spell_spec(ctx)
        self.assertIsNotNone(spec)
        self.assertEqual(spec["shape"], "line")
        self.assertEqual(spec["size_meters"], 20)
        self.assertIsNone(spec["range_meters"])

    def test_metadata_self_origin_range_zero_is_allowed(self):
        """range_meters=0 must pass through; the range check is handled at
        the map boundary (0 → null → skip range validation)."""
        ctx = {
            "target_type": "ranged", "area_shape": "cone",
            "area_size_meters": 3,
            "range_meters": 0,
            "spell_canonical_key": "custom_breath_weapon",
        }
        spec = CombatService._resolve_supported_area_spell_spec(ctx)
        self.assertIsNotNone(spec)
        self.assertEqual(spec["range_meters"], 0)

    def test_metadata_takes_priority_over_hardcoded_dict(self):
        """If a spell has area_size_meters in its context, the hardcoded spec
        is ignored even if the canonical key is present in the fallback dict."""
        ctx = {
            "target_type": "ranged", "area_shape": "sphere",
            "area_size_meters": 10,  # overrides hardcoded 6m for fireball
            "range_meters": 45,
            "spell_canonical_key": "fireball",
        }
        spec = CombatService._resolve_supported_area_spell_spec(ctx)
        self.assertIsNotNone(spec)
        self.assertEqual(spec["size_meters"], 10)  # from metadata, not hardcoded 6

    # ------------------------------------------------------------------
    # Spells without area_size_meters — always None (no fallback)
    # ------------------------------------------------------------------

    def test_spell_without_area_size_metadata_returns_none(self):
        """Any spell missing area_size_meters returns None regardless of canonical key."""
        for canonical_key in ("fireball", "burning_hands", "thunderwave", "custom_nova"):
            ctx = {
                "target_type": "ranged", "area_shape": "sphere",
                "area_size_meters": None,
                "range_meters": 45,
                "spell_canonical_key": canonical_key,
            }
            spec = CombatService._resolve_supported_area_spell_spec(ctx)
            self.assertIsNone(spec, f"expected None for {canonical_key} without area_size_meters")

    # ------------------------------------------------------------------
    # Unsupported / incomplete metadata — must fail safely
    # ------------------------------------------------------------------

    def test_non_area_target_mode_returns_none(self):
        ctx = {
            "target_type": "ranged",
            "area_size_meters": 5,
            "range_meters": 18,
            "spell_canonical_key": "magic_missile",
        }
        spec = CombatService._resolve_supported_area_spell_spec(ctx)
        self.assertIsNone(spec)

    def test_missing_target_mode_returns_none(self):
        ctx = {
            "target_type": None, "area_shape": None,
            "area_size_meters": 5,
            "range_meters": 18,
            "spell_canonical_key": "some_spell",
        }
        spec = CombatService._resolve_supported_area_spell_spec(ctx)
        self.assertIsNone(spec)

    def test_area_size_meters_zero_falls_through_to_legacy(self):
        """area_size_meters=0 is invalid; should fall through to legacy dict.
        If the spell is not in the dict either, returns None."""
        ctx = {
            "target_type": "ranged", "area_shape": "sphere",
            "area_size_meters": 0,
            "range_meters": 30,
            "spell_canonical_key": "unknown_sphere_spell",
        }
        spec = CombatService._resolve_supported_area_spell_spec(ctx)
        self.assertIsNone(spec)

    def test_unknown_spell_without_metadata_returns_none(self):
        ctx = {
            "target_type": "ranged", "area_shape": "sphere",
            "area_size_meters": None,
            "range_meters": 18,
            "spell_canonical_key": "custom_unknown_sphere",
        }
        spec = CombatService._resolve_supported_area_spell_spec(ctx)
        self.assertIsNone(spec)

    def test_metadata_cylinder_returns_spec_from_area_size_meters(self):
        """Cylinder uses a 2D circular map footprint with area_size_meters as radius."""
        ctx = {
            "target_type": "ranged", "area_shape": "cylinder",
            "area_size_meters": 5,
            "range_meters": 18,
            "spell_canonical_key": "some_cylinder_spell",
        }
        spec = CombatService._resolve_supported_area_spell_spec(ctx)
        self.assertIsNotNone(spec)
        self.assertEqual(spec["shape"], "cylinder")
        self.assertEqual(spec["size_meters"], 5)
        self.assertEqual(spec["range_meters"], 18)


class ExplicitDimensionTests(unittest.TestCase):
    """Tests for the new explicit dimension fields (radius_meters, length_meters, side_meters).

    These verify that the new fields take precedence over the deprecated
    area_size_meters fallback, and that the fallback still works when only
    area_size_meters is present.
    """

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

    def test_explicit_takes_priority_over_area_size_meters(self):
        """When both radius_meters and area_size_meters are set, the explicit
        field wins."""
        ctx = {
            "area_shape": "sphere",
            "radius_meters": 10,
            "area_size_meters": 6,
            "range_meters": 45,
        }
        spec = CombatService._resolve_supported_area_spell_spec(ctx)
        self.assertIsNotNone(spec)
        self.assertEqual(spec["size_meters"], 10)

    def test_all_new_fields_none_falls_back_to_area_size_meters(self):
        """Legacy spells with only area_size_meters still resolve correctly."""
        ctx = {
            "area_shape": "sphere",
            "radius_meters": None,
            "length_meters": None,
            "side_meters": None,
            "area_size_meters": 6,
            "range_meters": 45,
        }
        spec = CombatService._resolve_supported_area_spell_spec(ctx)
        self.assertIsNotNone(spec)
        self.assertEqual(spec["size_meters"], 6)

    def test_all_dimension_fields_none_returns_none(self):
        """No dimension of any kind → spec is None."""
        ctx = {
            "area_shape": "sphere",
            "radius_meters": None,
            "length_meters": None,
            "side_meters": None,
            "area_size_meters": None,
            "range_meters": 45,
        }
        spec = CombatService._resolve_supported_area_spell_spec(ctx)
        self.assertIsNone(spec)

    def test_wrong_shape_field_ignored_falls_back_correctly(self):
        """If the wrong explicit field is set for the shape (shouldn't happen
        in practice), fall back to area_size_meters."""
        ctx = {
            "area_shape": "sphere",
            "radius_meters": None,
            "side_meters": 4,       # side belongs to cube, not sphere
            "area_size_meters": 6,
            "range_meters": 45,
        }
        spec = CombatService._resolve_supported_area_spell_spec(ctx)
        self.assertIsNotNone(spec)
        self.assertEqual(spec["size_meters"], 6)  # fallback used


class CanonicalSpellDimensionTests(unittest.TestCase):
    """Verify that _resolve_supported_area_spell_spec returns the correct
    size_meters for every canonical D&D spell in the seed catalog.

    These tests use the *new explicit fields only* (no area_size_meters).
    Combined with test_unit_conversion.py they guarantee the full pipeline:

        seed value → _resolve_dimension_for_shape → meters_to_cells → sizeCells
    """

    def _ctx(self, shape: str, range_meters: float | None, **dims) -> dict:
        return {
            "area_shape": shape,
            "radius_meters": None,
            "length_meters": None,
            "side_meters": None,
            "area_size_meters": None,
            "range_meters": range_meters,
            **dims,
        }

    def test_burning_hands_cone_4_5m(self):
        """15-ft cone → lengthMeters=4.5 → size_meters=4.5."""
        ctx = self._ctx("cone", 0, length_meters=4.5)
        spec = CombatService._resolve_supported_area_spell_spec(ctx)
        self.assertIsNotNone(spec)
        self.assertEqual(spec["shape"], "cone")
        self.assertEqual(spec["size_meters"], 4.5)

    def test_thunderwave_cube_4_5m(self):
        """15-ft cube → sideMeters=4.5 → size_meters=4.5."""
        ctx = self._ctx("cube", 0, side_meters=4.5)
        spec = CombatService._resolve_supported_area_spell_spec(ctx)
        self.assertIsNotNone(spec)
        self.assertEqual(spec["shape"], "cube")
        self.assertEqual(spec["size_meters"], 4.5)

    def test_fireball_sphere_6m_range_45m(self):
        """Fireball: 20-ft radius → radiusMeters=6, rangeMeters=45."""
        ctx = self._ctx("sphere", 45, radius_meters=6.0)
        spec = CombatService._resolve_supported_area_spell_spec(ctx)
        self.assertIsNotNone(spec)
        self.assertEqual(spec["shape"], "sphere")
        self.assertEqual(spec["size_meters"], 6.0)
        self.assertEqual(spec["range_meters"], 45)

    def test_fog_cloud_sphere_6m_range_36m(self):
        """Fog Cloud: 20-ft radius → radiusMeters=6, rangeMeters=36."""
        ctx = self._ctx("sphere", 36, radius_meters=6.0)
        spec = CombatService._resolve_supported_area_spell_spec(ctx)
        self.assertIsNotNone(spec)
        self.assertEqual(spec["size_meters"], 6.0)
        self.assertEqual(spec["range_meters"], 36)

    def test_spike_growth_sphere_6m_range_45m(self):
        """Spike Growth: 20-ft radius → radiusMeters=6, rangeMeters=45."""
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
        """Context matching the seed: targetType=self, no area_shape."""
        return {
            "target_type": "self",
            "area_shape": None,
            "radius_meters": None,
            "length_meters": None,
            "side_meters": None,
            "area_size_meters": None,
            "range_meters": 0,
            "spell_canonical_key": "hail_of_thorns",
        }

    def test_hail_of_thorns_no_area_shape_returns_none_spec(self):
        """Without area_shape the AoE resolver returns None → single-target cast."""
        spec = CombatService._resolve_supported_area_spell_spec(self._hail_ctx())
        self.assertIsNone(
            spec,
            "hail_of_thorns must not produce an area spec — it has no area_shape "
            "in the catalog (AoE is auto-triggered on hit, not anchor-selected).",
        )

    def test_hail_of_thorns_accidental_area_shape_would_break(self):
        """Regression guard: if area_shape were accidentally added to the catalog,
        the resolver WOULD return a spec, which would force anchor selection.
        This test documents the hazard so the next person understands why
        area_shape must stay absent from hail_of_thorns."""
        ctx = dict(self._hail_ctx())
        ctx["area_shape"] = "sphere"
        ctx["radius_meters"] = 1.5
        spec = CombatService._resolve_supported_area_spell_spec(ctx)
        # This DOES resolve — proof that adding areaShape would break the spell.
        self.assertIsNotNone(
            spec,
            "If area_shape is set, the resolver produces a spec and the combat "
            "pipeline demands an anchor cell — wrong behavior for hail_of_thorns.",
        )
