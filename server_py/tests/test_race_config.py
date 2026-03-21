import unittest

from app.services.race_config import normalize_race_state, validate_race_state


class RaceConfigTests(unittest.TestCase):
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
