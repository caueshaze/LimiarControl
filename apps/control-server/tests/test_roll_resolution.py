"""Unit tests for RollResolutionService — pure logic, no DB."""

import unittest
from unittest.mock import patch

from app.schemas.roll import RollActorStats
from app.services.roll_resolution import (
    resolve_ability_check,
    resolve_attack_base,
    resolve_initiative,
    resolve_saving_throw,
    resolve_skill_check,
    roll_d20_pair,
    select_d20,
)


def _player_stats(**overrides) -> RollActorStats:
    defaults = dict(
        display_name="Hero",
        abilities={
            "strength": 16,     # mod +3
            "dexterity": 14,    # mod +2
            "constitution": 12, # mod +1
            "intelligence": 10, # mod 0
            "wisdom": 13,       # mod +1
            "charisma": 8,      # mod -1
        },
        saving_throws={"strength": 5, "constitution": 3},
        skills={"athletics": 5, "perception": 3},
        initiative_bonus=None,
        proficiency_bonus=2,
        actor_kind="player",
        actor_ref_id="user-1",
    )
    defaults.update(overrides)
    return RollActorStats(**defaults)


def _entity_stats(**overrides) -> RollActorStats:
    defaults = dict(
        display_name="Goblin",
        abilities={
            "strength": 8,      # mod -1
            "dexterity": 14,    # mod +2
            "constitution": 10, # mod 0
            "intelligence": 10, # mod 0
            "wisdom": 8,        # mod -1
            "charisma": 8,      # mod -1
        },
        saving_throws={"dexterity": 4},
        skills={"stealth": 6},
        initiative_bonus=3,
        proficiency_bonus=2,
        actor_kind="session_entity",
        actor_ref_id="se-1",
    )
    defaults.update(overrides)
    return RollActorStats(**defaults)


class TestD20Helpers(unittest.TestCase):
    def test_select_d20_normal_returns_first(self):
        self.assertEqual(select_d20(10, 18, "normal"), 10)

    def test_select_d20_advantage_returns_max(self):
        self.assertEqual(select_d20(10, 18, "advantage"), 18)

    def test_select_d20_disadvantage_returns_min(self):
        self.assertEqual(select_d20(10, 18, "disadvantage"), 10)

    @patch("random.randint", side_effect=[7, 14])
    def test_roll_d20_pair(self, _mock):
        a, b = roll_d20_pair()
        self.assertEqual(a, 7)
        self.assertEqual(b, 14)


class TestAbilityCheck(unittest.TestCase):
    @patch("app.services.roll_resolution.roll_d20_pair", return_value=(15, 8))
    def test_strength_normal(self, _mock):
        result = resolve_ability_check(_player_stats(), "strength")
        self.assertEqual(result.roll_type, "ability")
        self.assertEqual(result.modifier_used, 3)  # floor((16-10)/2)
        self.assertEqual(result.rolls, [15, 15])
        self.assertEqual(result.selected_roll, 15)
        self.assertEqual(result.total, 18)
        self.assertFalse(result.override_used)
        self.assertEqual(result.ability, "strength")
        self.assertIsNone(result.success)

    @patch("app.services.roll_resolution.roll_d20_pair", return_value=(5, 18))
    def test_advantage(self, _mock):
        result = resolve_ability_check(_player_stats(), "dexterity", "advantage")
        self.assertEqual(result.selected_roll, 18)
        self.assertEqual(result.rolls, [5, 18])
        self.assertEqual(result.modifier_used, 2)
        self.assertEqual(result.total, 20)

    @patch("app.services.roll_resolution.roll_d20_pair", return_value=(18, 5))
    def test_disadvantage(self, _mock):
        result = resolve_ability_check(_player_stats(), "dexterity", "disadvantage")
        self.assertEqual(result.selected_roll, 5)
        self.assertEqual(result.total, 7)

    @patch("app.services.roll_resolution.roll_d20_pair", return_value=(10, 10))
    def test_with_dc_success(self, _mock):
        result = resolve_ability_check(_player_stats(), "strength", dc=13)
        self.assertEqual(result.total, 13)
        self.assertTrue(result.success)

    @patch("app.services.roll_resolution.roll_d20_pair", return_value=(9, 9))
    def test_with_dc_failure(self, _mock):
        result = resolve_ability_check(_player_stats(), "strength", dc=13)
        self.assertEqual(result.total, 12)
        self.assertFalse(result.success)

    @patch("app.services.roll_resolution.roll_d20_pair", return_value=(10, 10))
    def test_bonus_override(self, _mock):
        result = resolve_ability_check(_player_stats(), "strength", bonus_override=7)
        self.assertEqual(result.modifier_used, 7)
        self.assertTrue(result.override_used)
        self.assertEqual(result.total, 17)


class TestSavingThrow(unittest.TestCase):
    @patch("app.services.roll_resolution.roll_d20_pair", return_value=(10, 10))
    def test_with_explicit_save_bonus(self, _mock):
        result = resolve_saving_throw(_player_stats(), "strength", dc=15)
        self.assertEqual(result.modifier_used, 5)  # explicit saving_throws["strength"]
        self.assertEqual(result.total, 15)
        self.assertTrue(result.success)

    @patch("app.services.roll_resolution.roll_d20_pair", return_value=(10, 10))
    def test_fallback_to_ability_mod(self, _mock):
        # "dexterity" not in saving_throws, falls back to ability mod (+2)
        result = resolve_saving_throw(_player_stats(), "dexterity")
        self.assertEqual(result.modifier_used, 2)
        self.assertFalse(result.override_used)

    @patch("app.services.roll_resolution.roll_d20_pair", return_value=(10, 10))
    def test_entity_save_override(self, _mock):
        result = resolve_saving_throw(_entity_stats(), "dexterity")
        self.assertEqual(result.modifier_used, 4)  # explicit saving_throws["dexterity"]

    @patch("app.services.roll_resolution.roll_d20_pair", return_value=(10, 10))
    def test_entity_save_fallback(self, _mock):
        result = resolve_saving_throw(_entity_stats(), "wisdom")
        self.assertEqual(result.modifier_used, -1)  # WIS 8 -> mod -1


class TestSkillCheck(unittest.TestCase):
    @patch("app.services.roll_resolution.roll_d20_pair", return_value=(12, 12))
    def test_with_explicit_skill_bonus(self, _mock):
        result = resolve_skill_check(_player_stats(), "athletics")
        self.assertEqual(result.modifier_used, 5)  # explicit skills["athletics"]
        self.assertEqual(result.skill, "athletics")

    @patch("app.services.roll_resolution.roll_d20_pair", return_value=(12, 12))
    def test_fallback_to_ability_mod(self, _mock):
        # "acrobatics" not in skills, falls back to DEX mod (+2)
        result = resolve_skill_check(_player_stats(), "acrobatics")
        self.assertEqual(result.modifier_used, 2)

    @patch("app.services.roll_resolution.roll_d20_pair", return_value=(12, 12))
    def test_entity_skill_override(self, _mock):
        result = resolve_skill_check(_entity_stats(), "stealth")
        self.assertEqual(result.modifier_used, 6)  # explicit skills["stealth"]

    @patch("app.services.roll_resolution.roll_d20_pair", return_value=(12, 12))
    def test_entity_skill_fallback(self, _mock):
        result = resolve_skill_check(_entity_stats(), "perception")
        self.assertEqual(result.modifier_used, -1)  # WIS 8 -> mod -1

    @patch("app.services.roll_resolution.roll_d20_pair", return_value=(10, 10))
    def test_with_dc(self, _mock):
        result = resolve_skill_check(_player_stats(), "athletics", dc=14)
        self.assertEqual(result.total, 15)
        self.assertTrue(result.success)


class TestInitiative(unittest.TestCase):
    @patch("app.services.roll_resolution.roll_d20_pair", return_value=(10, 10))
    def test_fallback_to_dex_mod(self, _mock):
        result = resolve_initiative(_player_stats())
        self.assertEqual(result.roll_type, "initiative")
        self.assertEqual(result.modifier_used, 2)  # DEX 14 -> mod +2
        self.assertEqual(result.total, 12)

    @patch("app.services.roll_resolution.roll_d20_pair", return_value=(10, 10))
    def test_explicit_initiative_bonus(self, _mock):
        result = resolve_initiative(_entity_stats())
        self.assertEqual(result.modifier_used, 3)  # explicit initiative_bonus=3
        self.assertEqual(result.total, 13)

    @patch("app.services.roll_resolution.roll_d20_pair", return_value=(10, 10))
    def test_bonus_override(self, _mock):
        result = resolve_initiative(_player_stats(), bonus_override=5)
        self.assertEqual(result.modifier_used, 5)
        self.assertTrue(result.override_used)


class TestAttackBase(unittest.TestCase):
    @patch("app.services.roll_resolution.roll_d20_pair", return_value=(15, 8))
    def test_hit(self, _mock):
        result = resolve_attack_base(_player_stats(), bonus_override=5, target_ac=18)
        self.assertEqual(result.total, 20)
        self.assertTrue(result.success)
        self.assertEqual(result.target_ac, 18)

    @patch("app.services.roll_resolution.roll_d20_pair", return_value=(10, 8))
    def test_miss(self, _mock):
        result = resolve_attack_base(_player_stats(), bonus_override=5, target_ac=18)
        self.assertEqual(result.total, 15)
        self.assertFalse(result.success)

    @patch("app.services.roll_resolution.roll_d20_pair", return_value=(20, 5))
    def test_natural_20_always_hits(self, _mock):
        result = resolve_attack_base(_player_stats(), bonus_override=0, target_ac=30)
        self.assertTrue(result.success)

    @patch("app.services.roll_resolution.roll_d20_pair", return_value=(1, 15))
    def test_natural_1_always_misses(self, _mock):
        result = resolve_attack_base(_player_stats(), bonus_override=20, target_ac=5)
        self.assertFalse(result.success)

    @patch("app.services.roll_resolution.roll_d20_pair", return_value=(15, 8))
    def test_no_target_ac_no_success(self, _mock):
        result = resolve_attack_base(_player_stats(), bonus_override=5)
        self.assertIsNone(result.success)

    @patch("app.services.roll_resolution.roll_d20_pair", return_value=(15, 8))
    def test_no_override_modifier_is_zero(self, _mock):
        result = resolve_attack_base(_player_stats())
        self.assertEqual(result.modifier_used, 0)
        self.assertFalse(result.override_used)


class TestResultStructure(unittest.TestCase):
    @patch("app.services.roll_resolution.roll_d20_pair", return_value=(12, 7))
    def test_result_has_all_fields(self, _mock):
        result = resolve_ability_check(_player_stats(), "strength", dc=10)
        self.assertIsNotNone(result.event_id)
        self.assertEqual(result.roll_type, "ability")
        self.assertEqual(result.actor_kind, "player")
        self.assertEqual(result.actor_ref_id, "user-1")
        self.assertEqual(result.actor_display_name, "Hero")
        self.assertEqual(len(result.rolls), 2)
        self.assertIsNotNone(result.timestamp)
        self.assertIn("+", result.formula)

    @patch("app.services.roll_resolution.roll_d20_pair", return_value=(12, 7))
    def test_negative_modifier_formula(self, _mock):
        result = resolve_ability_check(_player_stats(), "charisma")
        self.assertEqual(result.modifier_used, -1)
        self.assertIn("-", result.formula)


if __name__ == "__main__":
    unittest.main()
