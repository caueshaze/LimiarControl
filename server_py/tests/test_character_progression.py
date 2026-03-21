import unittest

from app.services.character_progression import (
    CharacterProgressionError,
    approve_level_up,
    deny_level_up,
    grant_experience,
    request_level_up,
)
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


if __name__ == "__main__":
    unittest.main()
