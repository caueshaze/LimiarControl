from __future__ import annotations

from typing import Any, Iterable

from .exceptions import _roll_dice_expression
from .unit_conversion import METERS_PER_CELL


def _coordinate_key(cell: Any) -> tuple[int, int] | None:
    if cell is None:
        return None
    if isinstance(cell, dict):
        x, y = cell.get("x"), cell.get("y")
    else:
        x, y = getattr(cell, "x", None), getattr(cell, "y", None)
    if not isinstance(x, int) or not isinstance(y, int):
        return None
    return (x, y)


def _is_movement_hazard(effect: dict[str, Any]) -> bool:
    """A hazard whose footprint deals damage as a creature traverses it.

    The shape mirrors the metadata seeded for Spike Growth in
    ``persistent_area_effects._metadata_for_spell``: a difficult-terrain
    effect that also declares damage dice and a per-distance interval. Pure
    obscurement (Fog Cloud) and difficult-terrain entries without damage
    metadata are deliberately excluded.
    """

    if not isinstance(effect, dict):
        return False
    if effect.get("terrain_effect") != "difficult_terrain":
        return False
    dice = effect.get("movement_damage_dice")
    if not isinstance(dice, str) or not dice.strip():
        return False
    per_meters = effect.get("damage_per_meters")
    if not isinstance(per_meters, (int, float)) or per_meters <= 0:
        return False
    return True


def _cells_inside_effect(effect: dict[str, Any], path: Iterable[Any]) -> int:
    affected = effect.get("affected_cells")
    if not isinstance(affected, list):
        return 0
    inside = {key for cell in affected if (key := _coordinate_key(cell)) is not None}
    if not inside:
        return 0
    count = 0
    for step in path:
        key = _coordinate_key(step)
        if key is not None and key in inside:
            count += 1
    return count


def compute_movement_hazard_outcomes(
    active_area_effects: Iterable[dict[str, Any]] | None,
    path: Iterable[Any] | None,
    *,
    meters_per_cell: float = METERS_PER_CELL,
) -> list[dict[str, Any]]:
    """Compute per-effect damage outcomes for a confirmed movement path.

    One outcome per active area effect that the path actually entered. Each
    distinct overlapping effect rolls its own dice — the chosen safe-stacking
    rule (one application per distinct active effect, no double-apply for the
    same effect on the same path).

    The path argument is the list of cells the actor *enters* — i.e. the
    response path returned by the map server, which already excludes the
    source cell. Zero-length paths therefore yield no outcomes.
    """

    if not active_area_effects or not path:
        return []
    path_list = list(path)
    if not path_list:
        return []
    outcomes: list[dict[str, Any]] = []
    for effect in active_area_effects:
        if not _is_movement_hazard(effect):
            continue
        cells_inside = _cells_inside_effect(effect, path_list)
        if cells_inside <= 0:
            continue
        per_meters = float(effect["damage_per_meters"])
        meters_inside = cells_inside * meters_per_cell
        damage_instances = int(meters_inside // per_meters)
        if damage_instances <= 0:
            continue
        dice_expression = str(effect["movement_damage_dice"])
        damage_total = sum(
            _roll_dice_expression(dice_expression) for _ in range(damage_instances)
        )
        if damage_total <= 0:
            continue
        outcomes.append(
            {
                "effect_id": effect.get("id"),
                "source_spell_canonical_key": effect.get("source_spell_canonical_key"),
                "source_spell_name": effect.get("source_spell_name") or "Spell area",
                "damage_type": effect.get("damage_type"),
                "cells_inside": cells_inside,
                "meters_inside": meters_inside,
                "damage_instances": damage_instances,
                "dice_expression": dice_expression,
                "damage": damage_total,
            }
        )
    return outcomes
