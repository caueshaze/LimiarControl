import type { Coordinate } from "@limiarmap/shared-contracts";

/**
 * Traces all grid cells that a line from the center of `from` to the center
 * of `to` passes through, **excluding both endpoints**.
 *
 * Uses the supercover variant of Bresenham's line algorithm: every cell the
 * line intersects is included, not just the primary Bresenham cells. This
 * prevents "squeezing" a line past a diagonal obstacle.
 *
 * When the line passes exactly through a cell corner (the decision variable
 * is zero), a single diagonal step is taken — neither adjacent cell is added.
 * This matches the D&D 5e convention that a line through a corner does not
 * count as passing through the cells adjacent to that corner.
 *
 * Intended for LoS/LoE checks: the origin is where the actor stands and
 * the target is what they're aiming at, so neither should block the trace.
 */
export function traceLine(from: Coordinate, to: Coordinate): Coordinate[] {
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  const nx = Math.abs(dx);
  const ny = Math.abs(dy);
  const signX = dx > 0 ? 1 : -1;
  const signY = dy > 0 ? 1 : -1;

  // Same cell — no intermediate cells
  if (nx === 0 && ny === 0) {
    return [];
  }

  const result: Coordinate[] = [];
  let x = from.x;
  let y = from.y;
  let ix = 0;
  let iy = 0;

  while (ix < nx || iy < ny) {
    // decision > 0  → next boundary crossed is horizontal → step Y
    // decision < 0  → next boundary crossed is vertical   → step X
    // decision == 0 → line crosses a corner exactly        → diagonal step
    const decision = (1 + 2 * ix) * ny - (1 + 2 * iy) * nx;

    if (decision === 0) {
      x += signX;
      y += signY;
      ix += 1;
      iy += 1;
    } else if (decision < 0) {
      x += signX;
      ix += 1;
    } else {
      y += signY;
      iy += 1;
    }

    // Skip the target cell — caller decides whether it blocks
    if (x === to.x && y === to.y) {
      continue;
    }

    result.push({ x, y });
  }

  return result;
}
