import unittest

from app.services.session_rest import (
    SessionRestError,
    apply_long_rest,
    end_rest,
    start_rest,
    use_hit_die,
)


class SessionRestTests(unittest.TestCase):
    def test_start_rest_marks_short_rest(self):
        data = start_rest({"restState": "exploration"}, "short_rest")
        self.assertEqual(data["restState"], "short_rest")

    def test_cannot_start_new_rest_when_one_is_active(self):
        with self.assertRaisesRegex(SessionRestError, "already active"):
            start_rest({"restState": "short_rest"}, "long_rest")

    def test_hit_die_requires_short_rest(self):
        with self.assertRaisesRegex(SessionRestError, "short rest"):
            use_hit_die({"restState": "exploration", "hitDiceRemaining": 1, "hitDiceType": "d8"})

    def test_hit_die_consumes_one_die_and_heals_with_constitution(self):
        next_data, outcome = use_hit_die(
            {
                "restState": "short_rest",
                "abilities": {"constitution": 14},
                "currentHP": 4,
                "maxHP": 15,
                "hitDiceType": "d8",
                "hitDiceTotal": 3,
                "hitDiceRemaining": 2,
            },
            roller=lambda _start, _end: 5,
        )
        self.assertEqual(next_data["hitDiceRemaining"], 1)
        self.assertEqual(next_data["currentHP"], 11)
        self.assertEqual(outcome["constitutionModifier"], 2)
        self.assertEqual(outcome["healingApplied"], 7)

    def test_end_short_rest_returns_to_exploration(self):
        next_data, ended_rest = end_rest({"restState": "short_rest"})
        self.assertEqual(ended_rest, "short_rest")
        self.assertEqual(next_data["restState"], "exploration")

    def test_end_short_rest_recharges_dragonborn_breath_weapon(self):
        next_data, ended_rest = end_rest(
            {
                "restState": "short_rest",
                "level": 4,
                "classResources": {
                    "dragonbornBreathWeapon": {"usesMax": 1, "usesRemaining": 0},
                },
            }
        )

        self.assertEqual(ended_rest, "short_rest")
        self.assertEqual(next_data["restState"], "exploration")
        self.assertEqual(
            next_data["classResources"]["dragonbornBreathWeapon"],
            {"usesMax": 1, "usesRemaining": 1},
        )

    def test_long_rest_restores_sorcery_points(self):
        # Font of Magic: a long rest restores all expended sorcery points.
        next_data = apply_long_rest(
            {
                "restState": "long_rest",
                "class": "sorcerer",
                "level": 6,
                "classResources": {
                    "sorceryPoints": {"usesMax": 6, "usesRemaining": 1},
                },
            }
        )
        self.assertEqual(
            next_data["classResources"]["sorceryPoints"],
            {"usesMax": 6, "usesRemaining": 6},
        )

    def test_short_rest_does_not_restore_sorcery_points(self):
        # Short rest must NOT restore sorcery points (RAW).
        next_data, ended_rest = end_rest(
            {
                "restState": "short_rest",
                "class": "sorcerer",
                "level": 6,
                "classResources": {
                    "sorceryPoints": {"usesMax": 6, "usesRemaining": 2},
                },
            }
        )
        self.assertEqual(ended_rest, "short_rest")
        self.assertEqual(
            next_data["classResources"]["sorceryPoints"],
            {"usesMax": 6, "usesRemaining": 2},
        )

    def test_long_rest_without_sorcery_points_is_safe(self):
        # Non-sorcerers (no sorceryPoints resource) must not break on long rest.
        next_data = apply_long_rest(
            {
                "restState": "long_rest",
                "class": "fighter",
                "level": 6,
                "maxHP": 40,
                "currentHP": 10,
            }
        )
        self.assertEqual(next_data["restState"], "exploration")
        self.assertNotIn("sorceryPoints", next_data.get("classResources", {}) or {})

    def test_long_rest_restores_core_resources(self):
        next_data = apply_long_rest(
            {
                "restState": "long_rest",
                "currentHP": 2,
                "maxHP": 18,
                "tempHP": 5,
                "hitDiceType": "d10",
                "hitDiceTotal": 5,
                "hitDiceRemaining": 1,
                "deathSaves": {"successes": 2, "failures": 1},
                "spellcasting": {
                    "ability": "wisdom",
                    "mode": "prepared",
                    "slots": {
                        1: {"max": 4, "used": 3},
                        2: {"max": 2, "used": 1},
                    },
                    "spells": [],
                },
            }
        )
        self.assertEqual(next_data["restState"], "exploration")
        self.assertEqual(next_data["currentHP"], 18)
        self.assertEqual(next_data["tempHP"], 0)
        self.assertEqual(next_data["hitDiceRemaining"], 3)
        self.assertEqual(next_data["deathSaves"], {"successes": 0, "failures": 0})
        self.assertEqual(next_data["spellcasting"]["slots"][1]["used"], 0)
        self.assertEqual(next_data["spellcasting"]["slots"][2]["used"], 0)

    def test_long_rest_does_not_revive_dead_character(self):
        next_data = apply_long_rest(
            {
                "restState": "long_rest",
                "currentHP": 0,
                "maxHP": 18,
                "tempHP": 5,
                "deathSaves": {"successes": 0, "failures": 3},
                "spellcasting": {
                    "ability": "wisdom",
                    "mode": "prepared",
                    "slots": {
                        1: {"max": 4, "used": 3},
                    },
                    "spells": [],
                },
            }
        )

        self.assertEqual(next_data["currentHP"], 0)
        self.assertEqual(next_data["deathSaves"], {"successes": 0, "failures": 3})
        self.assertEqual(next_data["tempHP"], 0)
        self.assertEqual(next_data["spellcasting"]["slots"][1]["used"], 0)

    def test_long_rest_keeps_goodberry_until_temporal_expiration(self):
        next_data = apply_long_rest(
            {
                "restState": "long_rest",
                "currentHP": 4,
                "maxHP": 8,
                "inventory": [
                    {"id": "inv-1", "name": "Bom Fruto", "canonicalKey": "goodberry", "quantity": 7},
                    {"id": "inv-2", "name": "Poção de Cura", "canonicalKey": "potion_healing", "quantity": 1},
                ],
            }
        )

        self.assertEqual(
            next_data["inventory"],
            [
                {"id": "inv-1", "name": "Bom Fruto", "canonicalKey": "goodberry", "quantity": 7},
                {"id": "inv-2", "name": "Poção de Cura", "canonicalKey": "potion_healing", "quantity": 1},
            ],
        )

    def test_long_rest_clears_persisted_active_spell_effects(self):
        owl_wisdom = {
            "id": "eff-1",
            "kind": "spell_effect",
            "duration_type": "manual",
            "metadata": {
                "source_spell_name": "Owl's Wisdom",
                "declarative_effect": {
                    "type": "passive_skill_bonus",
                    "params": {"skill": "perception", "bonus": 5},
                },
            },
        }
        next_data = apply_long_rest(
            {
                "restState": "long_rest",
                "currentHP": 4,
                "maxHP": 8,
                "active_spell_effects": [owl_wisdom],
            }
        )

        self.assertNotIn("active_spell_effects", next_data)
        self.assertEqual(next_data["currentHP"], 8)

    def test_long_rest_with_no_active_spell_effects_is_safe(self):
        next_data = apply_long_rest(
            {
                "restState": "long_rest",
                "currentHP": 4,
                "maxHP": 8,
            }
        )

        self.assertNotIn("active_spell_effects", next_data)
        self.assertEqual(next_data["currentHP"], 8)

    def test_long_rest_preserves_other_state_json_fields(self):
        next_data = apply_long_rest(
            {
                "restState": "long_rest",
                "currentHP": 4,
                "maxHP": 8,
                "active_spell_effects": [{"id": "eff-1"}],
                "customField": "should survive",
            }
        )

        self.assertNotIn("active_spell_effects", next_data)
        self.assertEqual(next_data["customField"], "should survive")


    def test_long_rest_clears_concentration_from_active_spell_effects(self):
        from app.services.combat_service.persistent_effects import derive_active_concentration

        conc_effect = {
            "id": "eff-conc",
            "kind": "spell_effect",
            "duration_type": "manual",
            "metadata": {
                "concentration": True,
                "concentration_group": "grp-1",
                "source_spell_name": "Bless",
            },
        }
        next_data = apply_long_rest(
            {
                "restState": "long_rest",
                "currentHP": 4,
                "maxHP": 8,
                "active_spell_effects": [conc_effect],
            }
        )

        self.assertNotIn("active_spell_effects", next_data)
        self.assertIsNone(derive_active_concentration(next_data))

    def test_long_rest_clears_until_long_rest_effects(self):
        effect = {
            "id": "eff-1",
            "kind": "spell_effect",
            "duration_type": "until_long_rest",
            "metadata": {"source_spell_name": "Bless"},
        }
        next_data = apply_long_rest(
            {
                "restState": "long_rest",
                "currentHP": 4,
                "maxHP": 8,
                "active_spell_effects": [effect],
            }
        )

        self.assertNotIn("active_spell_effects", next_data)

    def test_long_rest_clears_until_short_rest_effects(self):
        effect = {
            "id": "eff-1",
            "kind": "spell_effect",
            "duration_type": "until_short_rest",
            "metadata": {"source_spell_name": "Shield of Faith"},
        }
        next_data = apply_long_rest(
            {
                "restState": "long_rest",
                "currentHP": 4,
                "maxHP": 8,
                "active_spell_effects": [effect],
            }
        )

        self.assertNotIn("active_spell_effects", next_data)

    def test_long_rest_preserves_until_removed_effects(self):
        effect = {
            "id": "eff-1",
            "kind": "spell_effect",
            "duration_type": "until_removed",
            "metadata": {"source_spell_name": "Owl's Wisdom"},
        }
        next_data = apply_long_rest(
            {
                "restState": "long_rest",
                "currentHP": 4,
                "maxHP": 8,
                "active_spell_effects": [effect],
            }
        )

        self.assertIn("active_spell_effects", next_data)
        self.assertEqual(len(next_data["active_spell_effects"]), 1)
        self.assertEqual(next_data["active_spell_effects"][0]["id"], "eff-1")

    def test_long_rest_clears_mixed_lifecycle_effects_selectively(self):
        until_long = {
            "id": "eff-long",
            "kind": "spell_effect",
            "duration_type": "until_long_rest",
            "metadata": {},
        }
        until_removed = {
            "id": "eff-perm",
            "kind": "spell_effect",
            "duration_type": "until_removed",
            "metadata": {},
        }
        next_data = apply_long_rest(
            {
                "restState": "long_rest",
                "currentHP": 4,
                "maxHP": 8,
                "active_spell_effects": [until_long, until_removed],
            }
        )

        self.assertIn("active_spell_effects", next_data)
        self.assertEqual(len(next_data["active_spell_effects"]), 1)
        self.assertEqual(next_data["active_spell_effects"][0]["id"], "eff-perm")

    def test_short_rest_clears_until_short_rest_effects(self):
        from app.services.session_rest import end_rest

        effect = {
            "id": "eff-1",
            "kind": "spell_effect",
            "duration_type": "until_short_rest",
            "metadata": {"source_spell_name": "Cat's Grace"},
        }
        next_data, ended = end_rest(
            {
                "restState": "short_rest",
                "currentHP": 4,
                "maxHP": 8,
                "active_spell_effects": [effect],
            }
        )

        self.assertEqual(ended, "short_rest")
        self.assertNotIn("active_spell_effects", next_data)

    def test_short_rest_preserves_until_long_rest_effects(self):
        from app.services.session_rest import end_rest

        effect = {
            "id": "eff-1",
            "kind": "spell_effect",
            "duration_type": "until_long_rest",
            "metadata": {"source_spell_name": "Bless"},
        }
        next_data, ended = end_rest(
            {
                "restState": "short_rest",
                "currentHP": 4,
                "maxHP": 8,
                "active_spell_effects": [effect],
            }
        )

        self.assertEqual(ended, "short_rest")
        self.assertIn("active_spell_effects", next_data)
        self.assertEqual(len(next_data["active_spell_effects"]), 1)

    def test_short_rest_preserves_until_removed_effects(self):
        from app.services.session_rest import end_rest

        effect = {
            "id": "eff-1",
            "kind": "spell_effect",
            "duration_type": "until_removed",
            "metadata": {"source_spell_name": "Owl's Wisdom"},
        }
        next_data, ended = end_rest(
            {
                "restState": "short_rest",
                "currentHP": 4,
                "maxHP": 8,
                "active_spell_effects": [effect],
            }
        )

        self.assertEqual(ended, "short_rest")
        self.assertIn("active_spell_effects", next_data)
        self.assertEqual(len(next_data["active_spell_effects"]), 1)

    def test_short_rest_preserves_manual_effects(self):
        from app.services.session_rest import end_rest

        effect = {
            "id": "eff-1",
            "kind": "spell_effect",
            "duration_type": "manual",
            "metadata": {"source_spell_name": "Owl's Wisdom"},
        }
        next_data, ended = end_rest(
            {
                "restState": "short_rest",
                "currentHP": 4,
                "maxHP": 8,
                "active_spell_effects": [effect],
            }
        )

        self.assertEqual(ended, "short_rest")
        self.assertIn("active_spell_effects", next_data)
        self.assertEqual(len(next_data["active_spell_effects"]), 1)


if __name__ == "__main__":
    unittest.main()
