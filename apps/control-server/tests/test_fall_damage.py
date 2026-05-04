from __future__ import annotations

import unittest

from app.services.combat_service.fall_damage import (
    FALL_DAMAGE_DIE_SIDES,
    FALL_DAMAGE_METERS_PER_DIE,
    FALL_DAMAGE_TYPE,
    MAX_FALL_DAMAGE_DICE,
    FallDamageComputation,
    compute_fall_damage,
)


class TestComputeFallDamage(unittest.TestCase):
    def _assert_no_damage(self, result: FallDamageComputation, original_height: float) -> None:
        self.assertFalse(result.causes_damage)
        self.assertEqual(result.dice_count, 0)
        self.assertIsNone(result.damage_formula)
        self.assertEqual(result.height_meters, original_height)
        self.assertEqual(result.effective_height_meters, max(0, original_height))

    def _assert_damage(self, result: FallDamageComputation, expected_dice: int, original_height: float) -> None:
        self.assertTrue(result.causes_damage)
        self.assertEqual(result.dice_count, expected_dice)
        self.assertEqual(result.damage_formula, f"{expected_dice}d{FALL_DAMAGE_DIE_SIDES}")
        self.assertEqual(result.dice_sides, FALL_DAMAGE_DIE_SIDES)
        self.assertEqual(result.damage_type, FALL_DAMAGE_TYPE)
        self.assertEqual(result.height_meters, original_height)
        self.assertEqual(result.effective_height_meters, max(0, original_height))

    def test_zero_height(self):
        self._assert_no_damage(compute_fall_damage(0), 0)

    def test_below_threshold_1_5(self):
        self._assert_no_damage(compute_fall_damage(1.5), 1.5)

    def test_below_threshold_2_99(self):
        self._assert_no_damage(compute_fall_damage(2.99), 2.99)

    def test_exactly_3m_is_1d6(self):
        self._assert_damage(compute_fall_damage(3), 1, 3)

    def test_5_99m_still_1d6(self):
        self._assert_damage(compute_fall_damage(5.99), 1, 5.99)

    def test_6m_is_2d6(self):
        self._assert_damage(compute_fall_damage(6), 2, 6)

    def test_9m_is_3d6(self):
        self._assert_damage(compute_fall_damage(9), 3, 9)

    def test_60m_hits_cap_20d6(self):
        self._assert_damage(compute_fall_damage(60), 20, 60)

    def test_90m_capped_at_20d6(self):
        self._assert_damage(compute_fall_damage(90), 20, 90)

    def test_negative_height_normalizes_to_zero(self):
        result = compute_fall_damage(-1)
        self._assert_no_damage(result, -1)
        self.assertEqual(result.effective_height_meters, 0)

    def test_constants_are_correct(self):
        self.assertEqual(FALL_DAMAGE_METERS_PER_DIE, 3)
        self.assertEqual(FALL_DAMAGE_DIE_SIDES, 6)
        self.assertEqual(MAX_FALL_DAMAGE_DICE, 20)
        self.assertEqual(FALL_DAMAGE_TYPE, "bludgeoning")


if __name__ == "__main__":
    unittest.main()
