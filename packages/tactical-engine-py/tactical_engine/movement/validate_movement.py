from dataclasses import dataclass
from typing import Optional
from shared_contracts import CombatState, Coordinate, Token
from ..grid.grid_state import GridState, find_occupying_token, is_blocked_cell, is_inside_map
from ..validation.obstacle_rules import clips_diagonal_movement
from .path_cost import compute_path_cost


@dataclass
class MovementValidationResult:
    accepted: bool
    path_cost_units: int
    rejection_reason: Optional[str] = None


def validate_movement(
    grid_state: GridState,
    token: Token,
    path: list[Coordinate],
    combat_state: Optional[CombatState] = None,
) -> MovementValidationResult:
    if not path:
        return MovementValidationResult(accepted=False, path_cost_units=0, rejection_reason="empty_path")

    if (
        combat_state is not None
        and combat_state.status == "active"
        and token.combatant_id != combat_state.active_combatant_id
    ):
        return MovementValidationResult(accepted=False, path_cost_units=0, rejection_reason="out_of_turn")

    full_path = [token.position, *path]
    for i in range(1, len(full_path)):
        current = full_path[i]
        previous = full_path[i - 1]
        x_delta = abs(current.x - previous.x)
        y_delta = abs(current.y - previous.y)

        if not is_inside_map(grid_state, current):
            return MovementValidationResult(accepted=False, path_cost_units=0, rejection_reason="outside_map")

        if x_delta > 1 or y_delta > 1 or (x_delta == 0 and y_delta == 0):
            return MovementValidationResult(accepted=False, path_cost_units=0, rejection_reason="non_contiguous_path")

        if is_blocked_cell(grid_state, current):
            return MovementValidationResult(accepted=False, path_cost_units=0, rejection_reason="blocked_path")

        if x_delta == 1 and y_delta == 1:
            corner_a = Coordinate(x=current.x, y=previous.y)
            corner_b = Coordinate(x=previous.x, y=current.y)
            if clips_diagonal_movement(grid_state.obstacles, corner_a) or clips_diagonal_movement(
                grid_state.obstacles, corner_b
            ):
                return MovementValidationResult(
                    accepted=False, path_cost_units=0, rejection_reason="diagonal_clipped"
                )

        occupant = find_occupying_token(grid_state, current)
        if occupant is not None and occupant.id != token.id:
            return MovementValidationResult(accepted=False, path_cost_units=0, rejection_reason="occupied_cell")

    path_cost_units = compute_path_cost(full_path)
    if path_cost_units > token.movement_budget:
        return MovementValidationResult(
            accepted=False, path_cost_units=path_cost_units, rejection_reason="movement_budget_exceeded"
        )

    return MovementValidationResult(accepted=True, path_cost_units=path_cost_units)
