import { findOccupyingToken, getEdgeBetweenCells, isBlockedCell, isEdgeBlocked, isInsideMap } from "../grid/grid-state";
import { clipsDiagonalMovement, getMovementCostMultiplier } from "../validation/obstacle-rules";
import { computePathCost, isDiagonalStep, stepCost } from "./path-cost";
export function findReachableCells(gridState, token, combatState) {
    if (token.movementBudget <= 0) {
        return [];
    }
    if (combatState?.status === "active" && token.combatantId !== combatState.activeCombatantId) {
        return [];
    }
    const queue = [
        {
            coordinate: token.position,
            diagonalParity: 0,
            pathCostUnits: 0
        }
    ];
    const bestByState = new Map([[`${token.position.x}:${token.position.y}:0`, 0]]);
    const visited = new Set();
    const reachableByCoordinate = new Map();
    while (queue.length > 0) {
        let nextIndex = 0;
        for (let index = 1; index < queue.length; index += 1) {
            if (queue[index].pathCostUnits < queue[nextIndex].pathCostUnits) {
                nextIndex = index;
            }
        }
        const current = queue.splice(nextIndex, 1)[0];
        const currentKey = `${current.coordinate.x}:${current.coordinate.y}:${current.diagonalParity}`;
        if (visited.has(currentKey)) {
            continue;
        }
        visited.add(currentKey);
        const isOrigin = current.coordinate.x === token.position.x && current.coordinate.y === token.position.y;
        if (!isOrigin) {
            reachableByCoordinate.set(`${current.coordinate.x}:${current.coordinate.y}`, current.coordinate);
        }
        for (let yDelta = -1; yDelta <= 1; yDelta += 1) {
            for (let xDelta = -1; xDelta <= 1; xDelta += 1) {
                if (xDelta === 0 && yDelta === 0) {
                    continue;
                }
                const candidate = {
                    x: current.coordinate.x + xDelta,
                    y: current.coordinate.y + yDelta
                };
                const rejectionReason = getStepRejectionReason(gridState, token, current.coordinate, candidate);
                if (rejectionReason) {
                    continue;
                }
                const nextParity = isDiagonalStep(current.coordinate, candidate)
                    ? (1 - current.diagonalParity)
                    : current.diagonalParity;
                const nextCost = current.pathCostUnits +
                    stepCost(current.coordinate, candidate, current.diagonalParity, getMovementCostMultiplier(gridState.obstacles, candidate));
                if (nextCost > token.movementBudget) {
                    continue;
                }
                const nextKey = `${candidate.x}:${candidate.y}:${nextParity}`;
                const previousBest = bestByState.get(nextKey);
                if (previousBest !== undefined && previousBest <= nextCost) {
                    continue;
                }
                bestByState.set(nextKey, nextCost);
                queue.push({
                    coordinate: candidate,
                    diagonalParity: nextParity,
                    pathCostUnits: nextCost
                });
            }
        }
    }
    return Array.from(reachableByCoordinate.values()).sort((left, right) => left.x === right.x ? left.y - right.y : left.x - right.x);
}
function getStepRejectionReason(gridState, token, previous, current) {
    const xDelta = Math.abs(current.x - previous.x);
    const yDelta = Math.abs(current.y - previous.y);
    if (!isInsideMap(gridState, current)) {
        return "outside_map";
    }
    if (xDelta > 1 || yDelta > 1 || (xDelta === 0 && yDelta === 0)) {
        return "non_contiguous_path";
    }
    if ((xDelta === 1 && yDelta === 0) || (xDelta === 0 && yDelta === 1)) {
        if (isEdgeBlocked(gridState, previous, current)) {
            return "blocked_path";
        }
    }
    else if (xDelta === 1 && yDelta === 1) {
        const cornerH = getEdgeBetweenCells(gridState, previous, { x: current.x, y: previous.y });
        const cornerV = getEdgeBetweenCells(gridState, { x: current.x, y: previous.y }, current);
        if (cornerH?.blocksMovement || cornerV?.blocksMovement) {
            return "blocked_path";
        }
    }
    if (isBlockedCell(gridState, current)) {
        return "blocked_path";
    }
    if (xDelta === 1 &&
        yDelta === 1 &&
        (clipsDiagonalMovement(gridState.obstacles, { x: current.x, y: previous.y }) ||
            clipsDiagonalMovement(gridState.obstacles, { x: previous.x, y: current.y }))) {
        return "diagonal_clipped";
    }
    const occupant = findOccupyingToken(gridState, current);
    if (occupant && occupant.id !== token.id) {
        return "occupied_cell";
    }
    return undefined;
}
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
        const rejectionReason = getStepRejectionReason(gridState, token, previous, current);
        if (rejectionReason) {
            return { accepted: false, pathCostUnits: 0, rejectionReason };
        }
    }
    const pathCostUnits = computePathCost(fullPath, (cell) => getMovementCostMultiplier(gridState.obstacles, cell));
    if (pathCostUnits > token.movementBudget) {
        return { accepted: false, pathCostUnits, rejectionReason: "movement_budget_exceeded" };
    }
    return { accepted: true, pathCostUnits };
}
export function findMovementPath(gridState, token, destination, combatState) {
    if (combatState?.status === "active" && token.combatantId !== combatState.activeCombatantId) {
        return { accepted: false, path: [], pathCostUnits: 0, rejectionReason: "out_of_turn" };
    }
    if (destination.x === token.position.x && destination.y === token.position.y) {
        return { accepted: false, path: [], pathCostUnits: 0, rejectionReason: "empty_path" };
    }
    if (!isInsideMap(gridState, destination)) {
        return { accepted: false, path: [], pathCostUnits: 0, rejectionReason: "outside_map" };
    }
    if (isBlockedCell(gridState, destination)) {
        return { accepted: false, path: [], pathCostUnits: 0, rejectionReason: "blocked_path" };
    }
    const destinationOccupant = findOccupyingToken(gridState, destination);
    if (destinationOccupant && destinationOccupant.id !== token.id) {
        return { accepted: false, path: [], pathCostUnits: 0, rejectionReason: "occupied_cell" };
    }
    const queue = [{ coordinate: token.position, diagonalParity: 0, pathCostUnits: 0 }];
    const bestByState = new Map([[`${token.position.x}:${token.position.y}:0`, 0]]);
    const previousByState = new Map();
    const visited = new Set();
    while (queue.length > 0) {
        let nextIndex = 0;
        for (let index = 1; index < queue.length; index += 1) {
            if (queue[index].pathCostUnits < queue[nextIndex].pathCostUnits) {
                nextIndex = index;
            }
        }
        const current = queue.splice(nextIndex, 1)[0];
        const currentKey = `${current.coordinate.x}:${current.coordinate.y}:${current.diagonalParity}`;
        if (visited.has(currentKey)) {
            continue;
        }
        visited.add(currentKey);
        if (current.coordinate.x === destination.x && current.coordinate.y === destination.y) {
            const fullPath = [current.coordinate];
            let cursorKey = currentKey;
            while (previousByState.has(cursorKey)) {
                const previousState = previousByState.get(cursorKey);
                fullPath.push(previousState.coordinate);
                cursorKey = previousState.previousKey;
            }
            fullPath.reverse();
            const previewPath = fullPath.slice(1);
            const validation = validateMovement(gridState, token, previewPath, combatState);
            return {
                accepted: validation.accepted,
                path: previewPath,
                pathCostUnits: validation.pathCostUnits,
                rejectionReason: validation.rejectionReason
            };
        }
        for (let yDelta = -1; yDelta <= 1; yDelta += 1) {
            for (let xDelta = -1; xDelta <= 1; xDelta += 1) {
                if (xDelta === 0 && yDelta === 0) {
                    continue;
                }
                const candidate = {
                    x: current.coordinate.x + xDelta,
                    y: current.coordinate.y + yDelta
                };
                const rejectionReason = getStepRejectionReason(gridState, token, current.coordinate, candidate);
                if (rejectionReason) {
                    continue;
                }
                const nextParity = isDiagonalStep(current.coordinate, candidate)
                    ? (1 - current.diagonalParity)
                    : current.diagonalParity;
                const cost = stepCost(current.coordinate, candidate, current.diagonalParity, getMovementCostMultiplier(gridState.obstacles, candidate));
                const nextCost = current.pathCostUnits + cost;
                const nextKey = `${candidate.x}:${candidate.y}:${nextParity}`;
                const previousBest = bestByState.get(nextKey);
                if (previousBest !== undefined && previousBest <= nextCost) {
                    continue;
                }
                bestByState.set(nextKey, nextCost);
                previousByState.set(nextKey, {
                    previousKey: currentKey,
                    coordinate: current.coordinate
                });
                queue.push({
                    coordinate: candidate,
                    diagonalParity: nextParity,
                    pathCostUnits: nextCost
                });
            }
        }
    }
    return {
        accepted: false,
        path: [],
        pathCostUnits: 0,
        rejectionReason: "blocked_path"
    };
}
