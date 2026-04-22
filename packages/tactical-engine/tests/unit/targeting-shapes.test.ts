import { describe, expect, it } from "vitest";
import type { Obstacle } from "@limiarmap/shared-contracts";
import { resolveCone, resolveCube, resolveCylinder, resolveLine, resolveSphere } from "../../src";

describe("targeting shapes", () => {
  it("resolves a line without blocked cells", () => {
    expect(resolveLine({ x: 0, y: 0 }, { x: 3, y: 0 }, 3, [])).toEqual([
      { x: 1, y: 0 },
      { x: 2, y: 0 },
      { x: 3, y: 0 }
    ]);
  });

  it("resolves area shapes deterministically", () => {
    expect(resolveCone({ x: 1, y: 1 }, { x: 3, y: 1 }, 2, []).length).toBeGreaterThan(0);
    expect(resolveSphere({ x: 2, y: 2 }, 1, []).length).toBeGreaterThan(0);
    expect(resolveCylinder({ x: 2, y: 2 }, 1, [])).toEqual(resolveSphere({ x: 2, y: 2 }, 1, []));
    expect(resolveCube({ x: 2, y: 2 }, 2, []).length).toBe(4);
  });

  it("lets effects pass through movement-only obstacles but stops at effect blockers", () => {
    const obstacles: Obstacle[] = [
      {
        id: "move-only",
        battleMapId: "map",
        cells: [{ x: 1, y: 0 }],
        blocksMovement: true,
        blocksEffect: false,
        blocksVision: false,
        cover: "none",
        clipsDiagonalMovement: true,
        movementCostMultiplier: 1
      },
      {
        id: "spell-block",
        battleMapId: "map",
        cells: [{ x: 2, y: 0 }],
        blocksMovement: false,
        blocksEffect: true,
        blocksVision: false,
        cover: "none",
        clipsDiagonalMovement: false,
        movementCostMultiplier: 1
      }
    ];

    expect(resolveLine({ x: 0, y: 0 }, { x: 3, y: 0 }, 3, obstacles)).toEqual([{ x: 1, y: 0 }]);
  });
});
