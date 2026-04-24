"""
Unit conversion helpers for the LimiarControl → LimiarMap boundary.

The Control domain operates in meters (character sheet values, spell catalogs,
weapon stats). The Map tactical engine operates in cells (grid units).

Default scale: METERS_PER_CELL = 1.5
  1 cell = 1.5 meters, compatible with standard D&D 5e grids where
  1 square = 5 ft ≈ 1.524 m (rounded to 1.5 m for clean arithmetic).

Rounding policy
---------------
- Movement budget: floor — preserves D&D grid expectation (whole cells only,
  never partial cell from rounding up).
- Range / AoE size: round — nearest cell is mechanically appropriate for
  spell and weapon range (avoids systematic under/over-reach).

Example conversions (metersPerCell = 1.5)
-----------------------------------------
AoE dimensions
  1.5 m  →  1 cell   (5 ft — Hail of Thorns radius)
  4.5 m  →  3 cells  (15 ft — Burning Hands cone, Thunderwave cube)
  6.0 m  →  4 cells  (20 ft — Fireball / Fog Cloud / Spike Growth radius)

Spell ranges
  36 m   → 24 cells  (120 ft — Fog Cloud)
  45 m   → 30 cells  (150 ft — Fireball / Spike Growth)

Other
   9 m   →  6 cells  (30 ft — standard character movement)
  18 m   → 12 cells  (60 ft — Magic Missile)
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Scale constant
# ---------------------------------------------------------------------------

METERS_PER_CELL: float = 1.5
"""Default map scale: 1.5 meters per cell."""


# ---------------------------------------------------------------------------
# Conversion helpers
# ---------------------------------------------------------------------------

def meters_to_cells(meters: float, meters_per_cell: float = METERS_PER_CELL) -> int:
    """Convert a meter distance to the nearest grid-cell count.

    Use for range and AoE dimensions (round to nearest cell).

    >>> meters_to_cells(1.5)
    1
    >>> meters_to_cells(4.5)
    3
    >>> meters_to_cells(6)
    4
    >>> meters_to_cells(36)
    24
    >>> meters_to_cells(45)
    30
    """
    return round(meters / meters_per_cell)


def meters_to_movement_cells(meters: float, meters_per_cell: float = METERS_PER_CELL) -> int:
    """Convert a movement speed in meters to a cell budget (floor).

    Use for token movement speed (e.g. speedMeters → movementSpeedCells).
    Floors to ensure only whole cells are granted — partial cells are
    discarded, preserving D&D grid expectations.

    >>> meters_to_movement_cells(9)
    6
    >>> meters_to_movement_cells(12)
    8
    """
    return int(meters // meters_per_cell)
