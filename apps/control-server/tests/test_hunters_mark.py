"""Tests for Hunter's Mark (Marca do Caçador).

Covers:
- Seed contract: level=1, bonus_action, 27m, concentration, upcast.mode=duration_scaling
- Note: +1d6 weapon damage rider is handled separately in weapon_attack_damage.py
  (via _get_hunters_mark_effect_for_target). Tests cover the seed contract and
  basic effect structure.
- hunters_mark damage rider is tested implicitly in test_weapon_damage_breakdown.py
"""

from __future__ import annotations

import json
import unittest

from app.services.combat import CombatService


# ---------------------------------------------------------------------------
# Seed tests
# ---------------------------------------------------------------------------

class HuntersMarkSeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app.services.seed_paths import resolve_base_seed_path
        seed_path = resolve_base_seed_path(__file__, "base_spells.seed.json")
        with open(seed_path) as f:
            raw = json.load(f)
        spells = raw["spells"] if isinstance(raw, dict) else raw
        cls.entry = next(
            (s for s in spells if isinstance(s, dict) and s.get("canonicalKey") == "hunters_mark"),
            None,
        )

    def test_entry_exists(self):
        self.assertIsNotNone(self.entry, "hunters_mark not found in seed")

    def test_contract_fields(self):
        e = self.entry
        self.assertEqual(e["level"], 1)
        self.assertEqual(e["school"], "divination")
        self.assertEqual(e["castingTimeType"], "bonus_action")
        self.assertEqual(e["rangeMeters"], 27)
        self.assertTrue(e["concentration"])
        self.assertEqual(e["attackType"], "none")

    def test_upcast_duration_scaling(self):
        up = self.entry.get("upcast")
        self.assertIsNotNone(up)
        self.assertEqual(up["mode"], "duration_scaling")

    def test_resolutionType_buff(self):
        self.assertEqual(self.entry.get("resolutionType"), "buff")

    def test_casting_time_is_bonus_action(self):
        self.assertEqual(self.entry["castingTimeType"], "bonus_action")

    def test_requires_target_sight(self):
        self.assertTrue(self.entry.get("requiresTargetSight"))

    def test_no_declarative_effects(self):
        # hunters_mark damage rider is handled by _get_hunters_mark_effect_for_target
        self.assertFalse(bool(self.entry.get("effects")))


# ---------------------------------------------------------------------------
# Damage rider detection
# ---------------------------------------------------------------------------

class HuntersMarkDamageRiderTests(unittest.TestCase):
    def _participant_with_mark(self, target_id: str) -> dict:
        return {
            "id": "attacker",
            "active_effects": [
                {
                    "kind": "spell_effect",
                    "metadata": {
                        "source_spell_key": "hunters_mark",
                        "concentration": True,
                        "marked_target_participant_id": target_id,
                    },
                }
            ],
        }

    def test_mark_found_for_correct_target(self):
        attacker = self._participant_with_mark("enemy-1")
        effect = CombatService._get_hunters_mark_effect_for_target(
            attacker, target_participant_id="enemy-1"
        )
        self.assertIsNotNone(effect)
        self.assertEqual(effect["metadata"]["source_spell_key"], "hunters_mark")

    def test_mark_not_found_for_wrong_target(self):
        attacker = self._participant_with_mark("enemy-1")
        effect = CombatService._get_hunters_mark_effect_for_target(
            attacker, target_participant_id="enemy-2"
        )
        self.assertIsNone(effect)

    def test_no_mark_returns_none(self):
        attacker = {"id": "attacker", "active_effects": []}
        effect = CombatService._get_hunters_mark_effect_for_target(
            attacker, target_participant_id="enemy-1"
        )
        self.assertIsNone(effect)
