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

from dataclasses import dataclass
from typing import Literal

from .unit_conversion import METERS_PER_CELL

DEFAULT_MELEE_REACH_CELLS: int = 1
EXTENDED_REACH_CELLS: int = 2
TOUCH_RANGE_METERS: float = METERS_PER_CELL

WEAPON_RANGE_NOT_CONFIGURED = "weapon_range_not_configured"
SPELL_RANGE_NOT_CONFIGURED = "spell_range_not_configured"

WeaponRangeBand = Literal["normal", "long", "out_of_range"]


@dataclass(frozen=True)
class WeaponAttackRangeProfile:
    normal_range: float | None
    long_range: float | None
    max_range: float | None
    failure_reason: str | None = None


@dataclass(frozen=True)
class WeaponAttackRangeClassification:
    band: WeaponRangeBand
    is_in_range: bool
    is_in_normal_range: bool
    is_in_long_range: bool


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


def normalize_weapon_long_range(
    *,
    range_meters: int | float | None = None,
    range_long_meters: int | float | None = None,
) -> tuple[float | None, float | None]:
    """Normalize a weapon's normal/long range bounds.

    Long range is only considered valid when it is numeric and strictly
    greater than the normal range.
    """
    if not isinstance(range_meters, (int, float)):
        return (None, None)

    normal_range = float(range_meters)
    if normal_range <= 0:
        normal_range = TOUCH_RANGE_METERS

    long_range = None
    if isinstance(range_long_meters, (int, float)):
        maybe_long = float(range_long_meters)
        if maybe_long > normal_range:
            long_range = maybe_long

    return (normal_range, long_range)


def resolve_weapon_attack_range_profile(
    *,
    range_meters: int | float | None = None,
    range_long_meters: int | float | None = None,
    weapon_range_type: str | None = None,
    has_reach: bool = False,
) -> WeaponAttackRangeProfile:
    """Resolve the authoritative weapon range profile for a targeting intent."""
    normal_range, long_range = normalize_weapon_long_range(
        range_meters=range_meters,
        range_long_meters=range_long_meters,
    )
    if normal_range is not None:
        return WeaponAttackRangeProfile(
            normal_range=normal_range,
            long_range=long_range,
            max_range=long_range if long_range is not None else normal_range,
        )

    rng_type = (weapon_range_type or "").strip().lower()
    if rng_type == "melee":
        melee_reach = resolve_melee_reach_cells(has_reach=has_reach) * METERS_PER_CELL
        return WeaponAttackRangeProfile(
            normal_range=melee_reach,
            long_range=None,
            max_range=melee_reach,
        )

    if rng_type == "ranged":
        return WeaponAttackRangeProfile(
            normal_range=None,
            long_range=None,
            max_range=None,
            failure_reason=WEAPON_RANGE_NOT_CONFIGURED,
        )

    return WeaponAttackRangeProfile(
        normal_range=None,
        long_range=None,
        max_range=None,
    )


def classify_weapon_attack_distance(
    distance: int | float,
    *,
    normal_range: int | float | None,
    long_range: int | float | None = None,
) -> WeaponAttackRangeClassification:
    """Classify a resolved distance using the normal/long range profile."""
    normalized_normal, normalized_long = normalize_weapon_long_range(
        range_meters=normal_range,
        range_long_meters=long_range,
    )
    if normalized_normal is None:
        raise ValueError("normal_range must be numeric to classify weapon distance.")

    resolved_distance = float(distance)
    max_range = (
        normalized_long if normalized_long is not None else normalized_normal
    )
    if resolved_distance <= normalized_normal:
        return WeaponAttackRangeClassification(
            band="normal",
            is_in_range=True,
            is_in_normal_range=True,
            is_in_long_range=False,
        )
    if resolved_distance <= max_range:
        return WeaponAttackRangeClassification(
            band="long",
            is_in_range=True,
            is_in_normal_range=False,
            is_in_long_range=True,
        )
    return WeaponAttackRangeClassification(
        band="out_of_range",
        is_in_range=False,
        is_in_normal_range=False,
        is_in_long_range=False,
    )


def resolve_weapon_attack_kind(
    *,
    weapon_range_type: str | None = None,
    range_meters: int | float | None = None,
    range_long_meters: int | float | None = None,
    has_reach: bool = False,
    distance_meters: int | float | None = None,
) -> Literal["melee", "ranged"]:
    """Resolve the effective attack kind for a weapon strike.

    This keeps thrown/melee weapons coherent:
    - true ranged weapons are always ranged
    - melee weapons with a valid ranged profile become ranged only when the
      resolved attack distance exceeds melee reach
    - otherwise the attack remains melee
    """
    normalized_range_type = (weapon_range_type or "").strip().lower()
    if normalized_range_type == "ranged":
        return "ranged"

    if isinstance(distance_meters, (int, float)):
        profile = resolve_weapon_attack_range_profile(
            range_meters=range_meters,
            range_long_meters=range_long_meters,
            weapon_range_type=weapon_range_type,
            has_reach=has_reach,
        )
        melee_reach = resolve_melee_reach_cells(has_reach=has_reach) * METERS_PER_CELL
        if profile.normal_range is not None and float(distance_meters) > melee_reach:
            return "ranged"

    return "melee"


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


def derive_max_range_meters(
    *,
    range_meters: int | float | None = None,
    range_long_meters: int | float | None = None,
    weapon_range_type: str | None = None,
    has_reach: bool = False,
    target_type: str | None = None,
    range_kind: str | None = None,
) -> tuple[float | None, str | None]:
    """Derive the maximum allowed range in meters for a targeting intent.

    Returns a 2-tuple ``(max_range_meters, failure_reason)``.

    * ``max_range_meters`` is *None* when no range constraint applies
      (e.g. self-targeted spells, actions without spatial range).
    * ``failure_reason`` is a non-None canonical code when the intent
      carries *incomplete* range metadata that makes validation impossible.
    """
    normalized_range_kind = (range_kind or "").strip().lower()
    if normalized_range_kind == "self":
        return (None, None)

    if normalized_range_kind == "touch":
        return (TOUCH_RANGE_METERS, None)

    if normalized_range_kind == "distance":
        if isinstance(range_meters, (int, float)):
            if range_meters > 0:
                return (float(range_meters), None)
            return (TOUCH_RANGE_METERS, None)
        return (None, SPELL_RANGE_NOT_CONFIGURED)

    if target_type == "self":
        return (None, None)

    if target_type == "touch":
        return (TOUCH_RANGE_METERS, None)

    normalized_target_type = (target_type or "").strip().lower()
    if normalized_target_type == "ranged":
        if isinstance(range_meters, (int, float)):
            if range_meters > 0:
                return (float(range_meters), None)
            return (TOUCH_RANGE_METERS, None)
        return (None, SPELL_RANGE_NOT_CONFIGURED)

    profile = resolve_weapon_attack_range_profile(
        range_meters=range_meters,
        range_long_meters=range_long_meters,
        weapon_range_type=weapon_range_type,
        has_reach=has_reach,
    )
    if profile.failure_reason is not None:
        return (None, profile.failure_reason)
    if profile.max_range is not None:
        return (profile.max_range, None)
    return (None, None)
