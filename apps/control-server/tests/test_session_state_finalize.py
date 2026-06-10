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

    def test_active_armor_class_formula_beats_default_unarmored(self):
        armor_class = calculate_player_armor_class_from_state(
            {
                "abilities": {
                    "dexterity": 14,
                },
                "active_spell_effects": [
                    {
                        "id": "eff-mage-armor",
                        "kind": "spell_effect",
                        "metadata": {
                            "declarative_effect": {
                                "type": "armor_class_formula",
                                "params": {
                                    "base_value": 13,
                                    "ability": "dexterity",
                                    "requires_unarmored": True,
                                },
                            },
                        },
                    }
                ],
            }
        )

        self.assertEqual(armor_class, 15)

    def test_draconic_resilience_sets_unarmored_ac_to_13_plus_dex(self):
        state = finalize_session_state_data(
            {
                "class": "sorcerer",
                "subclass": "draconic_bloodline",
                "level": 1,
                "abilities": {"dexterity": 14, "constitution": 10},
                "currentHP": 6,
                "maxHP": 6,
            }
        )

        self.assertEqual(state["armorClass"], 15)
        self.assertEqual(state["armorClassSource"], "draconic_resilience")
        self.assertEqual(state["maxHP"], 7)

    def test_draconic_resilience_beats_default_unarmored_at_higher_dex(self):
        armor_class = calculate_player_armor_class_from_state(
            {
                "class": "sorcerer",
                "subclass": "draconic_bloodline",
                "abilities": {"dexterity": 18},
            }
        )

        self.assertEqual(armor_class, 17)

    def test_armor_class_formula_competes_as_base_not_additive_bonus(self):
        armor_class = calculate_player_armor_class_from_state(
            {
                "abilities": {
                    "dexterity": 14,
                },
                "equippedArmor": {
                    "name": "Leather",
                    "baseAC": 11,
                    "dexCap": None,
                    "armorType": "light",
                    "allowsDex": True,
                },
                "active_spell_effects": [
                    {
                        "id": "eff-mage-armor",
                        "kind": "spell_effect",
                        "metadata": {
                            "declarative_effect": {
                                "type": "armor_class_formula",
                                "params": {
                                    "base_value": 13,
                                    "ability": "dexterity",
                                    "requires_unarmored": True,
                                },
                            },
                        },
                    }
                ],
            }
        )

        self.assertEqual(armor_class, 13)

    def test_draconic_resilience_is_disabled_while_wearing_armor(self):
        armor_class = calculate_player_armor_class_from_state(
            {
                "class": "sorcerer",
                "subclass": "draconic_bloodline",
                "abilities": {"dexterity": 14},
                "equippedArmor": {
                    "name": "Leather",
                    "baseAC": 11,
                    "dexCap": None,
                    "armorType": "light",
                    "allowsDex": True,
                },
            }
        )

        self.assertEqual(armor_class, 13)

    def test_draconic_resilience_does_not_stack_with_mage_armor(self):
        armor_class = calculate_player_armor_class_from_state(
            {
                "class": "sorcerer",
                "subclass": "draconic_bloodline",
                "abilities": {"dexterity": 14},
                "active_spell_effects": [
                    {
                        "id": "eff-mage-armor",
                        "kind": "spell_effect",
                        "metadata": {
                            "declarative_effect": {
                                "type": "armor_class_formula",
                                "params": {
                                    "base_value": 13,
                                    "ability": "dexterity",
                                    "requires_unarmored": True,
                                },
                            },
                        },
                    }
                ],
            }
        )

        self.assertEqual(armor_class, 15)

    def test_draconic_resilience_does_not_stack_with_monk_unarmored_defense(self):
        armor_class = calculate_player_armor_class_from_state(
            {
                "class": "monk",
                "subclass": "draconic_bloodline",
                "abilities": {"dexterity": 14, "wisdom": 18},
            }
        )

        self.assertEqual(armor_class, 16)

    def test_draconic_resilience_does_not_stack_with_barbarian_unarmored_defense(self):
        armor_class = calculate_player_armor_class_from_state(
            {
                "class": "barbarian",
                "subclass": "draconic_bloodline",
                "abilities": {"dexterity": 14, "constitution": 18},
            }
        )

        self.assertEqual(armor_class, 16)

    def test_armor_class_formula_requires_unarmored(self):
        armor_class = calculate_player_armor_class_from_state(
            {
                "abilities": {
                    "dexterity": 16,
                },
                "equippedArmor": {
                    "name": "Scale Mail",
                    "baseAC": 14,
                    "dexCap": 2,
                    "armorType": "medium",
                    "allowsDex": True,
                },
                "active_spell_effects": [
                    {
                        "id": "eff-mage-armor",
                        "kind": "spell_effect",
                        "metadata": {
                            "declarative_effect": {
                                "type": "armor_class_formula",
                                "params": {
                                    "base_value": 13,
                                    "ability": "dexterity",
                                    "requires_unarmored": True,
                                },
                            },
                        },
                    }
                ],
            }
        )

        self.assertEqual(armor_class, 16)

    def test_armor_material_does_not_change_armor_class_metal_vs_leather(self):
        metal_state = {
            "abilities": {"dexterity": 14},
            "equippedArmor": {
                "name": "Chain Shirt",
                "baseAC": 13,
                "dexCap": 2,
                "armorType": "medium",
                "allowsDex": True,
                "armorMaterial": "metal",
            },
        }
        leather_state = {
            "abilities": {"dexterity": 14},
            "equippedArmor": {
                "name": "Leather",
                "baseAC": 13,
                "dexCap": 2,
                "armorType": "medium",
                "allowsDex": True,
                "armorMaterial": "leather",
            },
        }
        unknown_material_state = {
            "abilities": {"dexterity": 14},
            "equippedArmor": {
                "name": "Leather",
                "baseAC": 13,
                "dexCap": 2,
                "armorType": "medium",
                "allowsDex": True,
            },
        }

        self.assertEqual(calculate_player_armor_class_from_state(metal_state), 15)
        self.assertEqual(calculate_player_armor_class_from_state(leather_state), 15)
        self.assertEqual(calculate_player_armor_class_from_state(unknown_material_state), 15)

    def test_temp_ac_bonus_applies_after_formula_selection(self):
        armor_class = calculate_player_armor_class_from_state(
            {
                "abilities": {
                    "dexterity": 14,
                },
                "equippedShield": {"name": "Shield", "bonus": 2},
                "active_spell_effects": [
                    {
                        "id": "eff-mage-armor",
                        "kind": "spell_effect",
                        "metadata": {
                            "declarative_effect": {
                                "type": "armor_class_formula",
                                "params": {
                                    "base_value": 13,
                                    "ability": "dexterity",
                                    "requires_unarmored": True,
                                },
                            },
                        },
                    },
                    {
                        "id": "eff-ac",
                        "kind": "temp_ac_bonus",
                        "numeric_value": 1,
                    },
                ],
            }
        )

        self.assertEqual(armor_class, 18)

    def test_equal_formula_tie_breaking_is_stable_and_deterministic(self):
        armor_class = calculate_player_armor_class_from_state(
            {
                "abilities": {
                    "dexterity": 14,
                },
                "active_spell_effects": [
                    {
                        "id": "eff-b",
                        "kind": "spell_effect",
                        "metadata": {
                            "declarative_effect": {
                                "type": "armor_class_formula",
                                "params": {
                                    "base_value": 12,
                                    "ability": "dexterity",
                                },
                            },
                        },
                    },
                    {
                        "id": "eff-a",
                        "kind": "spell_effect",
                        "metadata": {
                            "declarative_effect": {
                                "type": "armor_class_formula",
                                "params": {
                                    "base_value": 12,
                                    "ability": "dexterity",
                                },
                            },
                        },
                    },
                ],
            }
        )

        self.assertEqual(armor_class, 14)

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

    def test_finalize_recomputes_draconic_resilience_hp_idempotently(self):
        state = {
            "class": "sorcerer",
            "subclass": "draconic_bloodline",
            "level": 6,
            "abilities": {"dexterity": 14, "constitution": 14},
            "currentHP": 20,
            "maxHP": 32,
        }

        once = finalize_session_state_data(state)
        twice = finalize_session_state_data(once)

        self.assertEqual(once["maxHP"], 44)
        self.assertEqual(twice["maxHP"], 44)
        self.assertEqual(once["currentHP"], 32)
        self.assertEqual(twice["currentHP"], 32)
        self.assertEqual(twice["maxHpBreakdown"]["draconicResilienceBonus"], 6)

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
