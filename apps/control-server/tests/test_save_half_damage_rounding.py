from __future__ import annotations

import unittest

from app.services.combat import CombatService


class SaveHalfDamageRoundingTests(unittest.TestCase):
    def test_half_damage_rounds_down_for_odd_damage(self):
        damage = CombatService._resolve_save_damage_amount(
            7,
            is_saved=True,
            save_success_outcome="half_damage",
        )
        self.assertEqual(damage, 3)

