import { blocksEffect } from "../validation/obstacle-rules";
import { canEffectReachAoE } from "./aoe-filter";
export function resolveCone(origin, anchor, size, obstacles, edgeObstacles = []) {
    const result = [];
    const deltaX = Math.sign(anchor.x - origin.x);
    const deltaY = Math.sign(anchor.y - origin.y);
    for (let step = 1; step <= size; step += 1) {
        for (let spread = -step + 1; spread <= step - 1; spread += 1) {
        const coordinate = Math.abs(deltaX) >= Math.abs(deltaY)
            ? { x: origin.x + deltaX * step, y: origin.y + spread }
            : { x: origin.x + spread, y: origin.y + deltaY * step };
        if (!blocksEffect(obstacles, coordinate) &&
            canEffectReachAoE(origin, coordinate, obstacles, edgeObstacles)) {
            result.push(coordinate);
        }
    }
    }
    return result;
}
