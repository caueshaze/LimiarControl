import type {
  ActiveAreaEffect,
  BattleMap,
  CellElevation,
  Coordinate,
  EdgeObstacle,
  Obstacle,
  Token
} from "@limiarmap/shared-contracts";
import { coordinateKey } from "./coordinates";

export interface GridState {
  map: BattleMap;
  obstacles: Obstacle[];
  edgeObstacles?: EdgeObstacle[];
  tokens: Token[];
  /**
   * Persistent combat-state-only area effects (e.g. Spike Growth) that may
   * influence movement cost or other tactical resolution. Map-level terrain
   * lives on `obstacles`; these never mutate the campaign map.
   */
  activeAreaEffects?: ActiveAreaEffect[];
  /**
   * Per-cell elevation metadata for fall detection and vertical movement.
   * Default elevation for missing cells is 0.
   */
  cellElevations?: CellElevation[];
}

export function isInsideMap(
  gridState: GridState,
  coordinate: Coordinate
): boolean {
  return (
    coordinate.x >= 0 &&
    coordinate.y >= 0 &&
    coordinate.x < gridState.map.gridWidth &&
    coordinate.y < gridState.map.gridHeight
  );
}

export function isBlockedCell(
  gridState: GridState,
  coordinate: Coordinate
): boolean {
  const key = coordinateKey(coordinate);
  return gridState.obstacles.some(
    (obstacle) =>
      obstacle.blocksMovement &&
      obstacle.cells.some((cell) => coordinateKey(cell) === key)
  );
}

export function findOccupyingToken(
  gridState: GridState,
  coordinate: Coordinate
): Token | undefined {
  const key = coordinateKey(coordinate);
  return gridState.tokens.find(
    (token) => coordinateKey(token.position) === key
  );
}

/**
 * Phase 10: Look up the canonical edge between two adjacent orthogonal cells
 * from a plain array of edge obstacles.
 *
 * Separated from getEdgeBetweenCells so that callers that only have an
 * EdgeObstacle[] (e.g. LoS/LoE utilities) don't need a full GridState.
 */
export function findEdgeBetween(
  edgeObstacles: EdgeObstacle[] = [],
  fromCell: Coordinate,
  toCell: Coordinate
): EdgeObstacle | undefined {
  const dx = toCell.x - fromCell.x;
  const dy = toCell.y - fromCell.y;

  if (Math.abs(dx) + Math.abs(dy) !== 1) return undefined;

  let direction: "N" | "E" | "S" | "W";
  if (dx === 1) direction = "E";
  else if (dx === -1) direction = "W";
  else if (dy === 1) direction = "S";
  else direction = "N";

  return edgeObstacles.find(
    (e) => e.x === fromCell.x && e.y === fromCell.y && e.direction === direction
  );
}

/**
 * Phase 10: Check if there's a blocking edge between two adjacent cells.
 */
export function getEdgeBetweenCells(
  gridState: GridState,
  fromCell: Coordinate,
  toCell: Coordinate
): EdgeObstacle | undefined {
  return findEdgeBetween(gridState.edgeObstacles ?? [], fromCell, toCell);
}

/**
 * Phase 10: Check if movement is blocked by an edge between two cells.
 */
export function isEdgeBlocked(
  gridState: GridState,
  fromCell: Coordinate,
  toCell: Coordinate
): boolean {
  const edge = getEdgeBetweenCells(gridState, fromCell, toCell);
  return edge?.blocksMovement ?? false;
}

/**
 * Phase 10: Check if vision is blocked by an edge between two cells.
 */
export function isEdgeBlockingVision(
  gridState: GridState,
  fromCell: Coordinate,
  toCell: Coordinate
): boolean {
  const edge = getEdgeBetweenCells(gridState, fromCell, toCell);
  return edge?.blocksVision ?? false;
}

/**
 * Phase 10: Check if effects are blocked by an edge between two cells.
 */
export function isEdgeBlockingEffect(
  gridState: GridState,
  fromCell: Coordinate,
  toCell: Coordinate
): boolean {
  const edge = getEdgeBetweenCells(gridState, fromCell, toCell);
  return edge?.blocksEffect ?? false;
}

/**
 * Phase 10: Get edge cover value between two cells.
 */
export function getEdgeCover(
  gridState: GridState,
  fromCell: Coordinate,
  toCell: Coordinate
): "none" | "half" | "threeQuarters" | "full" {
  const edge = getEdgeBetweenCells(gridState, fromCell, toCell);
  return edge?.cover ?? "none";
}

/**
 * Build a coordinate-keyed index from a CellElevation array.
 * Construct once per context (e.g. before a path-cost loop) and reuse.
 */
export function buildElevationIndex(
  cellElevations: CellElevation[] = []
): Map<string, number> {
  const index = new Map<string, number>();
  for (const entry of cellElevations) {
    index.set(coordinateKey(entry.cell), entry.elevationMeters);
  }
  return index;
}

/**
 * Look up the elevation for a single cell using a pre-built index.
 * Returns 0 for cells not in the index.
 */
export function getCellElevation(
  elevationIndex: Map<string, number>,
  cell: Coordinate
): number {
  return elevationIndex.get(coordinateKey(cell)) ?? 0;
}
