"""Tests for metadata-driven area spell targeting.

Verifies that _resolve_supported_area_spell_spec prefers area_size_meters
from the spell context over the hardcoded _SUPPORTED_AREA_SPELL_SPECS dict,
and that the legacy fallback still works for SRD spells without DB metadata.
"""
from __future__ import annotations

import unittest

from app.services.combat import CombatService


class ResolveAreaSpellSpecTests(unittest.TestCase):
    """Unit tests for _resolve_supported_area_spell_spec."""

    # ------------------------------------------------------------------
    # Metadata-driven path
    # ------------------------------------------------------------------

    def test_metadata_sphere_returns_spec_from_area_size_meters(self):
        ctx = {
            "target_mode": "sphere",
            "area_size_meters": 4,
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
            "target_mode": "cone",
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
            "target_mode": "cube",
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
            "target_mode": "line",
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
            "target_mode": "cone",
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
            "target_mode": "sphere",
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
                "target_mode": "sphere",
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
            "target_mode": "ranged",
            "area_size_meters": 5,
            "range_meters": 18,
            "spell_canonical_key": "magic_missile",
        }
        spec = CombatService._resolve_supported_area_spell_spec(ctx)
        self.assertIsNone(spec)

    def test_missing_target_mode_returns_none(self):
        ctx = {
            "target_mode": None,
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
            "target_mode": "sphere",
            "area_size_meters": 0,
            "range_meters": 30,
            "spell_canonical_key": "unknown_sphere_spell",
        }
        spec = CombatService._resolve_supported_area_spell_spec(ctx)
        self.assertIsNone(spec)

    def test_unknown_spell_without_metadata_returns_none(self):
        ctx = {
            "target_mode": "sphere",
            "area_size_meters": None,
            "range_meters": 18,
            "spell_canonical_key": "custom_unknown_sphere",
        }
        spec = CombatService._resolve_supported_area_spell_spec(ctx)
        self.assertIsNone(spec)

    def test_cylinder_target_mode_is_not_area_shape_returns_none(self):
        """cylinder is a valid TargetMode but not a supported AoE map shape."""
        ctx = {
            "target_mode": "cylinder",
            "area_size_meters": 5,
            "range_meters": 18,
            "spell_canonical_key": "some_cylinder_spell",
        }
        spec = CombatService._resolve_supported_area_spell_spec(ctx)
        self.assertIsNone(spec)
