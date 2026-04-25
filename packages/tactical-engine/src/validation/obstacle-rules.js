import { coordinateKey } from "../grid/coordinates";
const DIFFICULT_TERRAIN_MULTIPLIER = 2;
function hasObstacleAtCell(obstacles, coordinate, predicate) {
  const key = coordinateKey(coordinate);
  return obstacles.some(
    (obstacle) =>
      predicate(obstacle) &&
      obstacle.cells.some((cell) => coordinateKey(cell) === key)
  );
}
export function blocksEffect(obstacles, coordinate) {
  return hasObstacleAtCell(
    obstacles,
    coordinate,
    (obstacle) => obstacle.blocksEffect
  );
}
export function blocksVision(obstacles, coordinate) {
  return hasObstacleAtCell(
    obstacles,
    coordinate,
    (obstacle) => obstacle.blocksVision
  );
}
export function clipsDiagonalMovement(obstacles, coordinate) {
  return hasObstacleAtCell(
    obstacles,
    coordinate,
    (obstacle) => obstacle.clipsDiagonalMovement
  );
}
export function getMovementCostMultiplier(
  obstacles,
  coordinate,
  activeAreaEffects = []
) {
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
export const COVER_RANK = {
  none: 0,
  half: 1,
  threeQuarters: 2,
  full: 3
};
const coverRank = COVER_RANK;
export function getHighestCover(obstacles, coordinate) {
  let highestCover = "none";
  const key = coordinateKey(coordinate);
  obstacles.forEach((obstacle) => {
    if (!obstacle.cells.some((cell) => coordinateKey(cell) === key)) {
      return;
    }
    if (coverRank[obstacle.cover] > coverRank[highestCover]) {
      highestCover = obstacle.cover;
    }
  });
  return highestCover;
}
