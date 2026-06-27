import unittest

from app.services.dragonborn_breath_weapon import (
    compute_dragonborn_breath_weapon_damage_dice,
)


class DragonbornBreathWeaponDamageDiceTests(unittest.TestCase):
    def test_scales_by_level_bracket_phb_2014(self):
        # PHB 2014: dado aumenta nos níveis 6, 11 e 16.
        self.assertEqual(compute_dragonborn_breath_weapon_damage_dice(1), "2d6")
        self.assertEqual(compute_dragonborn_breath_weapon_damage_dice(5), "2d6")
        self.assertEqual(compute_dragonborn_breath_weapon_damage_dice(6), "3d6")
        self.assertEqual(compute_dragonborn_breath_weapon_damage_dice(10), "3d6")
        self.assertEqual(compute_dragonborn_breath_weapon_damage_dice(11), "4d6")
        self.assertEqual(compute_dragonborn_breath_weapon_damage_dice(15), "4d6")
        self.assertEqual(compute_dragonborn_breath_weapon_damage_dice(16), "5d6")
        self.assertEqual(compute_dragonborn_breath_weapon_damage_dice(20), "5d6")

    def test_clamps_non_positive_levels(self):
        self.assertEqual(compute_dragonborn_breath_weapon_damage_dice(0), "2d6")
        self.assertEqual(compute_dragonborn_breath_weapon_damage_dice(-3), "2d6")


if __name__ == "__main__":
    unittest.main()
