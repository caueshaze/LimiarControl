from __future__ import annotations

import unittest

from app.services.canonical_keys import canonical_keys_equal, normalize_canonical_key
from app.services.spell_keys import normalize_spell_key, spell_keys_equal


class CanonicalKeyNormalizationTests(unittest.TestCase):
    def test_normalize_canonical_key(self):
        self.assertEqual(normalize_canonical_key(None), "")
        self.assertEqual(normalize_canonical_key(""), "")
        self.assertEqual(normalize_canonical_key(" Spider Climb "), "spider_climb")
        self.assertEqual(normalize_canonical_key("spider climb"), "spider_climb")
        self.assertEqual(normalize_canonical_key("spider-climb"), "spider_climb")
        self.assertEqual(normalize_canonical_key("spider__climb"), "spider_climb")
        self.assertEqual(normalize_canonical_key("spider - climb"), "spider_climb")
        self.assertEqual(
            normalize_canonical_key("Protection from Evil and Good"),
            "protection_from_evil_and_good",
        )

    def test_canonical_key_equality(self):
        self.assertTrue(canonical_keys_equal("Spider Climb", "spider_climb"))
        self.assertTrue(canonical_keys_equal("spider-climb", "spider climb"))
        self.assertFalse(canonical_keys_equal("jump", "blur"))


class SpellKeyNormalizationTests(unittest.TestCase):
    def test_spell_key_wrapper(self):
        self.assertEqual(normalize_spell_key("Spider Climb"), "spider_climb")
        self.assertTrue(spell_keys_equal("spider-climb", "spider_climb"))


if __name__ == "__main__":
    unittest.main()
