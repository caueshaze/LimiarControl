import { blocksEffect } from "../validation/obstacle-rules";
import { canEffectReachAoE } from "./aoe-filter";
export function resolveCube(anchor, size, obstacles, edgeObstacles = []) {
    const result = [];
    for (let x = anchor.x; x < anchor.x + size; x += 1) {
        for (let y = anchor.y; y < anchor.y + size; y += 1) {
            const coordinate = { x, y };
            if (!blocksEffect(obstacles, coordinate) &&
                canEffectReachAoE(anchor, coordinate, obstacles, edgeObstacles)) {
                result.push(coordinate);
            }
        }
    }
    return result;
}
