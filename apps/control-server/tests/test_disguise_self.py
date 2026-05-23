"""Tests for Disguise Self (Disfarçar-se).

Covers:
- Seed contract: level=1, self-target, no concentration, persistent, no declarative effects
"""

from __future__ import annotations

import json
import unittest


class DisguiseSelfSeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app.services.seed_paths import resolve_base_seed_path
        seed_path = resolve_base_seed_path(__file__, "base_spells.seed.json")
        with open(seed_path) as f:
            raw = json.load(f)
        spells = raw["spells"] if isinstance(raw, dict) else raw
        cls.entry = next(
            (s for s in spells if isinstance(s, dict) and s.get("canonicalKey") == "disguise_self"),
            None,
        )

    def test_entry_exists(self):
        self.assertIsNotNone(self.entry, "disguise_self not found in seed")

    def test_contract_fields(self):
        e = self.entry
        self.assertEqual(e["level"], 1)
        self.assertEqual(e["school"], "illusion")
        self.assertEqual(e["castingTimeType"], "action")
        self.assertFalse(e["concentration"])
        self.assertEqual(e["attackType"], "none")

    def test_target_type_self(self):
        self.assertEqual(self.entry.get("targetType"), "self")

    def test_selection_type_self(self):
        self.assertEqual(self.entry.get("selectionType"), "self")

    def test_effect_timing_persistent(self):
        self.assertEqual(self.entry.get("effectTiming"), "persistent")

    def test_no_saving_throw(self):
        self.assertIsNone(self.entry.get("savingThrow"))

    def test_no_declarative_effects(self):
        self.assertFalse(bool(self.entry.get("effects")))

    def test_not_ritual(self):
        self.assertFalse(self.entry.get("ritual"))

    def test_range_self(self):
        self.assertEqual(self.entry.get("rangeKind"), "self")
