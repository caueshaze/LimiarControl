"""Tests for spell preparation logic.

Covers:
- compute_prepared_spell_limit
- create_pending_spell_preparation
- apply_prepared_spells
"""

from __future__ import annotations

import unittest

from app.services.spell_preparation import (
    apply_prepared_spells,
    compute_prepared_spell_limit,
    create_pending_spell_preparation,
)


class TestComputePreparedSpellLimit(unittest.TestCase):
    def test_full_caster(self):
        self.assertEqual(compute_prepared_spell_limit("cleric", 5, 3), 8)

    def test_half_caster(self):
        self.assertEqual(compute_prepared_spell_limit("paladin", 5, 2), 4)

    def test_half_caster_low_level(self):
        self.assertEqual(compute_prepared_spell_limit("paladin", 2, 1), 2)

    def test_minimum_one(self):
        self.assertEqual(compute_prepared_spell_limit("cleric", 1, -2), 1)

    def test_zero_modifier(self):
        self.assertEqual(compute_prepared_spell_limit("druid", 3, 0), 3)


class TestCreatePendingSpellPreparation(unittest.TestCase):
    def _base_state(self, **overrides):
        defaults = {
            "class": "cleric",
            "level": 5,
            "abilities": {"wisdom": 16},
            "spellcasting": {
                "ability": "wisdom",
                "spells": [
                    {
                        "id": "s1",
                        "name": "Bless",
                        "level": 1,
                        "prepared": True,
                    },
                    {
                        "id": "s2",
                        "name": "Cure Wounds",
                        "level": 1,
                        "prepared": False,
                    },
                    {
                        "id": "s3",
                        "name": "Guidance",
                        "level": 0,
                        "prepared": True,
                    },
                ],
            },
        }
        # Handle class_ kwarg → "class" dict key (class is a reserved word)
        if "class_" in overrides:
            overrides["class"] = overrides.pop("class_")
        defaults.update(overrides)
        return defaults

    def test_creates_pending_for_prepared_caster(self):
        pending = create_pending_spell_preparation(self._base_state())
        self.assertIsNotNone(pending)
        self.assertEqual(pending["class_key"], "cleric")
        self.assertEqual(pending["prepared_limit"], 8)  # 5 + 3
        self.assertEqual(pending["current_prepared_spell_ids"], ["s1"])
        self.assertEqual(pending["source"], "long_rest")

    def test_creates_pending_for_spellbook_caster(self):
        pending = create_pending_spell_preparation(
            self._base_state(
                class_="wizard",
                abilities={"intelligence": 18},
                spellcasting={
                    "ability": "intelligence",
                    "spells": [
                        {"id": "w1", "name": "Magic Missile", "level": 1, "prepared": True},
                    ],
                },
            )
        )
        self.assertIsNotNone(pending)
        self.assertEqual(pending["class_key"], "wizard")
        self.assertEqual(pending["prepared_limit"], 9)  # 5 + 4

    def test_creates_pending_for_half_caster(self):
        pending = create_pending_spell_preparation(
            self._base_state(
                class_="paladin",
                level=5,
                abilities={"charisma": 14},
                spellcasting={
                    "ability": "charisma",
                    "spells": [
                        {"id": "p1", "name": "Bless", "level": 1, "prepared": True},
                    ],
                },
            )
        )
        self.assertIsNotNone(pending)
        self.assertEqual(pending["class_key"], "paladin")
        self.assertEqual(pending["prepared_limit"], 4)  # floor(5/2) + 2

    def test_no_pending_for_known_caster(self):
        pending = create_pending_spell_preparation(
            self._base_state(class_="sorcerer")
        )
        self.assertIsNone(pending)

    def test_no_pending_for_non_caster(self):
        pending = create_pending_spell_preparation(
            self._base_state(class_="fighter", spellcasting=None)
        )
        self.assertIsNone(pending)

    def test_no_pending_without_spellcasting(self):
        pending = create_pending_spell_preparation(
            self._base_state(spellcasting=None)
        )
        self.assertIsNone(pending)

    def test_no_pending_without_spells(self):
        pending = create_pending_spell_preparation(
            self._base_state(spellcasting={"ability": "wisdom", "spells": []})
        )
        self.assertIsNone(pending)

    def test_no_pending_without_ability(self):
        pending = create_pending_spell_preparation(
            self._base_state(spellcasting={"spells": [{"id": "s1", "level": 1}]})
        )
        self.assertIsNone(pending)

    def test_cantrips_excluded_from_current_prepared(self):
        pending = create_pending_spell_preparation(self._base_state())
        self.assertEqual(pending["current_prepared_spell_ids"], ["s1"])


class TestApplyPreparedSpells(unittest.TestCase):
    def _base_state(self):
        return {
            "pending_spell_preparation": {"prepared_limit": 2},
            "spellcasting": {
                "ability": "wisdom",
                "spells": [
                    {"id": "s1", "name": "Bless", "level": 1, "prepared": True},
                    {"id": "s2", "name": "Cure Wounds", "level": 1, "prepared": False},
                    {"id": "s3", "name": "Guidance", "level": 0, "prepared": False},
                ],
            },
        }

    def test_updates_prepared_flags(self):
        result = apply_prepared_spells(self._base_state(), ["s2"])
        spells = result["spellcasting"]["spells"]
        self.assertFalse(spells[0]["prepared"])  # s1 not in list
        self.assertTrue(spells[1]["prepared"])   # s2 in list
        self.assertTrue(spells[2]["prepared"])   # s3 cantrip

    def test_clears_pending_state(self):
        result = apply_prepared_spells(self._base_state(), ["s1"])
        self.assertNotIn("pending_spell_preparation", result)

    def test_preserves_cantrips_always_prepared(self):
        result = apply_prepared_spells(self._base_state(), [])
        spells = result["spellcasting"]["spells"]
        self.assertTrue(spells[2]["prepared"])  # cantrip

    def test_handles_missing_spellcasting(self):
        result = apply_prepared_spells(
            {"pending_spell_preparation": {}}, ["s1"]
        )
        self.assertNotIn("pending_spell_preparation", result)

    def test_idempotent_on_empty_spells(self):
        result = apply_prepared_spells(
            {
                "pending_spell_preparation": {},
                "spellcasting": {"ability": "wisdom", "spells": []},
            },
            [],
        )
        self.assertEqual(result["spellcasting"]["spells"], [])
        self.assertNotIn("pending_spell_preparation", result)


if __name__ == "__main__":
    unittest.main()
