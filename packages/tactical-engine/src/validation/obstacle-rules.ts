import type { Coordinate, Obstacle, ObstacleCover } from "@limiarmap/shared-contracts";
import { coordinateKey } from "../grid/coordinates";

function hasObstacleAtCell(obstacles: Obstacle[], coordinate: Coordinate, predicate: (obstacle: Obstacle) => boolean): boolean {
  const key = coordinateKey(coordinate);
  return obstacles.some(
    (obstacle) => predicate(obstacle) && obstacle.cells.some((cell) => coordinateKey(cell) === key)
  );
}

export function blocksEffect(obstacles: Obstacle[], coordinate: Coordinate): boolean {
  return hasObstacleAtCell(obstacles, coordinate, (obstacle) => obstacle.blocksEffect);
}

export function blocksVision(obstacles: Obstacle[], coordinate: Coordinate): boolean {
  return hasObstacleAtCell(obstacles, coordinate, (obstacle) => obstacle.blocksVision);
}

export function clipsDiagonalMovement(obstacles: Obstacle[], coordinate: Coordinate): boolean {
  return hasObstacleAtCell(obstacles, coordinate, (obstacle) => obstacle.clipsDiagonalMovement);
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
  coordinate: Coordinate
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

export function getHighestCover(obstacles: Obstacle[], coordinate: Coordinate): ObstacleCover {
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
