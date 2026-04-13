import type { Coordinate, EdgeObstacle, Obstacle } from "@limiarmap/shared-contracts";
import { blocksEffect } from "../validation/obstacle-rules";
import { findEdgeBetween } from "../grid/grid-state";

/**
 * Resolves a line-shaped AoE from `origin` toward `anchor`.
 *
 * Phase 11: stops when an edge obstacle with `blocksEffect` is crossed, in
 * addition to the existing cell-obstacle stop behaviour. The check uses
 * `findEdgeBetween` on each consecutive step pair so only orthogonal lines
 * get edge blocking; diagonal lines degrade gracefully (no edge model for
 * diagonal crossings).
 */
export function resolveLine(
  origin: Coordinate,
  anchor: Coordinate,
  range: number,
  obstacles: Obstacle[],
  edgeObstacles: EdgeObstacle[] = []
): Coordinate[] {
  const result: Coordinate[] = [];
  const deltaX = Math.sign(anchor.x - origin.x);
  const deltaY = Math.sign(anchor.y - origin.y);
  let prev = origin;

  for (let step = 1; step <= range; step += 1) {
    const coordinate = { x: origin.x + deltaX * step, y: origin.y + deltaY * step };

    if (blocksEffect(obstacles, coordinate)) break;

    // Phase 11: stop when crossing a blocking edge obstacle.
    // findEdgeBetween only matches orthogonal steps; diagonal steps return
    // undefined and fall through (acceptable approximation).
    if (edgeObstacles.length > 0) {
      const crossedEdge = findEdgeBetween(edgeObstacles, prev, coordinate);
      if (crossedEdge?.blocksEffect) break;
    }

    result.push(coordinate);
    prev = coordinate;
  }

  return result;
}
