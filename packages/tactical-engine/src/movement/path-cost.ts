import type { Coordinate } from "@limiarmap/shared-contracts";

export function isDiagonalStep(from: Coordinate, to: Coordinate): boolean {
  return Math.abs(from.x - to.x) === 1 && Math.abs(from.y - to.y) === 1;
}

/**
 * Cost of a single step entering `to` from `from`.
 *
 * Base costs follow the standard D&D 5e alternating-diagonal rule:
 *   - Orthogonal: 5 units
 *   - Diagonal (odd index, i.e. 1st, 3rd…): 5 units
 *   - Diagonal (even index, i.e. 2nd, 4th…): 10 units
 *
 * Phase 7: `cellMultiplier` is applied to the base cost of the destination
 * cell. Normal terrain = 1 (default). Difficult terrain = 2.
 * Cost is based on the cell being entered, not the origin cell.
 */
export function stepCost(
  from: Coordinate,
  to: Coordinate,
  diagonalIndex: number,
  cellMultiplier = 1
): number {
  const baseCost = isDiagonalStep(from, to) ? (diagonalIndex % 2 === 0 ? 5 : 10) : 5;
  return baseCost * cellMultiplier;
}

/**
 * Total path cost in path-cost units.
 *
 * @param path     Ordered list of cells starting from the token's current
 *                 position (inclusive).
 * @param getMultiplier  Optional callback returning the movement cost
 *                 multiplier for a given destination cell. Defaults to 1
 *                 (normal terrain) when omitted — preserves full backward
 *                 compatibility with maps that have no terrain data.
 */
export function computePathCost(
  path: Coordinate[],
  getMultiplier?: (cell: Coordinate) => number
): number {
  let total = 0;
  let diagonalIndex = 0;

  for (let index = 1; index < path.length; index += 1) {
    const dest = path[index];
    const multiplier = getMultiplier ? getMultiplier(dest) : 1;
    const cost = stepCost(path[index - 1], dest, diagonalIndex, multiplier);
    total += cost;

    if (isDiagonalStep(path[index - 1], dest)) {
      diagonalIndex += 1;
    }
  }

  return total;
}
