"""Tests for class_progression service and the integrated approve_level_up flow."""

from __future__ import annotations

import unittest

from app.services.character_progression import approve_level_up
from app.services.class_progression import (
    apply_level_up_stats,
    get_hp_gain_per_level,
    get_spell_slots_for_class_level,
)


# ── HP gain per level ──────────────────────────────────────────────────────────


class HpGainTests(unittest.TestCase):
    def test_wizard_d6_gains_4(self):
        self.assertEqual(get_hp_gain_per_level("wizard"), 4)

    def test_sorcerer_d6_gains_4(self):
        self.assertEqual(get_hp_gain_per_level("sorcerer"), 4)

    def test_cleric_d8_gains_5(self):
        self.assertEqual(get_hp_gain_per_level("cleric"), 5)

    def test_rogue_d8_gains_5(self):
        self.assertEqual(get_hp_gain_per_level("rogue"), 5)

    def test_fighter_d10_gains_6(self):
        self.assertEqual(get_hp_gain_per_level("fighter"), 6)

    def test_barbarian_d12_gains_7(self):
        self.assertEqual(get_hp_gain_per_level("barbarian"), 7)

    def test_unknown_class_defaults_to_5(self):
        self.assertEqual(get_hp_gain_per_level("unknown"), 5)

    def test_empty_class_defaults_to_5(self):
        self.assertEqual(get_hp_gain_per_level(""), 5)

    def test_class_name_is_case_insensitive(self):
        self.assertEqual(get_hp_gain_per_level("Wizard"), get_hp_gain_per_level("wizard"))


# ── Spell slot tables ──────────────────────────────────────────────────────────


class SpellSlotTableTests(unittest.TestCase):
    # Full casters
    def test_wizard_level_1_has_two_first_level_slots(self):
        slots = get_spell_slots_for_class_level("wizard", 1)
        self.assertEqual(slots, {1: 2})

    def test_wizard_level_3_unlocks_second_level_slots(self):
        slots = get_spell_slots_for_class_level("wizard", 3)
        self.assertEqual(slots[2], 2)
        self.assertEqual(slots[1], 4)

    def test_wizard_level_5_unlocks_third_level_slots(self):
        slots = get_spell_slots_for_class_level("wizard", 5)
        self.assertEqual(slots[3], 2)

    def test_wizard_level_17_has_9th_level_slot(self):
        slots = get_spell_slots_for_class_level("wizard", 17)
        self.assertEqual(slots[9], 1)

    def test_cleric_uses_same_full_caster_table_as_wizard(self):
        for level in range(1, 21):
            self.assertEqual(
                get_spell_slots_for_class_level("cleric", level),
                get_spell_slots_for_class_level("wizard", level),
            )

    # Half casters
    def test_paladin_level_1_has_no_slots(self):
        slots = get_spell_slots_for_class_level("paladin", 1)
        self.assertEqual(slots, {})

    def test_paladin_level_2_gets_first_slots(self):
        slots = get_spell_slots_for_class_level("paladin", 2)
        self.assertEqual(slots, {1: 2})

    def test_paladin_level_5_unlocks_second_level_slots(self):
        slots = get_spell_slots_for_class_level("paladin", 5)
        self.assertEqual(slots[2], 2)

    def test_ranger_matches_paladin_table(self):
        for level in range(1, 21):
            self.assertEqual(
                get_spell_slots_for_class_level("ranger", level),
                get_spell_slots_for_class_level("paladin", level),
            )

    # Warlock pact magic
    def test_warlock_level_1_has_one_first_level_slot(self):
        slots = get_spell_slots_for_class_level("warlock", 1)
        self.assertEqual(slots, {1: 1})

    def test_warlock_level_3_upgrades_to_second_level_slots(self):
        slots = get_spell_slots_for_class_level("warlock", 3)
        self.assertEqual(slots, {2: 2})

    def test_warlock_level_5_has_two_third_level_slots(self):
        slots = get_spell_slots_for_class_level("warlock", 5)
        self.assertEqual(slots, {3: 2})

    def test_warlock_level_11_has_three_fifth_level_slots(self):
        slots = get_spell_slots_for_class_level("warlock", 11)
        self.assertEqual(slots, {5: 3})

    # Non-casters
    def test_fighter_returns_none(self):
        self.assertIsNone(get_spell_slots_for_class_level("fighter", 5))

    def test_barbarian_returns_none(self):
        self.assertIsNone(get_spell_slots_for_class_level("barbarian", 10))

    def test_monk_returns_none(self):
        self.assertIsNone(get_spell_slots_for_class_level("monk", 5))

    def test_rogue_returns_none(self):
        self.assertIsNone(get_spell_slots_for_class_level("rogue", 5))

    def test_unknown_class_returns_none(self):
        self.assertIsNone(get_spell_slots_for_class_level("unknown", 5))


# ── apply_level_up_stats ───────────────────────────────────────────────────────


class ApplyLevelUpStatsTests(unittest.TestCase):
    def _base_wizard(self) -> dict:
        return {
            "class": "wizard",
            "level": 2,
            "maxHP": 10,
            "currentHP": 10,
            "hitDiceTotal": 2,
            "hitDiceRemaining": 2,
            "spellcasting": {
                "slots": {
                    "1": {"max": 3, "used": 1},
                }
            },
        }

    def test_max_hp_increases_by_hp_gain(self):
        data = apply_level_up_stats(self._base_wizard(), 3)
        self.assertEqual(data["maxHP"], 14)  # 10 + 4 (d6 average)

    def test_current_hp_also_increases_by_hp_gain(self):
        data = apply_level_up_stats(self._base_wizard(), 3)
        self.assertEqual(data["currentHP"], 14)

    def test_hit_dice_total_equals_new_level(self):
        data = apply_level_up_stats(self._base_wizard(), 3)
        self.assertEqual(data["hitDiceTotal"], 3)

    def test_hit_dice_remaining_increases_by_one(self):
        base = self._base_wizard()
        base["hitDiceRemaining"] = 1  # used one in short rest
        data = apply_level_up_stats(base, 3)
        self.assertEqual(data["hitDiceRemaining"], 2)

    def test_hit_dice_remaining_capped_at_total(self):
        data = apply_level_up_stats(self._base_wizard(), 3)
        self.assertLessEqual(data["hitDiceRemaining"], data["hitDiceTotal"])

    def test_wizard_level_2_to_3_unlocks_second_level_slots(self):
        data = apply_level_up_stats(self._base_wizard(), 3)
        slots = data["spellcasting"]["slots"]
        self.assertEqual(slots["2"]["max"], 2)
        self.assertEqual(slots["2"]["used"], 0)

    def test_existing_used_slots_are_preserved(self):
        data = apply_level_up_stats(self._base_wizard(), 3)
        # Level 1 slots: 3 max → 4 max; 1 was used, should remain 1
        self.assertEqual(data["spellcasting"]["slots"]["1"]["used"], 1)

    def test_slot_max_increases_correctly(self):
        data = apply_level_up_stats(self._base_wizard(), 3)
        self.assertEqual(data["spellcasting"]["slots"]["1"]["max"], 4)

    def test_used_cannot_exceed_new_max(self):
        base = self._base_wizard()
        # Artificially set used > new max (edge case guard)
        base["spellcasting"]["slots"]["1"]["used"] = 99
        data = apply_level_up_stats(base, 3)
        slot = data["spellcasting"]["slots"]["1"]
        self.assertLessEqual(slot["used"], slot["max"])

    def test_non_caster_spell_slots_untouched(self):
        base = {
            "class": "fighter",
            "level": 4,
            "maxHP": 40,
            "currentHP": 40,
            "hitDiceTotal": 4,
            "hitDiceRemaining": 4,
        }
        data = apply_level_up_stats(base, 5)
        self.assertNotIn("spellcasting", data)

    def test_non_caster_hp_still_increases(self):
        base = {
            "class": "barbarian",
            "level": 4,
            "maxHP": 40,
            "currentHP": 38,
            "hitDiceTotal": 4,
            "hitDiceRemaining": 3,
        }
        data = apply_level_up_stats(base, 5)
        self.assertEqual(data["maxHP"], 47)   # 40 + 7 (d12 average)
        self.assertEqual(data["currentHP"], 45)  # 38 + 7

    def test_warlock_level_2_to_3_changes_slot_level(self):
        base = {
            "class": "warlock",
            "level": 2,
            "maxHP": 16,
            "currentHP": 16,
            "hitDiceTotal": 2,
            "hitDiceRemaining": 2,
            "spellcasting": {
                "slots": {
                    "1": {"max": 2, "used": 1},
                }
            },
        }
        data = apply_level_up_stats(base, 3)
        slots = data["spellcasting"]["slots"]
        # Old level-1 slots should now have max=0
        self.assertEqual(slots["1"]["max"], 0)
        # New level-2 pact slots should appear
        self.assertEqual(slots["2"]["max"], 2)
        self.assertEqual(slots["2"]["used"], 0)

    def test_paladin_level_1_to_2_gains_first_slots(self):
        base = {
            "class": "paladin",
            "level": 1,
            "maxHP": 10,
            "currentHP": 10,
            "hitDiceTotal": 1,
            "hitDiceRemaining": 1,
        }
        data = apply_level_up_stats(base, 2)
        slots = data["spellcasting"]["slots"]
        self.assertEqual(slots["1"]["max"], 2)

    def test_original_data_is_not_mutated(self):
        base = self._base_wizard()
        original_max_hp = base["maxHP"]
        apply_level_up_stats(base, 3)
        self.assertEqual(base["maxHP"], original_max_hp)


# ── Integration: approve_level_up now includes stat recalculation ──────────────


class ApproveLevelUpIntegrationTests(unittest.TestCase):
    def _sheet(self, class_id: str, level: int, xp: int) -> dict:
        return {
            "class": class_id,
            "level": level,
            "experiencePoints": xp,
            "pendingLevelUp": True,
            "maxHP": 8,
            "currentHP": 5,
            "hitDiceTotal": level,
            "hitDiceRemaining": level,
            "spellcasting": {
                "slots": {
                    "1": {"max": 2, "used": 0},
                }
            },
        }

    def test_approve_increments_level(self):
        data = approve_level_up(self._sheet("wizard", 1, 300))
        self.assertEqual(data["level"], 2)

    def test_approve_updates_max_hp(self):
        data = approve_level_up(self._sheet("wizard", 1, 300))
        self.assertEqual(data["maxHP"], 12)  # 8 + 4 (d6)

    def test_approve_updates_current_hp(self):
        data = approve_level_up(self._sheet("wizard", 1, 300))
        self.assertEqual(data["currentHP"], 9)  # 5 + 4

    def test_approve_updates_hit_dice_total(self):
        data = approve_level_up(self._sheet("wizard", 1, 300))
        self.assertEqual(data["hitDiceTotal"], 2)

    def test_approve_updates_spell_slots_for_caster(self):
        data = approve_level_up(self._sheet("wizard", 1, 300))
        # Level 1→2: wizard keeps {1: 3} (was {1: 2})
        slots = data["spellcasting"]["slots"]
        self.assertEqual(slots["1"]["max"], 3)

    def test_approve_level_3_wizard_unlocks_level_2_slots(self):
        sheet = self._sheet("wizard", 2, 900)
        sheet["spellcasting"]["slots"]["1"]["max"] = 3
        data = approve_level_up(sheet)
        self.assertEqual(data["level"], 3)
        self.assertEqual(data["spellcasting"]["slots"]["2"]["max"], 2)

    def test_approve_does_not_affect_spell_slots_for_fighter(self):
        base = {
            "class": "fighter",
            "level": 1,
            "experiencePoints": 300,
            "pendingLevelUp": True,
            "maxHP": 10,
            "currentHP": 10,
            "hitDiceTotal": 1,
            "hitDiceRemaining": 1,
        }
        data = approve_level_up(base)
        self.assertNotIn("spellcasting", data)
        self.assertEqual(data["maxHP"], 16)  # 10 + 6 (d10)


if __name__ == "__main__":
    unittest.main()
