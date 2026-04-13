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
  9 m  → 6 cells   (standard 30 ft character movement)
 18 m  → 12 cells  (Magic Missile / 60 ft range)
 45 m  → 30 cells  (Fireball / 150 ft range)
  6 m  →  4 cells  (Fireball 20 ft radius)
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

    >>> meters_to_cells(18)
    12
    >>> meters_to_cells(45)
    30
    >>> meters_to_cells(6)
    4
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
