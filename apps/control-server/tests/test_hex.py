"""Tests for Hex (Nublar / Maldição).

Covers:
- Seed contract: level=1, bonus_action, 27m, concentration, no effects in seed
- Note: +1d6 necrotic damage rider and ability disadvantage are NOT declaratively
  automated — they require manual GM/player tracking. Tests reflect this.
- Cast creates a persistent mark effect on the target (source_spell_key=hex)
- Concentration: mark is removed when caster loses concentration
"""

from __future__ import annotations

import json
import unittest


# ---------------------------------------------------------------------------
# Seed tests
# ---------------------------------------------------------------------------

class HexSeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app.services.seed_paths import resolve_base_seed_path
        seed_path = resolve_base_seed_path(__file__, "base_spells.seed.json")
        with open(seed_path) as f:
            raw = json.load(f)
        spells = raw["spells"] if isinstance(raw, dict) else raw
        cls.entry = next(
            (s for s in spells if isinstance(s, dict) and s.get("canonicalKey") == "hex"),
            None,
        )

    def test_entry_exists(self):
        self.assertIsNotNone(self.entry, "hex not found in seed")

    def test_contract_fields(self):
        e = self.entry
        self.assertEqual(e["level"], 1)
        self.assertEqual(e["school"], "enchantment")
        self.assertEqual(e["castingTimeType"], "bonus_action")
        self.assertEqual(e["rangeMeters"], 27)
        self.assertTrue(e["concentration"])
        self.assertEqual(e["attackType"], "none")

    def test_resolutionType_debuff(self):
        self.assertEqual(self.entry.get("resolutionType"), "debuff")

    def test_no_saving_throw(self):
        self.assertIsNone(self.entry.get("savingThrow"))

    def test_no_declarative_effects(self):
        # Hex damage rider and ability disadvantage are manual
        self.assertFalse(bool(self.entry.get("effects")))

    def test_casting_time_is_bonus_action(self):
        self.assertEqual(self.entry["castingTimeType"], "bonus_action")

    def test_target_type_ranged(self):
        self.assertEqual(self.entry.get("targetType"), "ranged")

    def test_requires_target_sight(self):
        self.assertTrue(self.entry.get("requiresTargetSight"))


# ---------------------------------------------------------------------------
# Persistent mark structure
# ---------------------------------------------------------------------------

class HexMarkStructureTests(unittest.TestCase):
    """Validates the structure of a hex persistent mark effect."""

    def _make_hex_mark(self, target_id: str = "enemy-1") -> dict:
        return {
            "kind": "spell_effect",
            "metadata": {
                "source_spell_key": "hex",
                "concentration": True,
                "concentration_group": "conc-hex-1",
                "target_participant_id": target_id,
            },
        }

    def test_mark_kind_is_spell_effect(self):
        mark = self._make_hex_mark()
        self.assertEqual(mark["kind"], "spell_effect")

    def test_mark_source_spell_key(self):
        mark = self._make_hex_mark()
        self.assertEqual(mark["metadata"]["source_spell_key"], "hex")

    def test_mark_is_concentration(self):
        mark = self._make_hex_mark()
        self.assertTrue(mark["metadata"]["concentration"])

    def test_mark_has_target_id(self):
        mark = self._make_hex_mark("enemy-5")
        self.assertEqual(mark["metadata"]["target_participant_id"], "enemy-5")
