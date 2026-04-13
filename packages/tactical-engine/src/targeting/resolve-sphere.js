import { chebyshevDistance } from "../grid/coordinates";
import { blocksEffect } from "../validation/obstacle-rules";
import { canEffectReachAoE } from "./aoe-filter";
export function resolveSphere(center, radius, obstacles, edgeObstacles = []) {
    const result = [];
    for (let x = center.x - radius; x <= center.x + radius; x += 1) {
        for (let y = center.y - radius; y <= center.y + radius; y += 1) {
            const coordinate = { x, y };
            if (chebyshevDistance(center, coordinate) <= radius &&
                !blocksEffect(obstacles, coordinate) &&
                canEffectReachAoE(center, coordinate, obstacles, edgeObstacles)) {
                result.push(coordinate);
            }
        }
    }
    return result;
}
