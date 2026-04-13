"""Phase F5 — Entity size and multi-cell occupancy.

Defines the size model for combat entities and provides helpers to
compute an entity's grid footprint from an anchor cell.

Design rules
------------
* All entities occupy a square footprint aligned to the grid.
* The anchor cell is the **top-left** corner of the footprint.
* There is no rotation; footprints are always axis-aligned.
* Tiny / Small / Medium all occupy 1×1.
* Large = 2×2, Huge = 3×3, Gargantuan capped at 4×4.

Position authority
------------------
Control does **not** store entity positions — that is the exclusive
domain of LimiarMap.  This module provides:

  1. Pure geometry helpers (``get_occupied_cells``) used when
     Control does hold a position (e.g., area-origin cell during AoE
     validation) or in unit tests.

  2. ``min_chebyshev_distance`` — minimum Chebyshev distance between
     two cell lists, used by the reach system to compute the effective
     distance between a multi-cell attacker and a multi-cell target.

  3. ``normalize_size_category`` — safely converts a raw string value
     (as stored in ``CampaignEntity.size`` or ``WildFormStats.size``)
     to a ``SizeCategory``, defaulting to MEDIUM when unrecognised.
"""
from __future__ import annotations

from enum import Enum


class SizeCategory(str, Enum):
    """D&D 5e creature size categories.

    Each category maps to a square footprint in grid cells:
      tiny / small / medium → 1×1
      large                 → 2×2
      huge                  → 3×3
      gargantuan            → 4×4  (capped; very large creatures can be bigger)
    """
    TINY = "tiny"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    HUGE = "huge"
    GARGANTUAN = "gargantuan"


# Footprint side length (in grid cells) for each size category.
_FOOTPRINT: dict[SizeCategory, int] = {
    SizeCategory.TINY: 1,
    SizeCategory.SMALL: 1,
    SizeCategory.MEDIUM: 1,
    SizeCategory.LARGE: 2,
    SizeCategory.HUGE: 3,
    SizeCategory.GARGANTUAN: 4,
}

_DEFAULT_SIZE = SizeCategory.MEDIUM


def size_footprint_cells(size_category: SizeCategory) -> int:
    """Return the side length (in cells) of the entity's square footprint.

    >>> size_footprint_cells(SizeCategory.MEDIUM)
    1
    >>> size_footprint_cells(SizeCategory.LARGE)
    2
    """
    return _FOOTPRINT[size_category]


def get_occupied_cells(
    anchor_cell: dict[str, int],
    size_category: SizeCategory,
) -> list[dict[str, int]]:
    """Return all grid cells occupied by an entity.

    The anchor cell is the **top-left** corner of the footprint.
    For a 1×1 entity the returned list contains only the anchor.

    Args:
        anchor_cell:    The top-left cell of the entity's footprint,
                        as ``{"x": int, "y": int}``.
        size_category:  The entity's size category.

    Returns:
        All cells that the entity occupies, ordered row-by-row
        (x varies fastest, then y).  The list has exactly
        ``side × side`` entries.

    Example (Large, anchor at (2, 3)):
        [(2,3), (3,3), (2,4), (3,4)]
    """
    side = size_footprint_cells(size_category)
    ax, ay = anchor_cell["x"], anchor_cell["y"]
    return [
        {"x": ax + dx, "y": ay + dy}
        for dy in range(side)
        for dx in range(side)
    ]


def normalize_size_category(
    raw: str | None,
    *,
    default: SizeCategory = _DEFAULT_SIZE,
) -> SizeCategory:
    """Convert a raw string to a ``SizeCategory``, defaulting safely.

    Accepts the canonical lowercase values stored in
    ``CampaignEntity.size`` and ``WildFormStats.size``.  Comparisons
    are case-insensitive.

    Args:
        raw:     The string to convert (may be ``None``).
        default: Fallback when the string is missing or unrecognised.
                 Defaults to :attr:`SizeCategory.MEDIUM`.

    Returns:
        A valid ``SizeCategory`` — never raises.
    """
    if not isinstance(raw, str):
        return default
    normalized = raw.strip().lower()
    for member in SizeCategory:
        if member.value == normalized:
            return member
    return default


def min_chebyshev_distance(
    cells_a: list[dict[str, int]],
    cells_b: list[dict[str, int]],
) -> int:
    """Return the minimum Chebyshev distance between two cell sets.

    Chebyshev distance between two cells is ``max(|dx|, |dy|)``, which
    corresponds to the number of king-moves on a chess board.

    This is used to determine the effective distance between a
    multi-cell attacker and a multi-cell target — the pair of cells
    (one from each entity) that are closest to each other determines
    whether the attacker can reach the target.

    Args:
        cells_a: Cell list for the first entity (attacker or target).
        cells_b: Cell list for the second entity.

    Returns:
        The minimum Chebyshev distance between any cell in *cells_a*
        and any cell in *cells_b*.

    Raises:
        ValueError: When either list is empty.
    """
    if not cells_a or not cells_b:
        raise ValueError("Both cell lists must be non-empty.")
    return min(
        max(abs(a["x"] - b["x"]), abs(a["y"] - b["y"]))
        for a in cells_a
        for b in cells_b
    )
