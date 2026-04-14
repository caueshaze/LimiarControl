"""Phase F4/F5 — reach.py unit tests.

Tests the centralized melee reach module:
  - get_effective_reach           : clamp logic
  - resolve_melee_reach_cells     : weapon-property resolution
  - is_within_melee_reach         : Chebyshev distance check (single cell)
  - is_within_melee_reach_multi   : min-distance check across cell lists (F5)
"""
import unittest

from app.services.combat_service.reach import (
    DEFAULT_MELEE_REACH_CELLS,
    EXTENDED_REACH_CELLS,
    get_effective_reach,
    is_within_melee_reach,
    is_within_melee_reach_multi,
    resolve_weapon_attack_kind,
    resolve_melee_reach_cells,
)


# ─── constants ────────────────────────────────────────────────────────────────

class TestReachConstants(unittest.TestCase):
    def test_default_reach_is_one(self):
        self.assertEqual(DEFAULT_MELEE_REACH_CELLS, 1)

    def test_extended_reach_is_two(self):
        self.assertEqual(EXTENDED_REACH_CELLS, 2)

    def test_extended_is_greater_than_default(self):
        self.assertGreater(EXTENDED_REACH_CELLS, DEFAULT_MELEE_REACH_CELLS)


# ─── get_effective_reach ─────────────────────────────────────────────────────

class TestGetEffectiveReach(unittest.TestCase):
    def test_standard_reach_unchanged(self):
        self.assertEqual(get_effective_reach(1), 1)

    def test_extended_reach_unchanged(self):
        self.assertEqual(get_effective_reach(2), 2)

    def test_large_reach_unchanged(self):
        self.assertEqual(get_effective_reach(5), 5)

    def test_zero_clamped_to_one(self):
        self.assertEqual(get_effective_reach(0), 1)

    def test_negative_clamped_to_one(self):
        self.assertEqual(get_effective_reach(-1), 1)

    def test_large_negative_clamped_to_one(self):
        self.assertEqual(get_effective_reach(-100), 1)


# ─── resolve_melee_reach_cells ───────────────────────────────────────────────

class TestResolveMeleeReachCells(unittest.TestCase):
    def test_default_reach_is_one(self):
        self.assertEqual(resolve_melee_reach_cells(), 1)

    def test_no_reach_property_returns_one(self):
        self.assertEqual(resolve_melee_reach_cells(has_reach=False), 1)

    def test_reach_property_returns_two(self):
        self.assertEqual(resolve_melee_reach_cells(has_reach=True), 2)

    def test_return_value_is_int(self):
        self.assertIsInstance(resolve_melee_reach_cells(), int)
        self.assertIsInstance(resolve_melee_reach_cells(has_reach=True), int)

    def test_reach_cells_at_least_one(self):
        # Ensures the clamp in get_effective_reach is respected via this path
        self.assertGreaterEqual(resolve_melee_reach_cells(), 1)
        self.assertGreaterEqual(resolve_melee_reach_cells(has_reach=True), 1)


class TestResolveWeaponAttackKind(unittest.TestCase):
    def test_true_ranged_weapon_is_always_ranged(self):
        self.assertEqual(
            resolve_weapon_attack_kind(
                weapon_range_type="ranged",
                range_meters=18,
                range_long_meters=36,
                distance_meters=1.5,
            ),
            "ranged",
        )

    def test_thrown_profile_stays_melee_inside_reach(self):
        self.assertEqual(
            resolve_weapon_attack_kind(
                weapon_range_type="melee",
                range_meters=6,
                range_long_meters=18,
                distance_meters=1.5,
            ),
            "melee",
        )

    def test_thrown_profile_becomes_ranged_beyond_melee_reach(self):
        self.assertEqual(
            resolve_weapon_attack_kind(
                weapon_range_type="melee",
                range_meters=6,
                range_long_meters=18,
                distance_meters=6,
            ),
            "ranged",
        )


# ─── is_within_melee_reach ───────────────────────────────────────────────────

def _pos(x: int, y: int) -> dict[str, int]:
    return {"x": x, "y": y}


class TestIsWithinMeleeReach(unittest.TestCase):
    """Chebyshev-distance reach checks."""

    # ── same cell ─────────────────────────────────────────────────────────────
    def test_same_cell_within_reach_1(self):
        # distance = 0, always within any reach >= 0
        self.assertTrue(is_within_melee_reach(_pos(3, 3), _pos(3, 3), reach_cells=1))

    def test_same_cell_within_reach_2(self):
        self.assertTrue(is_within_melee_reach(_pos(0, 0), _pos(0, 0), reach_cells=2))

    # ── adjacent cardinal (distance = 1) ──────────────────────────────────────
    def test_adjacent_north_within_reach_1(self):
        self.assertTrue(is_within_melee_reach(_pos(3, 3), _pos(3, 4), reach_cells=1))

    def test_adjacent_south_within_reach_1(self):
        self.assertTrue(is_within_melee_reach(_pos(3, 3), _pos(3, 2), reach_cells=1))

    def test_adjacent_east_within_reach_1(self):
        self.assertTrue(is_within_melee_reach(_pos(3, 3), _pos(4, 3), reach_cells=1))

    def test_adjacent_west_within_reach_1(self):
        self.assertTrue(is_within_melee_reach(_pos(3, 3), _pos(2, 3), reach_cells=1))

    # ── adjacent diagonal (distance = 1 in Chebyshev) ─────────────────────────
    def test_diagonal_ne_within_reach_1(self):
        # Chebyshev: max(1,1) = 1 — diagonals count as 1 cell
        self.assertTrue(is_within_melee_reach(_pos(3, 3), _pos(4, 4), reach_cells=1))

    def test_diagonal_sw_within_reach_1(self):
        self.assertTrue(is_within_melee_reach(_pos(3, 3), _pos(2, 2), reach_cells=1))

    def test_diagonal_nw_within_reach_1(self):
        self.assertTrue(is_within_melee_reach(_pos(3, 3), _pos(2, 4), reach_cells=1))

    def test_diagonal_se_within_reach_1(self):
        self.assertTrue(is_within_melee_reach(_pos(3, 3), _pos(4, 2), reach_cells=1))

    # ── out of default reach (distance = 2) ───────────────────────────────────
    def test_two_cells_north_out_of_reach_1(self):
        self.assertFalse(is_within_melee_reach(_pos(3, 3), _pos(3, 5), reach_cells=1))

    def test_two_cells_east_out_of_reach_1(self):
        self.assertFalse(is_within_melee_reach(_pos(3, 3), _pos(5, 3), reach_cells=1))

    def test_diagonal_two_cells_out_of_reach_1(self):
        # Chebyshev: max(2,2) = 2 > 1
        self.assertFalse(is_within_melee_reach(_pos(0, 0), _pos(2, 2), reach_cells=1))

    # ── extended reach (reach_cells = 2) ──────────────────────────────────────
    def test_two_cells_north_within_reach_2(self):
        self.assertTrue(is_within_melee_reach(_pos(3, 3), _pos(3, 5), reach_cells=2))

    def test_two_cells_east_within_reach_2(self):
        self.assertTrue(is_within_melee_reach(_pos(3, 3), _pos(5, 3), reach_cells=2))

    def test_diagonal_two_cells_within_reach_2(self):
        # Chebyshev: max(2,2) = 2 == reach_cells
        self.assertTrue(is_within_melee_reach(_pos(0, 0), _pos(2, 2), reach_cells=2))

    def test_three_cells_out_of_reach_2(self):
        self.assertFalse(is_within_melee_reach(_pos(3, 3), _pos(3, 6), reach_cells=2))

    # ── boundary: exactly at reach ────────────────────────────────────────────
    def test_exactly_at_reach_boundary_is_valid(self):
        # Chebyshev distance = 1 with reach_cells = 1 → boundary, must be valid
        self.assertTrue(is_within_melee_reach(_pos(0, 0), _pos(1, 0), reach_cells=1))

    def test_one_beyond_reach_boundary_is_invalid(self):
        # Chebyshev distance = 2 with reach_cells = 1 → just outside
        self.assertFalse(is_within_melee_reach(_pos(0, 0), _pos(2, 0), reach_cells=1))

    # ── asymmetric positions ───────────────────────────────────────────────────
    def test_asymmetric_dx_gt_dy_uses_max(self):
        # dx=2, dy=1 → Chebyshev = 2, outside reach=1
        self.assertFalse(is_within_melee_reach(_pos(0, 0), _pos(2, 1), reach_cells=1))

    def test_asymmetric_dy_gt_dx_uses_max(self):
        # dx=1, dy=2 → Chebyshev = 2, outside reach=1
        self.assertFalse(is_within_melee_reach(_pos(0, 0), _pos(1, 2), reach_cells=1))

    def test_asymmetric_within_reach_2(self):
        # dx=2, dy=1 → Chebyshev = 2, within reach=2
        self.assertTrue(is_within_melee_reach(_pos(0, 0), _pos(2, 1), reach_cells=2))

    # ── symmetry ─────────────────────────────────────────────────────────────
    def test_symmetry_attacker_and_target_swapped(self):
        # Distance is symmetric: A→B == B→A
        a, b = _pos(1, 1), _pos(3, 3)
        self.assertEqual(
            is_within_melee_reach(a, b, reach_cells=2),
            is_within_melee_reach(b, a, reach_cells=2),
        )

    # ── negative coordinates (valid grid coords) ───────────────────────────────
    def test_negative_coordinates_adjacent(self):
        self.assertTrue(is_within_melee_reach(_pos(-1, -1), _pos(0, 0), reach_cells=1))

    def test_negative_coordinates_far(self):
        self.assertFalse(is_within_melee_reach(_pos(-5, -5), _pos(0, 0), reach_cells=1))


# ─── reach integration: resolve then check ───────────────────────────────────

class TestReachResolveAndCheck(unittest.TestCase):
    """Combine resolve_melee_reach_cells + is_within_melee_reach."""

    def test_default_reach_adjacent_is_valid(self):
        reach = resolve_melee_reach_cells(has_reach=False)
        self.assertTrue(is_within_melee_reach(_pos(0, 0), _pos(1, 0), reach))

    def test_default_reach_two_cells_is_invalid(self):
        reach = resolve_melee_reach_cells(has_reach=False)
        self.assertFalse(is_within_melee_reach(_pos(0, 0), _pos(2, 0), reach))

    def test_extended_reach_two_cells_is_valid(self):
        reach = resolve_melee_reach_cells(has_reach=True)
        self.assertTrue(is_within_melee_reach(_pos(0, 0), _pos(2, 0), reach))

    def test_extended_reach_three_cells_is_invalid(self):
        reach = resolve_melee_reach_cells(has_reach=True)
        self.assertFalse(is_within_melee_reach(_pos(0, 0), _pos(3, 0), reach))


# ─── is_within_melee_reach_multi ─────────────────────────────────────────────

class TestIsWithinMeleeReachMulti(unittest.TestCase):
    """Phase F5: multi-cell reach checks.

    is_within_melee_reach_multi uses the minimum Chebyshev distance
    between any pair of (attacker_cell, target_cell).
    """

    # ── 1×1 vs 1×1 — identical to single-cell function ───────────────────────

    def test_1x1_same_cell_within_reach_1(self):
        self.assertTrue(is_within_melee_reach_multi([_pos(3, 3)], [_pos(3, 3)], 1))

    def test_1x1_adjacent_cardinal_within_reach_1(self):
        self.assertTrue(is_within_melee_reach_multi([_pos(3, 3)], [_pos(4, 3)], 1))

    def test_1x1_adjacent_diagonal_within_reach_1(self):
        # Chebyshev: max(1,1) = 1
        self.assertTrue(is_within_melee_reach_multi([_pos(3, 3)], [_pos(4, 4)], 1))

    def test_1x1_two_cells_apart_out_of_reach_1(self):
        self.assertFalse(is_within_melee_reach_multi([_pos(0, 0)], [_pos(2, 0)], 1))

    def test_1x1_two_cells_apart_within_reach_2(self):
        self.assertTrue(is_within_melee_reach_multi([_pos(0, 0)], [_pos(2, 0)], 2))

    # ── large (2×2) attacker vs 1×1 target ───────────────────────────────────

    def test_large_attacker_adjacent_to_1x1_within_reach_1(self):
        # Large at (0,0)-(1,1); target at (2,0): min dist = 1 (from (1,0))
        from app.services.combat_service.entity_size import (
            SizeCategory, get_occupied_cells,
        )
        attacker_cells = get_occupied_cells(_pos(0, 0), SizeCategory.LARGE)
        target_cells = [_pos(2, 0)]
        self.assertTrue(is_within_melee_reach_multi(attacker_cells, target_cells, 1))

    def test_large_attacker_three_cells_from_1x1_out_of_reach_1(self):
        from app.services.combat_service.entity_size import (
            SizeCategory, get_occupied_cells,
        )
        attacker_cells = get_occupied_cells(_pos(0, 0), SizeCategory.LARGE)
        # Closest attacker cell (1,0) is 3 away from (4,0)
        target_cells = [_pos(4, 0)]
        self.assertFalse(is_within_melee_reach_multi(attacker_cells, target_cells, 1))

    def test_large_attacker_diagonal_touch_within_reach_1(self):
        from app.services.combat_service.entity_size import (
            SizeCategory, get_occupied_cells,
        )
        # Large at (0,0)-(1,1); target at (2,2): (1,1)→(2,2) = max(1,1) = 1
        attacker_cells = get_occupied_cells(_pos(0, 0), SizeCategory.LARGE)
        target_cells = [_pos(2, 2)]
        self.assertTrue(is_within_melee_reach_multi(attacker_cells, target_cells, 1))

    # ── 1×1 attacker vs large (2×2) target ───────────────────────────────────

    def test_1x1_attacker_adjacent_to_large_within_reach_1(self):
        from app.services.combat_service.entity_size import (
            SizeCategory, get_occupied_cells,
        )
        attacker_cells = [_pos(2, 0)]
        target_cells = get_occupied_cells(_pos(0, 0), SizeCategory.LARGE)
        self.assertTrue(is_within_melee_reach_multi(attacker_cells, target_cells, 1))

    # ── large vs large ────────────────────────────────────────────────────────

    def test_two_large_entities_adjacent_within_reach_1(self):
        from app.services.combat_service.entity_size import (
            SizeCategory, get_occupied_cells,
        )
        a_cells = get_occupied_cells(_pos(0, 0), SizeCategory.LARGE)
        b_cells = get_occupied_cells(_pos(2, 0), SizeCategory.LARGE)
        self.assertTrue(is_within_melee_reach_multi(a_cells, b_cells, 1))

    def test_two_large_entities_two_apart_out_of_reach_1(self):
        from app.services.combat_service.entity_size import (
            SizeCategory, get_occupied_cells,
        )
        a_cells = get_occupied_cells(_pos(0, 0), SizeCategory.LARGE)
        b_cells = get_occupied_cells(_pos(3, 0), SizeCategory.LARGE)
        self.assertFalse(is_within_melee_reach_multi(a_cells, b_cells, 1))

    # ── symmetry ─────────────────────────────────────────────────────────────
    def test_symmetry_attacker_and_target_swapped(self):
        from app.services.combat_service.entity_size import (
            SizeCategory, get_occupied_cells,
        )
        a = get_occupied_cells(_pos(0, 0), SizeCategory.LARGE)
        b = [_pos(3, 0)]
        self.assertEqual(
            is_within_melee_reach_multi(a, b, 1),
            is_within_melee_reach_multi(b, a, 1),
        )

    # ── error: empty list ─────────────────────────────────────────────────────
    def test_empty_attacker_cells_raises(self):
        with self.assertRaises(ValueError):
            is_within_melee_reach_multi([], [_pos(0, 0)], 1)

    def test_empty_target_cells_raises(self):
        with self.assertRaises(ValueError):
            is_within_melee_reach_multi([_pos(0, 0)], [], 1)

    # ── return type ───────────────────────────────────────────────────────────
    def test_return_type_is_bool(self):
        result = is_within_melee_reach_multi([_pos(0, 0)], [_pos(1, 0)], 1)
        self.assertIsInstance(result, bool)

    # ── boundary at reach ─────────────────────────────────────────────────────
    def test_exactly_at_reach_boundary_is_valid(self):
        # distance == reach_cells → valid
        self.assertTrue(is_within_melee_reach_multi([_pos(0, 0)], [_pos(2, 0)], 2))

    def test_one_beyond_reach_boundary_is_invalid(self):
        self.assertFalse(is_within_melee_reach_multi([_pos(0, 0)], [_pos(3, 0)], 2))


if __name__ == "__main__":
    unittest.main()
