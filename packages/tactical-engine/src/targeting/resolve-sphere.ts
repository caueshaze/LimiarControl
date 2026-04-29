import type { Coordinate, EdgeObstacle, Obstacle } from "@limiarmap/shared-contracts";
import { blocksEffect } from "../validation/obstacle-rules";
import { canEffectReachAoE } from "./aoe-filter";

/**
 * Resolves a sphere-shaped AoE centered on `center` with the given `radius`.
 *
 * Uses Euclidean distance (dx² + dy² ≤ radius²) for a circular footprint.
 *
 * Phase 11: after computing the geometric footprint, filters each candidate
 * cell through `canEffectReachAoE` from the sphere's center. Cells inside the
 * radius that are separated from the center by a blocking cell or edge
 * obstacle are excluded (shadow zone behind walls).
 */
export function resolveSphere(
  center: Coordinate,
  radius: number,
  obstacles: Obstacle[],
  edgeObstacles: EdgeObstacle[] = []
): Coordinate[] {
  const result: Coordinate[] = [];

  for (let x = center.x - radius; x <= center.x + radius; x += 1) {
    for (let y = center.y - radius; y <= center.y + radius; y += 1) {
      const dx = x - center.x;
      const dy = y - center.y;
      const coordinate = { x, y };
      if (
        dx * dx + dy * dy <= radius * radius &&
        !blocksEffect(obstacles, coordinate) &&
        canEffectReachAoE(center, coordinate, obstacles, edgeObstacles)
      ) {
        result.push(coordinate);
      }
    }
  }

  return result;
}
