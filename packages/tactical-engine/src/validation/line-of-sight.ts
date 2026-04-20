import type { Coordinate, EdgeObstacle, Obstacle, ObstacleCover } from "@limiarmap/shared-contracts";
import { blocksEffect, blocksVision, getHighestCover, COVER_RANK } from "./obstacle-rules";
import { traceLine } from "../targeting/line-trace";
import { findEdgeBetween } from "../grid/grid-state";

/**
 * Returns true if there is an unobstructed line of sight from `from` to `to`.
 *
 * Phase 10: Now checks both cell obstacles and edge obstacles.
 * Traces a line between the two cells and checks every intermediate cell for
 * obstacles with `blocksVision === true` and every edge crossing for
 * edge obstacles with `blocksVision === true`. The origin and target cells are
 * excluded: you can always see from where you stand, and an obstacle AT the
 * target is a cover concern, not a sight-line concern.
 */
export function hasLineOfSight(
  obstacles: Obstacle[],
  from: Coordinate,
  to: Coordinate,
  edgeObstacles: EdgeObstacle[] = []
): boolean {
  const intermediate = traceLine(from, to);
  const fullPath = [from, ...intermediate, to];

  // Check cell obstacles for vision blocking
  for (const cell of intermediate) {
    if (blocksVision(obstacles, cell)) {
      return false;
    }
  }

  // Phase 10: Check edge obstacles for vision blocking
  // We need to check edges that the line crosses between consecutive cells
  for (let i = 0; i < fullPath.length - 1; i++) {
    const edge = findEdgeBetween(edgeObstacles, fullPath[i], fullPath[i + 1]);
    if (edge?.blocksVision) {
      return false;
    }
  }

  return true;
}

/**
 * Returns true if there is an unobstructed line of effect from `from` to `to`.
 *
 * Phase 10: Now checks both cell obstacles and edge obstacles.
 * Same geometry as LoS but checks `blocksEffect` — an obstacle that prevents
 * effects from propagating through the cell.
 *
 * Intermediate cells only; origin and target excluded.
 */
export function hasLineOfEffect(
  obstacles: Obstacle[],
  from: Coordinate,
  to: Coordinate,
  edgeObstacles: EdgeObstacle[] = []
): boolean {
  const intermediate = traceLine(from, to);
  const fullPath = [from, ...intermediate, to];

  // Check cell obstacles for effect blocking
  for (const cell of intermediate) {
    if (blocksEffect(obstacles, cell)) {
      return false;
    }
  }

  // Phase 10: Check edge obstacles for effect blocking
  for (let i = 0; i < fullPath.length - 1; i++) {
    const edge = findEdgeBetween(edgeObstacles, fullPath[i], fullPath[i + 1]);
    if (edge?.blocksEffect) {
      return false;
    }
  }

  return true;
}

/**
 * Evaluate the cover level between two positions on the grid.
 *
 * Phase 10: Now includes edge obstacle cover.
 * Cover is conceptually distinct from LoS/LoE:
 *   - LoS/LoE are hard pass/fail blockers (binary)
 *   - Cover is a graduated obstruction level (none → half → three-quarters → full)
 *
 * This function should be called **after** LoS/LoE pass. It does not duplicate
 * those checks; it only inspects the `cover` property of obstacles.
 *
 * Geometry policy:
 *   - Uses the canonical `traceLine` utility (same as LoS/LoE)
 *   - **Origin cell excluded**: you don't get cover from your own cell
 *   - **Target cell included**: an obstacle on the target's cell contributes
 *     cover (the target is sheltering behind / inside the obstacle)
 *   - All intermediate cells are evaluated
 *   - **Edge obstacles**: edges between consecutive cells contribute their cover value
 *
 * Aggregation rule: strongest encountered cover wins
 *   full > threeQuarters > half > none
 *
 * @returns The highest cover level found along the trace path
 */
export function evaluateCover(
  obstacles: Obstacle[],
  from: Coordinate,
  to: Coordinate,
  edgeObstacles: EdgeObstacle[] = []
): ObstacleCover {
  // traceLine excludes both endpoints; we manually include the target cell.
  const intermediate = traceLine(from, to);
  const cellsToCheck = [...intermediate, to];
  const fullPath = [from, ...intermediate, to];

  let highest: ObstacleCover = "none";
  for (const cell of cellsToCheck) {
    const cellCover = getHighestCover(obstacles, cell);
    if (COVER_RANK[cellCover] > COVER_RANK[highest]) {
      highest = cellCover;
    }
    // Short-circuit: can't get higher than full
    if (highest === "full") {
      return "full";
    }
  }

  // Phase 10: Check edge obstacles for cover contribution.
  // Use cellsToCheck (intermediate + target) so the edge adjacent to the target is also evaluated —
  // consistent with the cell-cover policy of including the target cell.
  for (let i = 0; i < fullPath.length - 1; i++) {
    const edge = findEdgeBetween(edgeObstacles, fullPath[i], fullPath[i + 1]);
    if (edge && edge.cover !== "none" && COVER_RANK[edge.cover] > COVER_RANK[highest]) {
      highest = edge.cover;
    }
    // Short-circuit: can't get higher than full
    if (highest === "full") {
      return "full";
    }
  }

  return highest;
}
