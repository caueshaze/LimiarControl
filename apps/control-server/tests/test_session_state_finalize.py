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


if __name__ == "__main__":
    unittest.main()
