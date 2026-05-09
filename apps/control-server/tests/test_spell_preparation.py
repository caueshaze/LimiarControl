"""Tests for spell preparation logic.

Covers:
- compute_prepared_spell_limit
- create_pending_spell_preparation
- seed_initial_spell_preparation
- apply_prepared_spells
"""

from __future__ import annotations

import unittest

from app.services.spell_preparation import (
    apply_prepared_spells,
    apply_prepared_spells_with_long_rest_tracking,
    compute_prepared_spell_limit,
    create_pending_spell_preparation,
    seed_initial_spell_preparation,
    seed_long_rest_spell_preparation,
    settle_long_rest_spell_preparation,
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
        self.assertFalse(pending["available_during_rest"])

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


class TestLongRestSpellPreparationLifecycle(unittest.TestCase):
    def _base_state(self, **overrides):
        defaults = {
            "restState": "long_rest",
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
        if "class_" in overrides:
            overrides["class"] = overrides.pop("class_")
        defaults.update(overrides)
        return defaults

    def test_seed_long_rest_spell_preparation_clears_stale_marker_and_marks_available(self):
        seeded = seed_long_rest_spell_preparation(
            self._base_state(
                pending_spell_preparation={
                    "source": "long_rest",
                    "class_key": "cleric",
                    "prepared_limit": 8,
                    "current_prepared_spell_ids": ["old"],
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "available_during_rest": False,
                },
                spell_preparation_completed_during_long_rest=True,
            )
        )

        self.assertIn("pending_spell_preparation", seeded)
        self.assertTrue(seeded["pending_spell_preparation"]["available_during_rest"])
        self.assertEqual(seeded["pending_spell_preparation"]["current_prepared_spell_ids"], ["s1"])
        self.assertNotIn("spell_preparation_completed_during_long_rest", seeded)

    def test_apply_prepared_spells_during_long_rest_sets_completion_marker(self):
        state = self._base_state(
            pending_spell_preparation={
                "source": "long_rest",
                "class_key": "cleric",
                "prepared_limit": 8,
                "current_prepared_spell_ids": ["s1"],
                "created_at": "2026-01-01T00:00:00+00:00",
                "available_during_rest": True,
            }
        )

        result = apply_prepared_spells_with_long_rest_tracking(state, ["s2"])

        self.assertNotIn("pending_spell_preparation", result)
        self.assertTrue(result["spell_preparation_completed_during_long_rest"])

    def test_apply_prepared_spells_outside_long_rest_does_not_set_completion_marker(self):
        state = self._base_state(
            restState="exploration",
            pending_spell_preparation={
                "source": "long_rest",
                "class_key": "cleric",
                "prepared_limit": 8,
                "current_prepared_spell_ids": ["s1"],
                "created_at": "2026-01-01T00:00:00+00:00",
                "available_during_rest": True,
            },
        )

        result = apply_prepared_spells_with_long_rest_tracking(state, ["s2"])

        self.assertNotIn("pending_spell_preparation", result)
        self.assertNotIn("spell_preparation_completed_during_long_rest", result)

    def test_settle_long_rest_spell_preparation_keeps_existing_pending(self):
        state = self._base_state(
            restState="exploration",
            pending_spell_preparation={
                "source": "long_rest",
                "class_key": "cleric",
                "prepared_limit": 8,
                "current_prepared_spell_ids": ["s1"],
                "created_at": "2026-01-01T00:00:00+00:00",
                "available_during_rest": True,
            },
        )

        result = settle_long_rest_spell_preparation(state)

        self.assertIn("pending_spell_preparation", result)
        self.assertTrue(result["pending_spell_preparation"]["available_during_rest"])
        self.assertNotIn("spell_preparation_completed_during_long_rest", result)

    def test_settle_long_rest_spell_preparation_skips_duplicate_when_marker_exists(self):
        state = self._base_state(
            restState="exploration",
            spell_preparation_completed_during_long_rest=True,
        )

        result = settle_long_rest_spell_preparation(state)

        self.assertNotIn("pending_spell_preparation", result)
        self.assertNotIn("spell_preparation_completed_during_long_rest", result)

    def test_settle_long_rest_spell_preparation_creates_fallback_when_missing(self):
        result = settle_long_rest_spell_preparation(self._base_state(restState="exploration"))

        self.assertIn("pending_spell_preparation", result)
        self.assertFalse(result["pending_spell_preparation"]["available_during_rest"])
        self.assertEqual(result["pending_spell_preparation"]["prepared_limit"], 8)
        self.assertNotIn("spell_preparation_completed_during_long_rest", result)

    def test_next_long_rest_can_create_pending_again_after_marker_cycle(self):
        first_start = seed_long_rest_spell_preparation(self._base_state())
        self.assertIn("pending_spell_preparation", first_start)
        self.assertTrue(first_start["pending_spell_preparation"]["available_during_rest"])
        self.assertNotIn("spell_preparation_completed_during_long_rest", first_start)

        completed = apply_prepared_spells_with_long_rest_tracking(first_start, ["s2"])
        self.assertNotIn("pending_spell_preparation", completed)
        self.assertTrue(completed["spell_preparation_completed_during_long_rest"])

        settled = settle_long_rest_spell_preparation(completed)
        self.assertNotIn("pending_spell_preparation", settled)
        self.assertNotIn("spell_preparation_completed_during_long_rest", settled)

        second_start = seed_long_rest_spell_preparation(settled)
        self.assertIn("pending_spell_preparation", second_start)
        self.assertTrue(second_start["pending_spell_preparation"]["available_during_rest"])
        self.assertEqual(
            second_start["pending_spell_preparation"]["current_prepared_spell_ids"],
            ["s2"],
        )
        self.assertNotIn("spell_preparation_completed_during_long_rest", second_start)


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


class TestSeedInitialSpellPreparation(unittest.TestCase):
    def _base_state(self, **overrides):
        defaults = {
            "class": "cleric",
            "level": 5,
            "abilities": {"wisdom": 16},
            "spellcasting": {
                "ability": "wisdom",
                "spells": [
                    {"id": "s1", "name": "Bless", "level": 1, "prepared": True},
                    {"id": "s2", "name": "Guidance", "level": 0, "prepared": True},
                ],
            },
        }
        defaults.update(overrides)
        return defaults

    def test_creates_pending_for_prepared_casters(self):
        for class_id in ("cleric", "druid", "paladin", "wizard"):
            with self.subTest(class_id=class_id):
                state = self._base_state(**{"class": class_id})
                seed_initial_spell_preparation(state)
                self.assertIn("pending_spell_preparation", state)
                self.assertEqual(state["pending_spell_preparation"]["source"], "initial_setup")

    def test_does_not_create_pending_for_known_casters(self):
        for class_id in ("sorcerer", "bard", "warlock"):
            with self.subTest(class_id=class_id):
                state = self._base_state(**{"class": class_id})
                seed_initial_spell_preparation(state)
                self.assertNotIn("pending_spell_preparation", state)

    def test_does_not_create_pending_for_non_caster(self):
        state = {"class": "fighter", "level": 5}
        seed_initial_spell_preparation(state)
        self.assertNotIn("pending_spell_preparation", state)

    def test_source_is_initial_setup(self):
        state = self._base_state()
        seed_initial_spell_preparation(state)
        self.assertEqual(state["pending_spell_preparation"]["source"], "initial_setup")

    def test_available_during_rest_is_false(self):
        state = self._base_state()
        seed_initial_spell_preparation(state)
        self.assertFalse(state["pending_spell_preparation"]["available_during_rest"])

    def test_no_op_when_initial_completed_marker_present(self):
        state = self._base_state(spell_preparation_initial_completed=True)
        seed_initial_spell_preparation(state)
        self.assertNotIn("pending_spell_preparation", state)

    def test_no_op_when_pending_already_exists(self):
        existing = {"source": "long_rest", "class_key": "cleric", "prepared_limit": 1,
                    "current_prepared_spell_ids": [], "created_at": "", "available_during_rest": False}
        state = self._base_state(pending_spell_preparation=existing)
        seed_initial_spell_preparation(state)
        self.assertEqual(state["pending_spell_preparation"]["source"], "long_rest")

    def test_long_rest_still_creates_pending_after_initial_completed(self):
        state = self._base_state(spell_preparation_initial_completed=True)
        seeded = seed_long_rest_spell_preparation(state)
        self.assertIn("pending_spell_preparation", seeded)
        self.assertEqual(seeded["pending_spell_preparation"]["source"], "long_rest")

    def test_apply_initial_sets_completed_marker(self):
        state = self._base_state()
        seed_initial_spell_preparation(state)
        self.assertEqual(state["pending_spell_preparation"]["source"], "initial_setup")

        # Simulate the endpoint: capture was_initial_setup, then apply
        pending = (state or {}).get("pending_spell_preparation") or {}
        was_initial_setup = pending.get("source") == "initial_setup"
        result = apply_prepared_spells_with_long_rest_tracking(state, ["s1"])
        if was_initial_setup:
            result["spell_preparation_initial_completed"] = True

        self.assertNotIn("pending_spell_preparation", result)
        self.assertTrue(result["spell_preparation_initial_completed"])

    def test_apply_initial_does_not_set_long_rest_marker(self):
        state = self._base_state()
        seed_initial_spell_preparation(state)
        result = apply_prepared_spells_with_long_rest_tracking(state, ["s1"])
        self.assertNotIn("spell_preparation_completed_during_long_rest", result)


if __name__ == "__main__":
    unittest.main()
