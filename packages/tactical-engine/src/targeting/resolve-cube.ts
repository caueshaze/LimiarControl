import type { Coordinate, EdgeObstacle, Obstacle } from "@limiarmap/shared-contracts";
import { blocksEffect } from "../validation/obstacle-rules";
import { canEffectReachAoE } from "./aoe-filter";

/**
 * Resolves a cube-shaped AoE anchored at `anchor` (top-left corner of the
 * cube footprint) with the given `size` in cells.
 *
 * Phase 11: after computing the geometric footprint, filters each candidate
 * cell through `canEffectReachAoE` from the anchor point. Cells inside the
 * cube that are separated from the anchor by a blocking cell or edge obstacle
 * are excluded.
 *
 * Note: using the anchor corner as the propagation origin is an intentional
 * approximation for Phase 11. A future phase may accept the caster's position
 * for more precise shadow zones.
 */
export function resolveCube(
  anchor: Coordinate,
  size: number,
  obstacles: Obstacle[],
  edgeObstacles: EdgeObstacle[] = []
): Coordinate[] {
  const result: Coordinate[] = [];

  for (let x = anchor.x; x < anchor.x + size; x += 1) {
    for (let y = anchor.y; y < anchor.y + size; y += 1) {
      const coordinate = { x, y };
      if (
        !blocksEffect(obstacles, coordinate) &&
        canEffectReachAoE(anchor, coordinate, obstacles, edgeObstacles)
      ) {
        result.push(coordinate);
      }
    }
  }

  return result;
}
