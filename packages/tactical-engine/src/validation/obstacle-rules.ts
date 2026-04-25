import type {
  ActiveAreaEffect,
  Coordinate,
  Obstacle,
  ObstacleCover
} from "@limiarmap/shared-contracts";
import { coordinateKey } from "../grid/coordinates";

/**
 * Multiplier applied to movement cost for cells covered by an active area
 * effect whose `terrainEffect` marks them as difficult terrain (e.g. Spike
 * Growth). Stacking with map-level difficult terrain is handled by `max`
 * semantics in `getMovementCostMultiplier` — overlapping difficult terrains
 * do not double-apply.
 */
const DIFFICULT_TERRAIN_MULTIPLIER = 2;

function hasObstacleAtCell(
  obstacles: Obstacle[],
  coordinate: Coordinate,
  predicate: (obstacle: Obstacle) => boolean
): boolean {
  const key = coordinateKey(coordinate);
  return obstacles.some(
    (obstacle) =>
      predicate(obstacle) &&
      obstacle.cells.some((cell) => coordinateKey(cell) === key)
  );
}

export function blocksEffect(
  obstacles: Obstacle[],
  coordinate: Coordinate
): boolean {
  return hasObstacleAtCell(
    obstacles,
    coordinate,
    (obstacle) => obstacle.blocksEffect
  );
}

export function blocksVision(
  obstacles: Obstacle[],
  coordinate: Coordinate
): boolean {
  return hasObstacleAtCell(
    obstacles,
    coordinate,
    (obstacle) => obstacle.blocksVision
  );
}

export function clipsDiagonalMovement(
  obstacles: Obstacle[],
  coordinate: Coordinate
): boolean {
  return hasObstacleAtCell(
    obstacles,
    coordinate,
    (obstacle) => obstacle.clipsDiagonalMovement
  );
}

/**
 * Phase 7: Returns the highest movement cost multiplier that applies to
 * `coordinate` across all obstacles.
 *
 * - Defaults to 1 (normal terrain) when no obstacle carries a multiplier > 1.
 * - When multiple obstacles overlap the same cell (e.g. stacked effects), the
 *   highest multiplier wins — consistent with how cover uses COVER_RANK.
 * - Blocked cells (blocksMovement = true) are rejected before this value is
 *   ever consulted; the multiplier on a blocked cell has no mechanical effect.
 */
export function getMovementCostMultiplier(
  obstacles: Obstacle[],
  coordinate: Coordinate,
  activeAreaEffects: ActiveAreaEffect[] = []
): number {
  const key = coordinateKey(coordinate);
  let max = 1;
  for (const obstacle of obstacles) {
    if (
      obstacle.movementCostMultiplier > 1 &&
      obstacle.cells.some((cell) => coordinateKey(cell) === key)
    ) {
      max = Math.max(max, obstacle.movementCostMultiplier);
    }
  }
  for (const effect of activeAreaEffects) {
    if (
      effect.terrainEffect === "difficult_terrain" &&
      effect.affectedCells.some((cell) => coordinateKey(cell) === key)
    ) {
      max = Math.max(max, DIFFICULT_TERRAIN_MULTIPLIER);
    }
  }
  return max;
}

/**
 * Numeric ranking of cover levels for comparison.
 * Higher value = stronger cover. Used by getHighestCover and evaluateCover.
 */
export const COVER_RANK: Record<ObstacleCover, number> = {
  none: 0,
  half: 1,
  threeQuarters: 2,
  full: 3
};

export function getHighestCover(
  obstacles: Obstacle[],
  coordinate: Coordinate
): ObstacleCover {
  let highestCover: ObstacleCover = "none";
  const key = coordinateKey(coordinate);

  obstacles.forEach((obstacle) => {
    if (!obstacle.cells.some((cell) => coordinateKey(cell) === key)) {
      return;
    }

    if (COVER_RANK[obstacle.cover] > COVER_RANK[highestCover]) {
      highestCover = obstacle.cover;
    }
  });

  return highestCover;
}
