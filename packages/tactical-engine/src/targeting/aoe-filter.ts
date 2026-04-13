import type { Coordinate, EdgeObstacle, Obstacle } from "@limiarmap/shared-contracts";
import { blocksEffect } from "../validation/obstacle-rules";
import { findEdgeBetween } from "../grid/grid-state";
import { traceLine } from "./line-trace";

/**
 * Phase 11: AoE effect-reachability check.
 *
 * Determines whether an area effect can propagate from `origin` to `target`.
 * Stricter than the single-target `hasLineOfEffect` in one key way:
 *
 *   - Single-target LoE excludes the edge adjacent to the target (by policy:
 *     an obstacle AT the target contributes cover, not line-of-effect denial).
 *   - AoE propagation INCLUDES the target-adjacent edge, because a wall on the
 *     near face of a cell should prevent the effect from entering that cell.
 *
 * Edges adjacent to the ORIGIN remain excluded (same as single-target LoE):
 * an effect always radiates from the caster's cell regardless of its boundaries.
 *
 * Returns false if any intermediate cell blocks effect, or if any edge
 * between intermediate cells (or between the last intermediate cell and the
 * target) has `blocksEffect === true`.
 */
export function canEffectReachAoE(
  origin: Coordinate,
  target: Coordinate,
  obstacles: Obstacle[],
  edgeObstacles: EdgeObstacle[] = []
): boolean {
  const intermediate = traceLine(origin, target);

  // Check intermediate cells for effect blocking
  for (const cell of intermediate) {
    if (blocksEffect(obstacles, cell)) return false;
  }

  if (edgeObstacles.length === 0) return true;

  // Check edges from the first intermediate cell onward (origin-adjacent edge excluded),
  // including the edge between the last intermediate cell and the target.
  // fullPath = [origin, ...intermediate, target]
  // We check edges at indices i→i+1 for i = 1..fullPath.length-2
  const fullPath: Coordinate[] = [origin, ...intermediate, target];
  for (let i = 1; i < fullPath.length - 1; i++) {
    const edge = findEdgeBetween(edgeObstacles, fullPath[i], fullPath[i + 1]);
    if (edge?.blocksEffect) return false;
  }

  return true;
}

/**
 * Phase 11: Batch AoE filter.
 *
 * Filters a list of candidate cells to those reachable by `canEffectReachAoE`.
 * Use this after computing a shape's geometric footprint.
 *
 * @param origin     - The radiating point (caster position or shape center).
 * @param candidates - Cells in the geometric footprint (already excluding
 *                     cells that themselves block effect).
 */
export function filterByEffectReachability(
  origin: Coordinate,
  candidates: Coordinate[],
  obstacles: Obstacle[],
  edgeObstacles: EdgeObstacle[] = []
): Coordinate[] {
  if (edgeObstacles.length === 0) return candidates;
  return candidates.filter((cell) =>
    canEffectReachAoE(origin, cell, obstacles, edgeObstacles)
  );
}
