import type { CombatState, Coordinate, Token } from "@limiarmap/shared-contracts";
import { findOccupyingToken, getEdgeBetweenCells, isBlockedCell, isEdgeBlocked, isInsideMap, type GridState } from "../grid/grid-state";
import { clipsDiagonalMovement, getMovementCostMultiplier } from "../validation/obstacle-rules";
import { computePathCost } from "./path-cost";

export interface MovementValidationResult {
  accepted: boolean;
  pathCostUnits: number;
  rejectionReason?: string;
}

export function validateMovement(
  gridState: GridState,
  token: Token,
  path: Coordinate[],
  combatState?: CombatState
): MovementValidationResult {
  if (path.length === 0) {
    return { accepted: false, pathCostUnits: 0, rejectionReason: "empty_path" };
  }

  if (combatState?.status === "active" && token.combatantId !== combatState.activeCombatantId) {
    return { accepted: false, pathCostUnits: 0, rejectionReason: "out_of_turn" };
  }

  const fullPath = [token.position, ...path];
  for (let index = 1; index < fullPath.length; index += 1) {
    const current = fullPath[index];
    const previous = fullPath[index - 1];
    const xDelta = Math.abs(current.x - previous.x);
    const yDelta = Math.abs(current.y - previous.y);

    if (!isInsideMap(gridState, current)) {
      return { accepted: false, pathCostUnits: 0, rejectionReason: "outside_map" };
    }

    if (xDelta > 1 || yDelta > 1 || (xDelta === 0 && yDelta === 0)) {
      return { accepted: false, pathCostUnits: 0, rejectionReason: "non_contiguous_path" };
    }

    // Phase 10: Edge blocking takes priority over cell semantics
    if ((xDelta === 1 && yDelta === 0) || (xDelta === 0 && yDelta === 1)) {
      // Orthogonal: check the single edge between the two cells
      if (isEdgeBlocked(gridState, previous, current)) {
        return { accepted: false, pathCostUnits: 0, rejectionReason: "blocked_path" };
      }
    } else if (xDelta === 1 && yDelta === 1) {
      // Diagonal: check both orthogonal "corner" edges.
      // Mirrors the existing clipsDiagonalMovement cell check.
      const cornerH = getEdgeBetweenCells(gridState, previous, { x: current.x, y: previous.y });
      const cornerV = getEdgeBetweenCells(gridState, { x: current.x, y: previous.y }, current);
      if (cornerH?.blocksMovement || cornerV?.blocksMovement) {
        return { accepted: false, pathCostUnits: 0, rejectionReason: "blocked_path" };
      }
    }

    if (isBlockedCell(gridState, current)) {
      return { accepted: false, pathCostUnits: 0, rejectionReason: "blocked_path" };
    }

    if (
      xDelta === 1 &&
      yDelta === 1 &&
      (clipsDiagonalMovement(gridState.obstacles, { x: current.x, y: previous.y }) ||
        clipsDiagonalMovement(gridState.obstacles, { x: previous.x, y: current.y }))
    ) {
      return { accepted: false, pathCostUnits: 0, rejectionReason: "diagonal_clipped" };
    }

    const occupant = findOccupyingToken(gridState, current);
    if (occupant && occupant.id !== token.id) {
      return { accepted: false, pathCostUnits: 0, rejectionReason: "occupied_cell" };
    }
  }

  // Phase 7: terrain multipliers are applied per destination cell.
  // Blocked cells were already rejected above; this only affects traversable
  // cells whose movementCostMultiplier > 1 (e.g. difficult terrain = 2).
  const pathCostUnits = computePathCost(
    fullPath,
    (cell) => getMovementCostMultiplier(gridState.obstacles, cell)
  );
  if (pathCostUnits > token.movementBudget) {
    return { accepted: false, pathCostUnits, rejectionReason: "movement_budget_exceeded" };
  }

  return { accepted: true, pathCostUnits };
}
