import type { Coordinate, EdgeObstacle, Obstacle } from "@limiarmap/shared-contracts";
import { blocksEffect } from "../validation/obstacle-rules";
import { canEffectReachAoE } from "./aoe-filter";

/**
 * Resolves a cone-shaped AoE expanding from `origin` toward `anchor`.
 *
 * Phase 11: after computing the geometric footprint, filters each candidate
 * cell through `canEffectReachAoE` from the cone's origin. Cells that are
 * geometrically inside the cone but separated from the origin by a blocking
 * cell or edge obstacle are excluded (shadow zone).
 */
export function resolveCone(
  origin: Coordinate,
  anchor: Coordinate,
  size: number,
  obstacles: Obstacle[],
  edgeObstacles: EdgeObstacle[] = []
): Coordinate[] {
  const result: Coordinate[] = [];
  const deltaX = Math.sign(anchor.x - origin.x);
  const deltaY = Math.sign(anchor.y - origin.y);

  for (let step = 1; step <= size; step += 1) {
    for (let spread = -step + 1; spread <= step - 1; spread += 1) {
      const coordinate =
        Math.abs(deltaX) >= Math.abs(deltaY)
          ? { x: origin.x + deltaX * step, y: origin.y + spread }
          : { x: origin.x + spread, y: origin.y + deltaY * step };

      if (
        !blocksEffect(obstacles, coordinate) &&
        canEffectReachAoE(origin, coordinate, obstacles, edgeObstacles)
      ) {
        result.push(coordinate);
      }
    }
  }

  return result;
}
