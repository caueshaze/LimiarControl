import unittest

from app.services.dragonborn_breath_weapon import (
    apply_dragonborn_breath_weapon_canonical_state,
    compute_dragonborn_breath_weapon_damage_dice,
    compute_dragonborn_breath_weapon_dc,
    resolve_dragonborn_breath_weapon_action_state,
)
from app.services.dragonborn_ancestry import resolve_dragonborn_lineage_state
from app.services.race_config import normalize_race_state, validate_race_state


class RaceConfigTests(unittest.TestCase):
    EXPECTED_DRAGONBORN_LINEAGES = {
        "black": {"damageType": "acid", "resistanceType": "acid", "breathWeaponShape": "line", "breathWeaponSaveType": "dexterity"},
        "blue": {"damageType": "lightning", "resistanceType": "lightning", "breathWeaponShape": "line", "breathWeaponSaveType": "dexterity"},
        "brass": {"damageType": "fire", "resistanceType": "fire", "breathWeaponShape": "line", "breathWeaponSaveType": "dexterity"},
        "bronze": {"damageType": "lightning", "resistanceType": "lightning", "breathWeaponShape": "line", "breathWeaponSaveType": "dexterity"},
        "copper": {"damageType": "acid", "resistanceType": "acid", "breathWeaponShape": "line", "breathWeaponSaveType": "dexterity"},
        "gold": {"damageType": "fire", "resistanceType": "fire", "breathWeaponShape": "cone", "breathWeaponSaveType": "constitution"},
        "green": {"damageType": "poison", "resistanceType": "poison", "breathWeaponShape": "cone", "breathWeaponSaveType": "constitution"},
        "red": {"damageType": "fire", "resistanceType": "fire", "breathWeaponShape": "cone", "breathWeaponSaveType": "constitution"},
        "silver": {"damageType": "cold", "resistanceType": "cold", "breathWeaponShape": "cone", "breathWeaponSaveType": "constitution"},
        "white": {"damageType": "cold", "resistanceType": "cold", "breathWeaponShape": "cone", "breathWeaponSaveType": "constitution"},
    }

    def test_dragonborn_requires_draconic_ancestry(self):
        ok, error = validate_race_state(
            {
                "race": "dragonborn",
                "raceConfig": None,
            }
        )

        self.assertFalse(ok)
        self.assertEqual(error, "draconicAncestry is required for dragonborn")

    def test_dragonborn_rejects_invalid_draconic_ancestry(self):
        ok, error = validate_race_state(
            {
                "race": "dragonborn",
                "raceConfig": {"draconicAncestry": "shadow"},
            }
        )

        self.assertFalse(ok)
        self.assertEqual(error, "draconicAncestry is invalid for dragonborn")

    def test_dragonborn_normalization_migrates_legacy_keys(self):
        normalized = normalize_race_state(
            "dragonborn",
            {
                "dragonbornAncestry": "red",
            },
        )

        self.assertEqual(
            normalized,
            {
                "race": "dragonborn",
                "raceConfig": {
                    "draconicAncestry": "red",
                },
            },
        )

    def test_dragonborn_lineage_derives_damage_resistance_and_breath_weapon(self):
        for ancestry, expected in self.EXPECTED_DRAGONBORN_LINEAGES.items():
            with self.subTest(ancestry=ancestry):
                lineage = resolve_dragonborn_lineage_state(
                    {
                        "race": "dragonborn",
                        "raceConfig": {"draconicAncestry": ancestry},
                    }
                )

                self.assertEqual(lineage["damageType"], expected["damageType"])
                self.assertEqual(lineage["resistanceType"], expected["resistanceType"])
                self.assertEqual(lineage["breathWeaponShape"], expected["breathWeaponShape"])
                self.assertEqual(lineage["breathWeaponSaveType"], expected["breathWeaponSaveType"])

    def test_dragonborn_breath_weapon_damage_scales_by_level(self):
        self.assertEqual(compute_dragonborn_breath_weapon_damage_dice(1), "2d6")
        self.assertEqual(compute_dragonborn_breath_weapon_damage_dice(5), "3d6")
        self.assertEqual(compute_dragonborn_breath_weapon_damage_dice(11), "4d6")
        self.assertEqual(compute_dragonborn_breath_weapon_damage_dice(17), "5d6")

    def test_dragonborn_breath_weapon_dc_uses_constitution_and_proficiency(self):
        dc = compute_dragonborn_breath_weapon_dc(
            {
                "level": 9,
                "abilities": {"constitution": 18},
            }
        )

        self.assertEqual(dc, 16)

    def test_dragonborn_breath_weapon_canonical_state_initializes_resource(self):
        normalized = apply_dragonborn_breath_weapon_canonical_state(
            {
                "level": 3,
                "race": "dragonborn",
                "raceConfig": {"draconicAncestry": "red"},
            }
        )
        action_state = resolve_dragonborn_breath_weapon_action_state(normalized)

        self.assertEqual(
            normalized["classResources"]["dragonbornBreathWeapon"],
            {"usesMax": 1, "usesRemaining": 1},
        )
        self.assertIsNotNone(action_state)
        self.assertEqual(action_state["damageType"], "fire")
        self.assertEqual(action_state["saveType"], "constitution")
        self.assertEqual(action_state["damageDice"], "2d6")

    def test_half_elf_requires_two_distinct_non_charisma_ability_choices(self):
        ok, error = validate_race_state(
            {
                "race": "half-elf",
                "raceConfig": {
                    "halfElfAbilityChoices": ["charisma", "wisdom"],
                    "halfElfSkillChoices": ["insight", "persuasion"],
                },
            }
        )

        self.assertFalse(ok)
        self.assertIn("ability choices", error or "")

    def test_half_elf_requires_two_distinct_skill_choices(self):
        ok, error = validate_race_state(
            {
                "race": "half-elf",
                "raceConfig": {
                    "halfElfAbilityChoices": ["constitution", "wisdom"],
                    "halfElfSkillChoices": ["insight", "insight"],
                },
            }
        )

        self.assertFalse(ok)
        self.assertIn("skill choices", error or "")

    def test_half_elf_normalization_keeps_valid_choices(self):
        normalized = normalize_race_state(
            "half-elf",
            {
                "halfElfAbilityChoices": ["constitution", "wisdom", "wisdom"],
                "halfElfSkillChoices": ["insight", "persuasion", "insight"],
            },
        )

        self.assertEqual(
            normalized,
            {
                "race": "half-elf",
                "raceConfig": {
                    "halfElfAbilityChoices": ["constitution", "wisdom"],
                    "halfElfSkillChoices": ["insight", "persuasion"],
                },
            },
        )


if __name__ == "__main__":
    unittest.main()
