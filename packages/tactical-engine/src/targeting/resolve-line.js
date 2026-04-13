import { blocksEffect } from "../validation/obstacle-rules";
import { findEdgeBetween } from "../grid/grid-state";
export function resolveLine(origin, anchor, range, obstacles, edgeObstacles = []) {
    const result = [];
    const deltaX = Math.sign(anchor.x - origin.x);
    const deltaY = Math.sign(anchor.y - origin.y);
    let prev = origin;
    for (let step = 1; step <= range; step += 1) {
        const coordinate = { x: origin.x + deltaX * step, y: origin.y + deltaY * step };
        if (blocksEffect(obstacles, coordinate))
            break;
        if (edgeObstacles.length > 0) {
            const crossedEdge = findEdgeBetween(edgeObstacles, prev, coordinate);
            if (crossedEdge?.blocksEffect)
                break;
        }
        result.push(coordinate);
        prev = coordinate;
    }
    return result;
}
