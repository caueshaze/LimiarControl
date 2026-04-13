"""reach.py — Phase F4/F5 centralized reach resolution.

Reach is measured in grid cells using Chebyshev distance.

Default melee reach:  1 cell (adjacent)
Extended reach:      2 cells (e.g., reach weapons, polearms)

All melee range derivation must flow through this module so that weapon
metadata, creature size, and conditions are resolved in one place.

Phase F5 — multi-cell reach
----------------------------
``is_within_melee_reach_multi`` extends single-cell reach checks to
entities that occupy multiple grid cells (Large/Huge/Gargantuan).  It
uses the minimum Chebyshev distance between any pair of cells — one
from the attacker's footprint, one from the target's footprint.

For 1×1 entities the two functions are equivalent.
"""

from __future__ import annotations

DEFAULT_MELEE_REACH_CELLS: int = 1
EXTENDED_REACH_CELLS: int = 2


def get_effective_reach(base_reach_cells: int) -> int:
    """Return effective reach in grid cells.

    Currently a passthrough — creature-size and condition modifiers will be
    resolved here once the combat model carries that data.

    Args:
        base_reach_cells: The weapon/form's native reach in cells.

    Returns:
        Effective reach, clamped to a minimum of 1 cell.
    """
    return max(1, base_reach_cells)


def resolve_melee_reach_cells(*, has_reach: bool = False) -> int:
    """Resolve melee reach in grid cells for a weapon or natural attack.

    Args:
        has_reach: True when the weapon carries the *reach* property.

    Returns:
        Effective reach in cells.
    """
    base = EXTENDED_REACH_CELLS if has_reach else DEFAULT_MELEE_REACH_CELLS
    return get_effective_reach(base)


def is_within_melee_reach(
    attacker_position: dict[str, int],
    target_position: dict[str, int],
    reach_cells: int,
) -> bool:
    """Return True if the target is within melee reach of the attacker.

    Distance is measured with **Chebyshev distance** — ``max(|dx|, |dy|)`` —
    which matches the 5e grid convention where diagonal movement costs the
    same as cardinal movement (1 square per step).

    This function is the single source of truth for local reach-distance
    checks.  When the LimiarMap integration is active, the same value is
    passed to the map as ``range_cells``; the map performs its own distance
    check using the same metric.

    Args:
        attacker_position: Grid cell coordinates as ``{"x": int, "y": int}``.
        target_position:   Grid cell coordinates as ``{"x": int, "y": int}``.
        reach_cells:       Effective reach in cells (from
                           :func:`resolve_melee_reach_cells`).

    Returns:
        ``True`` when ``chebyshev_distance(attacker, target) <= reach_cells``.
    """
    dx = abs(attacker_position["x"] - target_position["x"])
    dy = abs(attacker_position["y"] - target_position["y"])
    return max(dx, dy) <= reach_cells


def is_within_melee_reach_multi(
    attacker_cells: list[dict[str, int]],
    target_cells: list[dict[str, int]],
    reach_cells: int,
) -> bool:
    """Return True if any attacker cell is within melee reach of any target cell.

    Extends :func:`is_within_melee_reach` to entities that occupy
    multiple grid cells (Large, Huge, Gargantuan).  The effective
    distance is the **minimum** Chebyshev distance across all
    (attacker_cell, target_cell) pairs.

    For 1×1 entities (both lists have exactly one entry) this is
    identical to calling :func:`is_within_melee_reach` directly.

    Args:
        attacker_cells: All grid cells occupied by the attacker (from
                        :func:`~entity_size.get_occupied_cells`).
        target_cells:   All grid cells occupied by the target.
        reach_cells:    Effective reach in cells (from
                        :func:`resolve_melee_reach_cells`).

    Returns:
        ``True`` when the minimum Chebyshev distance between any
        attacker cell and any target cell is ``<= reach_cells``.

    Raises:
        ValueError: When either cell list is empty.
    """
    from .entity_size import min_chebyshev_distance  # local import avoids circular dep

    return min_chebyshev_distance(attacker_cells, target_cells) <= reach_cells
