"""Tests for meters_to_cells and the D&D 5e AoE conversion table.

Ensures that METERS_PER_CELL = 1.5 produces the expected integer cell counts
for every canonical D&D spell dimension used in the seed catalog.

Guarantee: if a spell carries lengthMeters / radiusMeters / sideMeters and
_resolve_dimension_for_shape returns that value, meters_to_cells(value) must
equal the cell count expected by D&D grid rules.
"""
from __future__ import annotations

import unittest

from app.services.combat_service.unit_conversion import meters_to_cells


class MetersToСellsConversionTests(unittest.TestCase):
    """Verify the D&D ↔ grid conversion table (METERS_PER_CELL = 1.5)."""

    # ------------------------------------------------------------------
    # AoE dimension conversions
    # ------------------------------------------------------------------

    def test_1_5m_is_1_cell(self):
        """5 ft = 1.5 m → 1 cell (Hail of Thorns radius)."""
        self.assertEqual(meters_to_cells(1.5), 1)

    def test_4_5m_is_3_cells(self):
        """15 ft = 4.5 m → 3 cells (Burning Hands cone, Thunderwave cube)."""
        self.assertEqual(meters_to_cells(4.5), 3)

    def test_6m_is_4_cells(self):
        """20 ft = 6.0 m → 4 cells (Fireball / Fog Cloud / Spike Growth radius)."""
        self.assertEqual(meters_to_cells(6.0), 4)

    # ------------------------------------------------------------------
    # Range conversions
    # ------------------------------------------------------------------

    def test_36m_is_24_cells(self):
        """120 ft = 36 m → 24 cells (Fog Cloud range)."""
        self.assertEqual(meters_to_cells(36), 24)

    def test_45m_is_30_cells(self):
        """150 ft = 45 m → 30 cells (Fireball / Spike Growth range)."""
        self.assertEqual(meters_to_cells(45), 30)

    def test_9m_is_6_cells(self):
        """30 ft = 9 m → 6 cells (standard character movement)."""
        self.assertEqual(meters_to_cells(9), 6)

    def test_18m_is_12_cells(self):
        """60 ft = 18 m → 12 cells (Magic Missile range)."""
        self.assertEqual(meters_to_cells(18), 12)

    # ------------------------------------------------------------------
    # Canonical D&D spell cell counts
    # ------------------------------------------------------------------

    def test_burning_hands_cone_cells(self):
        """Burning Hands: 15-ft cone → lengthMeters=4.5 → 3 cells."""
        self.assertEqual(meters_to_cells(4.5), 3)

    def test_thunderwave_cube_cells(self):
        """Thunderwave: 15-ft cube → sideMeters=4.5 → 3 cells."""
        self.assertEqual(meters_to_cells(4.5), 3)

    def test_fireball_radius_cells(self):
        """Fireball: 20-ft radius → radiusMeters=6 → 4 cells."""
        self.assertEqual(meters_to_cells(6.0), 4)

    def test_fireball_range_cells(self):
        """Fireball: 150-ft range → rangeMeters=45 → 30 cells."""
        self.assertEqual(meters_to_cells(45), 30)

    def test_fog_cloud_radius_cells(self):
        """Fog Cloud: 20-ft radius → radiusMeters=6 → 4 cells."""
        self.assertEqual(meters_to_cells(6.0), 4)

    def test_fog_cloud_range_cells(self):
        """Fog Cloud: 120-ft range → rangeMeters=36 → 24 cells."""
        self.assertEqual(meters_to_cells(36), 24)

    def test_spike_growth_radius_cells(self):
        """Spike Growth: 20-ft radius → radiusMeters=6 → 4 cells."""
        self.assertEqual(meters_to_cells(6.0), 4)

    def test_spike_growth_range_cells(self):
        """Spike Growth: 150-ft range → rangeMeters=45 → 30 cells."""
        self.assertEqual(meters_to_cells(45), 30)

    def test_hail_of_thorns_radius_cells(self):
        """Hail of Thorns: 5-ft radius → radiusMeters=1.5 → 1 cell."""
        self.assertEqual(meters_to_cells(1.5), 1)

    # ------------------------------------------------------------------
    # Arithmetic invariant: exact D&D multiples round cleanly
    # ------------------------------------------------------------------

    def test_all_canonical_values_divide_evenly(self):
        """Every canonical AoE dimension is an exact multiple of 1.5 m.
        None of them should produce a fractional intermediate result.
        """
        canonical = {
            "hail_of_thorns radius": 1.5,
            "burning_hands length": 4.5,
            "thunderwave side": 4.5,
            "fireball radius": 6.0,
            "fog_cloud radius": 6.0,
            "spike_growth radius": 6.0,
        }
        for name, meters in canonical.items():
            remainder = meters % 1.5
            self.assertAlmostEqual(
                remainder, 0.0,
                msg=f"{name} ({meters}m) is not an exact multiple of 1.5m",
            )


class MetersToСellsDocTests(unittest.TestCase):
    """Verify the examples documented in unit_conversion.py module docstring."""

    def test_docstring_examples(self):
        pairs = [
            (1.5, 1),
            (4.5, 3),
            (6.0, 4),
            (9.0, 6),
            (18.0, 12),
            (36.0, 24),
            (45.0, 30),
        ]
        for meters, expected_cells in pairs:
            with self.subTest(meters=meters):
                self.assertEqual(meters_to_cells(meters), expected_cells)
