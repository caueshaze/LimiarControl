import unittest

from app.services.session_state_merge import merge_session_state_data


class SessionStateMergeTests(unittest.TestCase):
    def test_merge_keeps_runtime_rest_and_hp_while_filling_missing_fields(self):
        merged = merge_session_state_data(
            {
                "name": "Aela",
                "class": "fighter",
                "currentHP": 4,
                "maxHP": 12,
                "restState": "short_rest",
            },
            {
                "name": "Aela",
                "class": "fighter",
                "currentHP": 12,
                "maxHP": 12,
                "pendingLevelUp": False,
                "experiencePoints": 0,
            },
        )

        self.assertEqual(merged["restState"], "short_rest")
        self.assertEqual(merged["currentHP"], 4)
        self.assertEqual(merged["pendingLevelUp"], False)
        self.assertEqual(merged["experiencePoints"], 0)


if __name__ == "__main__":
    unittest.main()
