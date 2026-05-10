import unittest

from app.services.session_state_finalize import (
    calculate_player_armor_class_from_state,
    finalize_session_state_data,
)


class SessionStateFinalizeTests(unittest.TestCase):
    def test_finalize_recalculates_armor_class_from_equipment(self):
        state = finalize_session_state_data(
            {
                "class": "fighter",
                "abilities": {
                    "strength": 14,
                    "dexterity": 14,
                    "constitution": 12,
                    "intelligence": 10,
                    "wisdom": 10,
                    "charisma": 8,
                },
                "equippedArmor": {
                    "name": "Scale Mail",
                    "baseAC": 14,
                    "dexCap": 2,
                    "armorType": "medium",
                    "allowsDex": True,
                },
                "equippedShield": {"name": "Shield", "bonus": 2},
                "miscACBonus": 1,
                "fightingStyle": "defense",
            }
        )

        self.assertEqual(state["armorClass"], 20)

    def test_calculate_armor_class_falls_back_to_unarmored_rules(self):
        armor_class = calculate_player_armor_class_from_state(
            {
                "class": "barbarian",
                "abilities": {
                    "strength": 14,
                    "dexterity": 14,
                    "constitution": 16,
                    "intelligence": 10,
                    "wisdom": 10,
                    "charisma": 8,
                },
                "equippedArmor": {
                    "name": "None",
                    "baseAC": 0,
                    "dexCap": None,
                    "armorType": "none",
                },
            }
        )

        self.assertEqual(armor_class, 15)

    def test_finalize_prunes_expired_timed_effects_when_game_time_is_provided(self):
        state = finalize_session_state_data(
            {
                "active_spell_effects": [
                    {
                        "id": "eff-expired",
                        "kind": "spell_effect",
                        "duration_type": "timed",
                        "expires_at_game_time_seconds": 3600,
                        "created_at": "2026-01-01T00:00:00+00:00",
                    },
                    {
                        "id": "eff-valid",
                        "kind": "spell_effect",
                        "duration_type": "timed",
                        "expires_at_game_time_seconds": 7200,
                        "created_at": "2026-01-01T00:00:00+00:00",
                    },
                ],
            },
            game_time_seconds=3600,
        )

        self.assertEqual(len(state["active_spell_effects"]), 1)
        self.assertEqual(state["active_spell_effects"][0]["id"], "eff-valid")

    def test_finalize_preserves_timed_effects_without_game_time(self):
        state = finalize_session_state_data(
            {
                "active_spell_effects": [
                    {
                        "id": "eff-expired",
                        "kind": "spell_effect",
                        "duration_type": "timed",
                        "expires_at_game_time_seconds": 3600,
                        "created_at": "2026-01-01T00:00:00+00:00",
                    }
                ],
            }
        )

        self.assertEqual(len(state["active_spell_effects"]), 1)
        self.assertEqual(state["active_spell_effects"][0]["id"], "eff-expired")

    def test_finalize_prunes_timed_effect_with_invalid_expiration(self):
        state = finalize_session_state_data(
            {
                "active_spell_effects": [
                    {
                        "id": "eff-invalid",
                        "kind": "spell_effect",
                        "duration_type": "timed",
                        "created_at_game_time_seconds": 100,
                        "created_at": "2026-01-01T00:00:00+00:00",
                    },
                    {
                        "id": "eff-valid",
                        "kind": "spell_effect",
                        "duration_type": "timed",
                        "expires_at_game_time_seconds": 7200,
                        "created_at": "2026-01-01T00:00:00+00:00",
                    },
                ],
            },
            game_time_seconds=3600,
        )

        self.assertEqual(len(state["active_spell_effects"]), 1)
        self.assertEqual(state["active_spell_effects"][0]["id"], "eff-valid")

    def test_finalize_keeps_timed_effect_without_created_at_game_time(self):
        state = finalize_session_state_data(
            {
                "active_spell_effects": [
                    {
                        "id": "eff-valid",
                        "kind": "spell_effect",
                        "duration_type": "timed",
                        "expires_at_game_time_seconds": 7200,
                        "created_at": "2026-01-01T00:00:00+00:00",
                    }
                ],
            },
            game_time_seconds=3600,
        )

        self.assertEqual(len(state["active_spell_effects"]), 1)
        self.assertEqual(state["active_spell_effects"][0]["id"], "eff-valid")


if __name__ == "__main__":
    unittest.main()
