"""Phase F5 — Entity size model unit tests.

Tests cover:
  - SizeCategory enum values
  - size_footprint_cells() for all categories
  - get_occupied_cells() layout, count, anchor inclusion
  - normalize_size_category() round-trips, case insensitivity, defaults
  - min_chebyshev_distance() for single cells, multi-cell footprints,
    adjacency, touching corners, symmetry, and error cases
"""
import unittest

from app.services.combat_service.entity_size import (
    SizeCategory,
    get_occupied_cells,
    min_chebyshev_distance,
    normalize_size_category,
    size_footprint_cells,
)


def _pos(x: int, y: int) -> dict[str, int]:
    return {"x": x, "y": y}


# ─── SizeCategory enum ────────────────────────────────────────────────────────

class TestSizeCategoryEnum(unittest.TestCase):

    def test_all_categories_exist(self):
        names = {m.name for m in SizeCategory}
        self.assertEqual(names, {"TINY", "SMALL", "MEDIUM", "LARGE", "HUGE", "GARGANTUAN"})

    def test_values_are_lowercase_strings(self):
        for cat in SizeCategory:
            with self.subTest(cat=cat):
                self.assertEqual(cat.value, cat.value.lower())

    def test_tiny_value(self):
        self.assertEqual(SizeCategory.TINY.value, "tiny")

    def test_small_value(self):
        self.assertEqual(SizeCategory.SMALL.value, "small")

    def test_medium_value(self):
        self.assertEqual(SizeCategory.MEDIUM.value, "medium")

    def test_large_value(self):
        self.assertEqual(SizeCategory.LARGE.value, "large")

    def test_huge_value(self):
        self.assertEqual(SizeCategory.HUGE.value, "huge")

    def test_gargantuan_value(self):
        self.assertEqual(SizeCategory.GARGANTUAN.value, "gargantuan")

    def test_is_string_enum(self):
        self.assertIsInstance(SizeCategory.MEDIUM, str)


# ─── size_footprint_cells ─────────────────────────────────────────────────────

class TestSizeFootprintCells(unittest.TestCase):

    def test_tiny_is_one(self):
        self.assertEqual(size_footprint_cells(SizeCategory.TINY), 1)

    def test_small_is_one(self):
        self.assertEqual(size_footprint_cells(SizeCategory.SMALL), 1)

    def test_medium_is_one(self):
        self.assertEqual(size_footprint_cells(SizeCategory.MEDIUM), 1)

    def test_large_is_two(self):
        self.assertEqual(size_footprint_cells(SizeCategory.LARGE), 2)

    def test_huge_is_three(self):
        self.assertEqual(size_footprint_cells(SizeCategory.HUGE), 3)

    def test_gargantuan_is_four(self):
        self.assertEqual(size_footprint_cells(SizeCategory.GARGANTUAN), 4)

    def test_non_large_sizes_are_one(self):
        for cat in (SizeCategory.TINY, SizeCategory.SMALL, SizeCategory.MEDIUM):
            with self.subTest(cat=cat):
                self.assertEqual(size_footprint_cells(cat), 1)

    def test_large_and_bigger_are_greater_than_one(self):
        for cat in (SizeCategory.LARGE, SizeCategory.HUGE, SizeCategory.GARGANTUAN):
            with self.subTest(cat=cat):
                self.assertGreater(size_footprint_cells(cat), 1)

    def test_return_type_is_int(self):
        for cat in SizeCategory:
            with self.subTest(cat=cat):
                self.assertIsInstance(size_footprint_cells(cat), int)


# ─── get_occupied_cells ───────────────────────────────────────────────────────

class TestGetOccupiedCells(unittest.TestCase):

    # ── medium (1×1) ─────────────────────────────────────────────────────────
    def test_medium_at_origin_returns_single_cell(self):
        cells = get_occupied_cells(_pos(0, 0), SizeCategory.MEDIUM)
        self.assertEqual(cells, [_pos(0, 0)])

    def test_medium_count_is_one(self):
        self.assertEqual(len(get_occupied_cells(_pos(5, 3), SizeCategory.MEDIUM)), 1)

    def test_medium_anchor_is_only_cell(self):
        anchor = _pos(7, 2)
        cells = get_occupied_cells(anchor, SizeCategory.MEDIUM)
        self.assertIn(anchor, cells)

    def test_tiny_at_origin_is_single_cell(self):
        self.assertEqual(get_occupied_cells(_pos(0, 0), SizeCategory.TINY), [_pos(0, 0)])

    def test_small_at_origin_is_single_cell(self):
        self.assertEqual(get_occupied_cells(_pos(0, 0), SizeCategory.SMALL), [_pos(0, 0)])

    # ── large (2×2) ───────────────────────────────────────────────────────────
    def test_large_at_origin_count_is_four(self):
        self.assertEqual(len(get_occupied_cells(_pos(0, 0), SizeCategory.LARGE)), 4)

    def test_large_at_origin_contains_all_corners(self):
        cells = get_occupied_cells(_pos(0, 0), SizeCategory.LARGE)
        self.assertIn(_pos(0, 0), cells)
        self.assertIn(_pos(1, 0), cells)
        self.assertIn(_pos(0, 1), cells)
        self.assertIn(_pos(1, 1), cells)

    def test_large_at_offset_applies_correctly(self):
        cells = get_occupied_cells(_pos(3, 5), SizeCategory.LARGE)
        self.assertIn(_pos(3, 5), cells)
        self.assertIn(_pos(4, 5), cells)
        self.assertIn(_pos(3, 6), cells)
        self.assertIn(_pos(4, 6), cells)

    def test_large_anchor_always_included(self):
        anchor = _pos(10, 10)
        cells = get_occupied_cells(anchor, SizeCategory.LARGE)
        self.assertIn(anchor, cells)

    def test_large_cells_are_unique(self):
        cells = get_occupied_cells(_pos(0, 0), SizeCategory.LARGE)
        self.assertEqual(len(cells), len({(c["x"], c["y"]) for c in cells}))

    # ── huge (3×3) ────────────────────────────────────────────────────────────
    def test_huge_count_is_nine(self):
        self.assertEqual(len(get_occupied_cells(_pos(0, 0), SizeCategory.HUGE)), 9)

    def test_huge_contains_all_cells(self):
        cells = get_occupied_cells(_pos(0, 0), SizeCategory.HUGE)
        expected = [_pos(x, y) for y in range(3) for x in range(3)]
        for cell in expected:
            with self.subTest(cell=cell):
                self.assertIn(cell, cells)

    def test_huge_anchor_always_included(self):
        anchor = _pos(2, 4)
        cells = get_occupied_cells(anchor, SizeCategory.HUGE)
        self.assertIn(anchor, cells)

    # ── gargantuan (4×4) ──────────────────────────────────────────────────────
    def test_gargantuan_count_is_sixteen(self):
        self.assertEqual(len(get_occupied_cells(_pos(0, 0), SizeCategory.GARGANTUAN)), 16)

    def test_gargantuan_cells_unique(self):
        cells = get_occupied_cells(_pos(1, 1), SizeCategory.GARGANTUAN)
        self.assertEqual(len(cells), len({(c["x"], c["y"]) for c in cells}))

    # ── cell count = footprint² ───────────────────────────────────────────────
    def test_cell_count_matches_footprint_squared(self):
        for cat in SizeCategory:
            with self.subTest(cat=cat):
                side = size_footprint_cells(cat)
                cells = get_occupied_cells(_pos(0, 0), cat)
                self.assertEqual(len(cells), side * side)

    # ── negative coordinates ──────────────────────────────────────────────────
    def test_large_with_negative_anchor(self):
        cells = get_occupied_cells(_pos(-1, -1), SizeCategory.LARGE)
        self.assertIn(_pos(-1, -1), cells)
        self.assertIn(_pos(0, -1), cells)
        self.assertIn(_pos(-1, 0), cells)
        self.assertIn(_pos(0, 0), cells)


# ─── normalize_size_category ─────────────────────────────────────────────────

class TestNormalizeSizeCategory(unittest.TestCase):

    def test_valid_lowercase_round_trips(self):
        for cat in SizeCategory:
            with self.subTest(cat=cat):
                self.assertEqual(normalize_size_category(cat.value), cat)

    def test_case_insensitive_upper(self):
        self.assertEqual(normalize_size_category("LARGE"), SizeCategory.LARGE)

    def test_case_insensitive_mixed(self):
        self.assertEqual(normalize_size_category("Huge"), SizeCategory.HUGE)

    def test_none_returns_default(self):
        self.assertEqual(normalize_size_category(None), SizeCategory.MEDIUM)

    def test_empty_string_returns_default(self):
        self.assertEqual(normalize_size_category(""), SizeCategory.MEDIUM)

    def test_whitespace_only_returns_default(self):
        self.assertEqual(normalize_size_category("   "), SizeCategory.MEDIUM)

    def test_unknown_string_returns_default(self):
        self.assertEqual(normalize_size_category("colossal"), SizeCategory.MEDIUM)

    def test_custom_default(self):
        self.assertEqual(
            normalize_size_category(None, default=SizeCategory.LARGE),
            SizeCategory.LARGE,
        )

    def test_return_type_is_size_category(self):
        self.assertIsInstance(normalize_size_category("large"), SizeCategory)

    def test_whitespace_stripped(self):
        self.assertEqual(normalize_size_category("  large  "), SizeCategory.LARGE)


# ─── min_chebyshev_distance ───────────────────────────────────────────────────

class TestMinChebyshevDistance(unittest.TestCase):

    # ── same cell ─────────────────────────────────────────────────────────────
    def test_same_cell_distance_is_zero(self):
        cells = [_pos(3, 3)]
        self.assertEqual(min_chebyshev_distance(cells, cells), 0)

    def test_same_cell_in_separate_lists(self):
        self.assertEqual(min_chebyshev_distance([_pos(1, 1)], [_pos(1, 1)]), 0)

    # ── 1×1 adjacency ────────────────────────────────────────────────────────
    def test_adjacent_cardinal_distance_one(self):
        self.assertEqual(
            min_chebyshev_distance([_pos(0, 0)], [_pos(1, 0)]), 1
        )

    def test_adjacent_diagonal_distance_one(self):
        self.assertEqual(
            min_chebyshev_distance([_pos(0, 0)], [_pos(1, 1)]), 1
        )

    def test_two_apart_distance_two(self):
        self.assertEqual(
            min_chebyshev_distance([_pos(0, 0)], [_pos(2, 0)]), 2
        )

    # ── multi-cell: 1×1 vs 2×2 ───────────────────────────────────────────────
    def test_1x1_adjacent_to_large(self):
        # 2×2 at (0,0)-(1,1); 1×1 at (2,0): distance from (1,0)→(2,0) = 1
        large_cells = get_occupied_cells(_pos(0, 0), SizeCategory.LARGE)
        small_cells = [_pos(2, 0)]
        self.assertEqual(min_chebyshev_distance(large_cells, small_cells), 1)

    def test_1x1_two_cells_from_large(self):
        # 2×2 at (0,0)-(1,1); 1×1 at (3,0): closest is (1,0)→(3,0) = 2
        large_cells = get_occupied_cells(_pos(0, 0), SizeCategory.LARGE)
        small_cells = [_pos(3, 0)]
        self.assertEqual(min_chebyshev_distance(large_cells, small_cells), 2)

    def test_large_touching_small_diagonal(self):
        # 2×2 at (0,0); 1×1 at (2,2): closest pair is (1,1)→(2,2) = max(1,1) = 1
        large_cells = get_occupied_cells(_pos(0, 0), SizeCategory.LARGE)
        small_cells = [_pos(2, 2)]
        self.assertEqual(min_chebyshev_distance(large_cells, small_cells), 1)

    def test_two_large_entities_adjacent(self):
        # 2×2 at (0,0)-(1,1) and 2×2 at (2,0)-(3,1)
        # closest: (1,0)→(2,0) = max(1,0) = 1
        a_cells = get_occupied_cells(_pos(0, 0), SizeCategory.LARGE)
        b_cells = get_occupied_cells(_pos(2, 0), SizeCategory.LARGE)
        self.assertEqual(min_chebyshev_distance(a_cells, b_cells), 1)

    def test_two_large_entities_two_apart(self):
        # 2×2 at (0,0)-(1,1) and 2×2 at (3,0)-(4,1)
        # closest: (1,0)→(3,0) = 2
        a_cells = get_occupied_cells(_pos(0, 0), SizeCategory.LARGE)
        b_cells = get_occupied_cells(_pos(3, 0), SizeCategory.LARGE)
        self.assertEqual(min_chebyshev_distance(a_cells, b_cells), 2)

    # ── symmetry ─────────────────────────────────────────────────────────────
    def test_distance_is_symmetric(self):
        a = get_occupied_cells(_pos(0, 0), SizeCategory.LARGE)
        b = [_pos(3, 0)]
        self.assertEqual(
            min_chebyshev_distance(a, b),
            min_chebyshev_distance(b, a),
        )

    # ── huge entity ───────────────────────────────────────────────────────────
    def test_1x1_adjacent_to_huge(self):
        # Huge 3×3 at (0,0)-(2,2); 1×1 at (3,0): (2,0)→(3,0) = 1
        huge_cells = get_occupied_cells(_pos(0, 0), SizeCategory.HUGE)
        small_cells = [_pos(3, 0)]
        self.assertEqual(min_chebyshev_distance(huge_cells, small_cells), 1)

    # ── error: empty list ─────────────────────────────────────────────────────
    def test_empty_cells_a_raises(self):
        with self.assertRaises(ValueError):
            min_chebyshev_distance([], [_pos(0, 0)])

    def test_empty_cells_b_raises(self):
        with self.assertRaises(ValueError):
            min_chebyshev_distance([_pos(0, 0)], [])

    def test_both_empty_raises(self):
        with self.assertRaises(ValueError):
            min_chebyshev_distance([], [])

    # ── return type ───────────────────────────────────────────────────────────
    def test_return_type_is_int(self):
        result = min_chebyshev_distance([_pos(0, 0)], [_pos(2, 1)])
        self.assertIsInstance(result, int)


# ─── reach integration: get_occupied_cells + min_chebyshev_distance ──────────

class TestOccupiedCellsAndDistanceIntegration(unittest.TestCase):
    """Verify that get_occupied_cells feeds correctly into min_chebyshev_distance."""

    def test_medium_vs_medium_adjacent(self):
        a = get_occupied_cells(_pos(0, 0), SizeCategory.MEDIUM)
        b = get_occupied_cells(_pos(1, 0), SizeCategory.MEDIUM)
        self.assertEqual(min_chebyshev_distance(a, b), 1)

    def test_medium_vs_medium_same_cell(self):
        a = get_occupied_cells(_pos(5, 5), SizeCategory.MEDIUM)
        b = get_occupied_cells(_pos(5, 5), SizeCategory.MEDIUM)
        self.assertEqual(min_chebyshev_distance(a, b), 0)

    def test_large_attacking_adjacent_medium_within_default_reach(self):
        from app.services.combat_service.reach import (
            is_within_melee_reach_multi,
            DEFAULT_MELEE_REACH_CELLS,
        )
        attacker = get_occupied_cells(_pos(0, 0), SizeCategory.LARGE)
        target = get_occupied_cells(_pos(2, 0), SizeCategory.MEDIUM)
        self.assertTrue(
            is_within_melee_reach_multi(attacker, target, DEFAULT_MELEE_REACH_CELLS)
        )

    def test_large_attacking_out_of_default_reach(self):
        from app.services.combat_service.reach import (
            is_within_melee_reach_multi,
            DEFAULT_MELEE_REACH_CELLS,
        )
        attacker = get_occupied_cells(_pos(0, 0), SizeCategory.LARGE)
        # Target 3 cells away from closest attacker cell (2 + 1 = 3 away from (1,0))
        target = get_occupied_cells(_pos(4, 0), SizeCategory.MEDIUM)
        self.assertFalse(
            is_within_melee_reach_multi(attacker, target, DEFAULT_MELEE_REACH_CELLS)
        )

    def test_two_medium_entities_three_cells_apart(self):
        from app.services.combat_service.reach import is_within_melee_reach_multi
        a = get_occupied_cells(_pos(0, 0), SizeCategory.MEDIUM)
        b = get_occupied_cells(_pos(3, 0), SizeCategory.MEDIUM)
        self.assertFalse(is_within_melee_reach_multi(a, b, 2))

    def test_huge_vs_medium_adjacent(self):
        from app.services.combat_service.reach import (
            is_within_melee_reach_multi,
            DEFAULT_MELEE_REACH_CELLS,
        )
        attacker = get_occupied_cells(_pos(0, 0), SizeCategory.HUGE)
        target = get_occupied_cells(_pos(3, 0), SizeCategory.MEDIUM)
        self.assertTrue(
            is_within_melee_reach_multi(attacker, target, DEFAULT_MELEE_REACH_CELLS)
        )


if __name__ == "__main__":
    unittest.main()
