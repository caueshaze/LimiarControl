from __future__ import annotations

import unittest

from app.services.item_condition_tags import normalize_item_condition_tags


class TestItemConditionTags(unittest.TestCase):
    def test_none_to_empty(self):
        self.assertEqual(normalize_item_condition_tags(None), [])

    def test_broken_valid(self):
        self.assertEqual(normalize_item_condition_tags(["broken"]), ["broken"])

    def test_dedup(self):
        self.assertEqual(
            normalize_item_condition_tags(["broken", "broken"]),
            ["broken"],
        )

    def test_uppercase_invalid(self):
        with self.assertRaises(ValueError):
            normalize_item_condition_tags(["BROKEN"])

    def test_portuguese_invalid(self):
        with self.assertRaises(ValueError):
            normalize_item_condition_tags(["quebrado"])

