import { blocksEffect } from "../validation/obstacle-rules";
import { findEdgeBetween } from "../grid/grid-state";
import { traceLine } from "./line-trace";

export function canEffectReachAoE(origin, target, obstacles, edgeObstacles = []) {
    const intermediate = traceLine(origin, target);
    for (const cell of intermediate) {
        if (blocksEffect(obstacles, cell))
            return false;
    }
    if (edgeObstacles.length === 0)
        return true;
    const fullPath = [origin, ...intermediate, target];
    for (let i = 1; i < fullPath.length - 1; i++) {
        const edge = findEdgeBetween(edgeObstacles, fullPath[i], fullPath[i + 1]);
        if (edge?.blocksEffect)
            return false;
    }
    return true;
}

export function filterByEffectReachability(origin, candidates, obstacles, edgeObstacles = []) {
    if (edgeObstacles.length === 0)
        return candidates;
    return candidates.filter((cell) => canEffectReachAoE(origin, cell, obstacles, edgeObstacles));
}
