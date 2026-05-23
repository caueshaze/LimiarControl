"""Tests for Floating Disk / Tenser's Floating Disk (Disco Flutuante).

Covers:
- Seed contract: level=1, ritual, point target, no concentration, persistent, utility
"""

from __future__ import annotations

import json
import unittest


class FloatingDiskSeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app.services.seed_paths import resolve_base_seed_path
        seed_path = resolve_base_seed_path(__file__, "base_spells.seed.json")
        with open(seed_path) as f:
            raw = json.load(f)
        spells = raw["spells"] if isinstance(raw, dict) else raw
        cls.entry = next(
            (s for s in spells if isinstance(s, dict) and s.get("canonicalKey") == "floating_disk"),
            None,
        )

    def test_entry_exists(self):
        self.assertIsNotNone(self.entry, "floating_disk not found in seed")

    def test_contract_fields(self):
        e = self.entry
        self.assertEqual(e["level"], 1)
        self.assertEqual(e["school"], "conjuration")
        self.assertEqual(e["castingTimeType"], "action")
        self.assertFalse(e["concentration"])
        self.assertEqual(e["attackType"], "none")

    def test_is_ritual(self):
        self.assertTrue(self.entry.get("ritual"))

    def test_selection_type_point(self):
        self.assertEqual(self.entry.get("selectionType"), "point")

    def test_effect_timing_persistent(self):
        self.assertEqual(self.entry.get("effectTiming"), "persistent")

    def test_resolution_type_utility(self):
        self.assertEqual(self.entry.get("resolutionType"), "utility")

    def test_no_saving_throw(self):
        self.assertIsNone(self.entry.get("savingThrow"))

    def test_range_30ft(self):
        self.assertEqual(self.entry.get("rangeMeters"), 9)

    def test_no_declarative_effects(self):
        self.assertFalse(bool(self.entry.get("effects")))
