import { coordinateKey } from "./coordinates";
export function isInsideMap(gridState, coordinate) {
  return (
    coordinate.x >= 0 &&
    coordinate.y >= 0 &&
    coordinate.x < gridState.map.gridWidth &&
    coordinate.y < gridState.map.gridHeight
  );
}
export function isBlockedCell(gridState, coordinate) {
  const key = coordinateKey(coordinate);
  return gridState.obstacles.some(
    (obstacle) =>
      obstacle.blocksMovement &&
      obstacle.cells.some((cell) => coordinateKey(cell) === key)
  );
}
export function findOccupyingToken(gridState, coordinate) {
  const key = coordinateKey(coordinate);
  return gridState.tokens.find(
    (token) => coordinateKey(token.position) === key
  );
}
export function findEdgeBetween(edgeObstacles = [], fromCell, toCell) {
  const dx = toCell.x - fromCell.x;
  const dy = toCell.y - fromCell.y;
  if (Math.abs(dx) + Math.abs(dy) !== 1) return undefined;
  let direction;
  if (dx === 1) direction = "E";
  else if (dx === -1) direction = "W";
  else if (dy === 1) direction = "S";
  else direction = "N";
  return edgeObstacles.find(
    (e) => e.x === fromCell.x && e.y === fromCell.y && e.direction === direction
  );
}
export function getEdgeBetweenCells(gridState, fromCell, toCell) {
  return findEdgeBetween(gridState.edgeObstacles, fromCell, toCell);
}
export function isEdgeBlocked(gridState, fromCell, toCell) {
  const edge = getEdgeBetweenCells(gridState, fromCell, toCell);
  return edge?.blocksMovement ?? false;
}
export function isEdgeBlockingVision(gridState, fromCell, toCell) {
  const edge = getEdgeBetweenCells(gridState, fromCell, toCell);
  return edge?.blocksVision ?? false;
}
export function isEdgeBlockingEffect(gridState, fromCell, toCell) {
  const edge = getEdgeBetweenCells(gridState, fromCell, toCell);
  return edge?.blocksEffect ?? false;
}
export function getEdgeCover(gridState, fromCell, toCell) {
  const edge = getEdgeBetweenCells(gridState, fromCell, toCell);
  return edge?.cover ?? "none";
}
