import { findOccupyingToken, getEdgeBetweenCells, isBlockedCell, isEdgeBlocked, isInsideMap } from "../grid/grid-state";
import { clipsDiagonalMovement, getMovementCostMultiplier } from "../validation/obstacle-rules";
import { computePathCost } from "./path-cost";
export function validateMovement(gridState, token, path, combatState) {
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
        if ((xDelta === 1 && yDelta === 0) || (xDelta === 0 && yDelta === 1)) {
            if (isEdgeBlocked(gridState, previous, current)) {
                return { accepted: false, pathCostUnits: 0, rejectionReason: "blocked_path" };
            }
        }
        else if (xDelta === 1 && yDelta === 1) {
            const cornerH = getEdgeBetweenCells(gridState, previous, { x: current.x, y: previous.y });
            const cornerV = getEdgeBetweenCells(gridState, { x: current.x, y: previous.y }, current);
            if (cornerH?.blocksMovement || cornerV?.blocksMovement) {
                return { accepted: false, pathCostUnits: 0, rejectionReason: "blocked_path" };
            }
        }
        if (isBlockedCell(gridState, current)) {
            return { accepted: false, pathCostUnits: 0, rejectionReason: "blocked_path" };
        }
        if (xDelta === 1 &&
            yDelta === 1 &&
            (clipsDiagonalMovement(gridState.obstacles, { x: current.x, y: previous.y }) ||
                clipsDiagonalMovement(gridState.obstacles, { x: previous.x, y: current.y }))) {
            return { accepted: false, pathCostUnits: 0, rejectionReason: "diagonal_clipped" };
        }
        const occupant = findOccupyingToken(gridState, current);
        if (occupant && occupant.id !== token.id) {
            return { accepted: false, pathCostUnits: 0, rejectionReason: "occupied_cell" };
        }
    }
    const pathCostUnits = computePathCost(fullPath, (cell) => getMovementCostMultiplier(gridState.obstacles, cell));
    if (pathCostUnits > token.movementBudget) {
        return { accepted: false, pathCostUnits, rejectionReason: "movement_budget_exceeded" };
    }
    return { accepted: true, pathCostUnits };
}
