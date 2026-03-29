import unittest

from app.services.progression_sync import merge_progression_session_state
from app.services.character_progression import (
    CharacterProgressionError,
    approve_level_up,
    deny_level_up,
    grant_experience,
    request_level_up,
)
from app.services.guardian_progression import apply_guardian_canonical_state
from app.services.sorcerer_progression import apply_sorcerer_canonical_state
from app.services.draconic_ancestry import resolve_elemental_affinity, resolve_draconic_lineage_state
from app.services.xp_thresholds import can_level_up, get_xp_for_next_level


class XpThresholdsTests(unittest.TestCase):
    def test_can_level_up_uses_phb_thresholds(self):
        self.assertFalse(can_level_up(1, 299))
        self.assertTrue(can_level_up(1, 300))
        self.assertFalse(can_level_up(2, 899))
        self.assertTrue(can_level_up(2, 900))

    def test_level_20_cannot_level_up(self):
        self.assertIsNone(get_xp_for_next_level(20))
        self.assertFalse(can_level_up(20, 999999))


class CharacterProgressionTests(unittest.TestCase):
    def test_grant_xp_adds_experience(self):
        data = grant_experience({"level": 1, "experiencePoints": 50}, 250)
        self.assertEqual(data["experiencePoints"], 300)

    def test_request_level_up_requires_enough_xp(self):
        with self.assertRaisesRegex(CharacterProgressionError, "Not enough XP"):
            request_level_up({"level": 1, "experiencePoints": 299, "pendingLevelUp": False})

    def test_request_level_up_sets_pending_flag(self):
        data = request_level_up({"level": 1, "experiencePoints": 300, "pendingLevelUp": False})
        self.assertTrue(data["pendingLevelUp"])
        self.assertEqual(data["level"], 1)

    def test_approve_level_up_increments_level(self):
        data = approve_level_up({"level": 1, "experiencePoints": 300, "pendingLevelUp": True})
        self.assertEqual(data["level"], 2)
        self.assertFalse(data["pendingLevelUp"])

    def test_deny_level_up_clears_pending_without_changing_level(self):
        data = deny_level_up({"level": 4, "experiencePoints": 2700, "pendingLevelUp": True})
        self.assertEqual(data["level"], 4)
        self.assertFalse(data["pendingLevelUp"])

    def test_approve_level_up_requires_pending_request(self):
        with self.assertRaisesRegex(CharacterProgressionError, "No pending level-up request"):
            approve_level_up({"level": 1, "experiencePoints": 300, "pendingLevelUp": False})

    def test_guardian_level_1_to_2_sets_fixed_style_spellcasting_and_features(self):
        data = approve_level_up({
            "class": "guardian",
            "level": 1,
            "experiencePoints": 300,
            "pendingLevelUp": True,
            "maxHP": 12,
            "currentHP": 12,
            "hitDiceTotal": 1,
            "hitDiceRemaining": 1,
            "abilities": {"dexterity": 16, "constitution": 14},
        })

        self.assertEqual(data["level"], 2)
        self.assertEqual(data["maxHP"], 20)
        self.assertEqual(data["fightingStyle"], "archery")
        self.assertEqual(data["subclass"], None)
        self.assertEqual(data["spellcasting"]["ability"], "wisdom")
        self.assertEqual(data["spellcasting"]["mode"], "known")
        self.assertEqual(data["spellcasting"]["slots"]["1"]["max"], 2)
        # Only hunters_mark is required by canonical state; player chooses other spells from catalog
        self.assertEqual(
            [spell["canonicalKey"] for spell in data["spellcasting"]["spells"]],
            ["hunters_mark"],
        )
        self.assertIn("fighting_style_archery", [feature["id"] for feature in data["classFeatures"]])

    def test_guardian_level_2_to_3_sets_hunter_subclass_and_colossus_slayer(self):
        data = approve_level_up({
            "class": "guardian",
            "level": 2,
            "experiencePoints": 900,
            "pendingLevelUp": True,
            "maxHP": 20,
            "currentHP": 20,
            "hitDiceTotal": 2,
            "hitDiceRemaining": 2,
            "abilities": {"dexterity": 16, "constitution": 14},
            "fightingStyle": "archery",
            "spellcasting": {"ability": "wisdom", "mode": "known", "slots": {"1": {"max": 2, "used": 1}}, "spells": []},
        })

        self.assertEqual(data["maxHP"], 28)
        self.assertEqual(data["subclass"], "hunter")
        self.assertEqual(data["spellcasting"]["slots"]["1"]["max"], 3)
        self.assertIn("subclass_hunter", [feature["id"] for feature in data["classFeatures"]])
        self.assertIn("hunter_colossus_slayer", [feature["id"] for feature in data["classFeatures"]])

    def test_guardian_level_1_has_no_spellcasting_in_canonical_state(self):
        data = apply_guardian_canonical_state({
            "class": "guardian",
            "level": 1,
            "spellcasting": {
                "ability": "wisdom",
                "mode": "known",
                "slots": {"1": {"max": 2, "used": 0}},
                "spells": [{"id": "x", "canonicalKey": "goodberry", "name": "Goodberry", "level": 1, "school": "Transmutation", "prepared": True, "notes": ""}],
            },
        })

        self.assertIsNone(data["spellcasting"])

    def test_guardian_preserves_player_chosen_spells_and_ensures_hunters_mark(self):
        """Player-chosen spells are preserved; hunters_mark is always present after canonical state."""
        data = apply_guardian_canonical_state({
            "class": "guardian",
            "level": 2,
            "spellcasting": {
                "ability": "wisdom",
                "mode": "known",
                "slots": {"1": {"max": 2, "used": 0}},
                "spells": [
                    {"id": "spell-1", "canonicalKey": "animal_friendship", "name": "Animal Friendship", "level": 1, "school": "Enchantment", "prepared": True, "notes": ""},
                    {"id": "spell-2", "canonicalKey": "goodberry", "name": "Goodberry", "level": 1, "school": "Transmutation", "prepared": True, "notes": ""},
                    {"id": "spell-3", "canonicalKey": "hunters_mark", "name": "Hunter's Mark", "level": 1, "school": "Divination", "prepared": True, "notes": ""},
                ],
            },
        })
        data = apply_guardian_canonical_state(data)
        spell_keys = [spell["canonicalKey"] for spell in data["spellcasting"]["spells"]]
        self.assertIn("hunters_mark", spell_keys)
        self.assertIn("animal_friendship", spell_keys)
        self.assertIn("goodberry", spell_keys)

    def test_guardian_level_3_to_4_applies_fixed_dexterity_asi(self):
        data = approve_level_up({
            "class": "guardian",
            "level": 3,
            "experiencePoints": 2700,
            "pendingLevelUp": True,
            "maxHP": 28,
            "currentHP": 28,
            "hitDiceTotal": 3,
            "hitDiceRemaining": 3,
            "abilities": {"dexterity": 16, "constitution": 14},
            "subclass": "hunter",
            "fightingStyle": "archery",
            "spellcasting": {"ability": "wisdom", "mode": "known", "slots": {"1": {"max": 3, "used": 0}}, "spells": []},
        })

        self.assertEqual(data["level"], 4)
        self.assertEqual(data["maxHP"], 36)
        self.assertEqual(data["abilities"]["dexterity"], 18)
        self.assertIn("asi_guardian_dexterity_2", [feature["id"] for feature in data["classFeatures"]])

    def test_sync_progression_session_state_preserves_damage_when_sheet_hp_delta_increases(self):
        updated = merge_progression_session_state({
            "currentHP": 10,
            "maxHP": 20,
            "hitDiceTotal": 2,
            "hitDiceRemaining": 1,
        }, {
            "level": 3,
            "experiencePoints": 900,
            "pendingLevelUp": False,
            "abilities": {"constitution": 14},
            "classFeatures": [],
            "maxHP": 28,
            "currentHP": 28,
            "hitDiceTotal": 3,
            "spellcasting": None,
        })

        self.assertEqual(updated["maxHP"], 28)
        self.assertEqual(updated["currentHP"], 18)

    def test_sync_progression_session_state_preserves_dragonborn_breath_weapon_uses(self):
        updated = merge_progression_session_state(
            {
                "currentHP": 12,
                "maxHP": 12,
                "classResources": {
                    "dragonbornBreathWeapon": {
                        "usesMax": 1,
                        "usesRemaining": 0,
                    },
                },
            },
            {
                "level": 4,
                "experiencePoints": 2700,
                "pendingLevelUp": False,
                "abilities": {"constitution": 14},
                "classFeatures": [],
                "maxHP": 20,
                "currentHP": 20,
                "hitDiceTotal": 4,
                "spellcasting": None,
                "classResources": {
                    "dragonbornBreathWeapon": {
                        "usesMax": 1,
                        "usesRemaining": 1,
                    },
                },
            },
        )

        self.assertEqual(
            updated["classResources"]["dragonbornBreathWeapon"],
            {"usesMax": 1, "usesRemaining": 0},
        )

    def test_draconic_bloodline_level_below_6_has_no_resistance(self):
        data = apply_sorcerer_canonical_state({
            "class": "sorcerer",
            "subclass": "draconic_bloodline",
            "level": 5,
            "subclassConfig": {"draconicAncestry": "red"},
            "abilities": {"charisma": 16},
        })

        lineage = resolve_draconic_lineage_state(data)
        self.assertEqual(lineage["damageType"], "fire")
        self.assertEqual(lineage["resistances"], [])
        self.assertFalse(lineage["hasElementalAffinity"])
        self.assertEqual([feature["id"] for feature in data["classFeatures"]], ["draconic_ancestry"])

    def test_draconic_bloodline_level_6_gains_resistance_and_elemental_affinity(self):
        data = apply_sorcerer_canonical_state({
            "class": "sorcerer",
            "subclass": "draconic_bloodline",
            "level": 6,
            "subclassConfig": {"draconicAncestry": "silver"},
            "abilities": {"charisma": 18},
        })

        lineage = resolve_draconic_lineage_state(data)
        self.assertEqual(lineage["damageType"], "cold")
        self.assertEqual(lineage["resistances"], ["cold"])
        self.assertTrue(lineage["hasElementalAffinity"])
        self.assertEqual(
            [feature["id"] for feature in data["classFeatures"]],
            ["draconic_ancestry", "elemental_affinity"],
        )

    def test_elemental_affinity_only_matches_spells_of_the_lineage_damage_type(self):
        data = {
            "class": "sorcerer",
            "subclass": "draconic_bloodline",
            "level": 6,
            "subclassConfig": {"draconicAncestry": "blue"},
            "abilities": {"charisma": 18},
        }

        self.assertEqual(
            resolve_elemental_affinity(data, "lightning"),
            {"eligible": True, "damageType": "lightning", "bonus": 4},
        )
        self.assertEqual(
            resolve_elemental_affinity(data, "fire"),
            {"eligible": False, "damageType": "lightning", "bonus": None},
        )


if __name__ == "__main__":
    unittest.main()
