import { describe, it, expect } from "vitest";
import type { EdgeObstacle, Obstacle } from "@limiarmap/shared-contracts";
import {
  resolveLine,
  resolveCone,
  resolveSphere,
  resolveCube,
  canEffectReachAoE,
  filterByEffectReachability
} from "../../src";

// ─── Shared helpers ──────────────────────────────────────────────────────────

function cellObstacle(id: string, x: number, y: number, opts: { blocksEffect?: boolean; blocksVision?: boolean } = {}): Obstacle {
  return {
    id,
    battleMapId: "map",
    cells: [{ x, y }],
    blocksMovement: false,
    blocksEffect: opts.blocksEffect ?? true,
    blocksVision: opts.blocksVision ?? false,
    cover: "none",
    clipsDiagonalMovement: false,
    movementCostMultiplier: 1
  };
}

function edgeObstacle(id: string, x: number, y: number, dir: "N" | "E" | "S" | "W", opts: { blocksEffect?: boolean; blocksVision?: boolean; blocksMovement?: boolean } = {}): EdgeObstacle {
  return {
    id,
    battleMapId: "map",
    x,
    y,
    direction: dir,
    blocksMovement: opts.blocksMovement ?? false,
    blocksVision: opts.blocksVision ?? false,
    blocksEffect: opts.blocksEffect ?? true,
    cover: "none"
  };
}

// ─── canEffectReachAoE ───────────────────────────────────────────────────────

describe("canEffectReachAoE", () => {
  it("always returns true when no obstacles", () => {
    expect(canEffectReachAoE({ x: 0, y: 0 }, { x: 3, y: 0 }, [], [])).toBe(true);
  });

  it("returns true for the origin cell itself", () => {
    expect(canEffectReachAoE({ x: 5, y: 5 }, { x: 5, y: 5 }, [], [])).toBe(true);
  });

  it("returns true for cells adjacent to origin (no intermediate)", () => {
    expect(canEffectReachAoE({ x: 0, y: 0 }, { x: 1, y: 0 }, [], [edgeObstacle("e", 0, 0, "E")])).toBe(true);
  });

  it("blocks when intermediate cell blocks effect", () => {
    const wall = cellObstacle("w", 1, 0);
    expect(canEffectReachAoE({ x: 0, y: 0 }, { x: 2, y: 0 }, [wall], [])).toBe(false);
  });

  it("blocks when intermediate edge blocks effect", () => {
    const wall = edgeObstacle("e", 1, 0, "E");
    expect(canEffectReachAoE({ x: 0, y: 0 }, { x: 3, y: 0 }, [], [wall])).toBe(false);
  });

  it("blocks on the target-adjacent edge (unlike single-target LoE policy)", () => {
    // Edge between (1,0) and (2,0): target-adjacent edge for origin=(0,0),target=(2,0)
    const wall = edgeObstacle("e", 1, 0, "E");
    expect(canEffectReachAoE({ x: 0, y: 0 }, { x: 2, y: 0 }, [], [wall])).toBe(false);
  });

  it("does not block on a non-effect edge (blocksVision only)", () => {
    const sightOnly = edgeObstacle("e", 1, 0, "E", { blocksEffect: false, blocksVision: true });
    expect(canEffectReachAoE({ x: 0, y: 0 }, { x: 3, y: 0 }, [], [sightOnly])).toBe(true);
  });
});

// ─── resolveLine ─────────────────────────────────────────────────────────────

describe("resolveLine — Phase 11 edge propagation", () => {
  it("backward compatible: no edges → unchanged result", () => {
    expect(resolveLine({ x: 0, y: 0 }, { x: 4, y: 0 }, 4, [])).toEqual([
      { x: 1, y: 0 },
      { x: 2, y: 0 },
      { x: 3, y: 0 },
      { x: 4, y: 0 }
    ]);
  });

  it("stops before the edge when an effect-blocking edge is crossed", () => {
    // Edge between (2,0) and (3,0)
    const wall = edgeObstacle("e", 2, 0, "E");
    expect(resolveLine({ x: 0, y: 0 }, { x: 5, y: 0 }, 5, [], [wall])).toEqual([
      { x: 1, y: 0 },
      { x: 2, y: 0 }
    ]);
  });

  it("stops at first cell blocker even without edge obstacles", () => {
    const blocker = cellObstacle("c", 2, 0);
    expect(resolveLine({ x: 0, y: 0 }, { x: 4, y: 0 }, 4, [blocker], [])).toEqual([{ x: 1, y: 0 }]);
  });

  it("stops at cell blocker before reaching an edge further along", () => {
    const cellWall = cellObstacle("c", 2, 0);
    const edgeWall = edgeObstacle("e", 3, 0, "E");
    expect(resolveLine({ x: 0, y: 0 }, { x: 5, y: 0 }, 5, [cellWall], [edgeWall])).toEqual([{ x: 1, y: 0 }]);
  });

  it("does not stop on a vision-only edge (transparent barrier)", () => {
    const sightOnly = edgeObstacle("e", 2, 0, "E", { blocksEffect: false, blocksVision: true });
    expect(resolveLine({ x: 0, y: 0 }, { x: 5, y: 0 }, 5, [], [sightOnly])).toEqual([
      { x: 1, y: 0 }, { x: 2, y: 0 }, { x: 3, y: 0 }, { x: 4, y: 0 }, { x: 5, y: 0 }
    ]);
  });

  it("vertical line is stopped by a south-facing edge", () => {
    const wall = edgeObstacle("e", 0, 1, "S");
    expect(resolveLine({ x: 0, y: 0 }, { x: 0, y: 4 }, 4, [], [wall])).toEqual([{ x: 0, y: 1 }]);
  });
});

// ─── resolveCone ─────────────────────────────────────────────────────────────

describe("resolveCone — Phase 11 shadow filtering", () => {
  it("backward compatible: no obstacles, same footprint as before", () => {
    const result = resolveCone({ x: 0, y: 0 }, { x: 2, y: 0 }, 2, [], []);
    expect(result.length).toBeGreaterThan(0);
    // No negative-x cells
    expect(result.every((c) => c.x > 0)).toBe(true);
  });

  it("excludes cell directly behind an effect-blocking cell obstacle", () => {
    // Cone going East, blocker at (1,0), cell at (2,0) is shadowed
    const blocker = cellObstacle("c", 1, 0);
    const result = resolveCone({ x: 0, y: 0 }, { x: 3, y: 0 }, 3, [blocker], []);
    expect(result.some((c) => c.x === 2 && c.y === 0)).toBe(false);
    expect(result.some((c) => c.x === 3 && c.y === 0)).toBe(false);
  });

  it("excludes cells shadowed by an effect-blocking edge", () => {
    // Cone going East, edge between (1,0)→(2,0) at (1,0,E)
    const wall = edgeObstacle("e", 1, 0, "E");
    const result = resolveCone({ x: 0, y: 0 }, { x: 4, y: 0 }, 4, [], [wall]);
    // Cells at (2,0), (3,0), (4,0) on the axis are behind the edge
    expect(result.some((c) => c.x >= 2 && c.y === 0)).toBe(false);
  });

  it("cells on the near side of the wall remain included", () => {
    const wall = edgeObstacle("e", 2, 0, "E");
    const result = resolveCone({ x: 0, y: 0 }, { x: 4, y: 0 }, 4, [], [wall]);
    expect(result.some((c) => c.x === 1 && c.y === 0)).toBe(true);
    expect(result.some((c) => c.x === 2 && c.y === 0)).toBe(true);
  });

  it("non-effect edge does not create shadow", () => {
    const sightOnly = edgeObstacle("e", 1, 0, "E", { blocksEffect: false, blocksVision: true });
    const noEdge = resolveCone({ x: 0, y: 0 }, { x: 3, y: 0 }, 3, [], []);
    const withEdge = resolveCone({ x: 0, y: 0 }, { x: 3, y: 0 }, 3, [], [sightOnly]);
    expect(withEdge).toEqual(noEdge);
  });
});

// ─── resolveSphere ───────────────────────────────────────────────────────────

describe("resolveSphere — Phase 11 shadow filtering", () => {
  it("no obstacles: all cells within Euclidean radius included", () => {
    const result = resolveSphere({ x: 5, y: 5 }, 2, [], []);
    // Euclidean radius 2 → circular footprint, 13 cells (dx²+dy² ≤ 4)
    expect(result.length).toBe(13);
  });

  it("sphere does not include Chebyshev corners outside Euclidean radius", () => {
    const result = resolveSphere({ x: 5, y: 5 }, 2, [], []);
    const coords = new Set(result.map((c) => `${c.x},${c.y}`));
    expect(coords.has("3,3")).toBe(false);
    expect(coords.has("7,3")).toBe(false);
    expect(coords.has("3,7")).toBe(false);
    expect(coords.has("7,7")).toBe(false);
    // cardinal edge cells remain included
    expect(coords.has("3,5")).toBe(true);
    expect(coords.has("7,5")).toBe(true);
    expect(coords.has("5,3")).toBe(true);
    expect(coords.has("5,7")).toBe(true);
  });

  it("cells inside radius but behind a cell-obstacle wall are excluded", () => {
    // Wall at (6,5), cells (7,5) and (8,5) should be shadowed from center (5,5)
    const wall = cellObstacle("c", 6, 5);
    const result = resolveSphere({ x: 5, y: 5 }, 3, [wall], []);
    expect(result.some((c) => c.x === 7 && c.y === 5)).toBe(false);
    expect(result.some((c) => c.x === 8 && c.y === 5)).toBe(false);
    // but cells on the origin side are unaffected
    expect(result.some((c) => c.x === 4 && c.y === 5)).toBe(true);
  });

  it("cells behind an effect-blocking edge are excluded", () => {
    // Edge at (5,6,S) = between (5,6) and (5,7). Center=(5,5), radius=3.
    const wall = edgeObstacle("e", 5, 6, "S");
    const result = resolveSphere({ x: 5, y: 5 }, 3, [], [wall]);
    expect(result.some((c) => c.x === 5 && c.y === 7)).toBe(false);
    expect(result.some((c) => c.x === 5 && c.y === 8)).toBe(false);
  });

  it("cells on the same side as center remain included when edge blocks far side", () => {
    const wall = edgeObstacle("e", 5, 6, "S");
    const result = resolveSphere({ x: 5, y: 5 }, 3, [], [wall]);
    expect(result.some((c) => c.x === 5 && c.y === 6)).toBe(true);
    expect(result.some((c) => c.x === 5 && c.y === 5)).toBe(true);
  });

  it("cells immediately adjacent to center are never shadowed (no intermediate cells)", () => {
    // Even with edges all around the center, adjacent cells have no intermediate path
    const walls = [
      edgeObstacle("n", 5, 5, "N"),
      edgeObstacle("s", 5, 5, "S"),
      edgeObstacle("e", 5, 5, "E"),
      edgeObstacle("w", 5, 5, "W")
    ];
    const result = resolveSphere({ x: 5, y: 5 }, 2, [], walls);
    // (5,4) (5,6) (4,5) (6,5) are all adjacent to center → always reachable
    expect(result.some((c) => c.x === 5 && c.y === 4)).toBe(true);
    expect(result.some((c) => c.x === 6 && c.y === 5)).toBe(true);
  });

  it("non-effect edge does not create shadow", () => {
    const sightOnly = edgeObstacle("e", 5, 6, "S", { blocksEffect: false, blocksVision: true });
    const noEdge = resolveSphere({ x: 5, y: 5 }, 2, [], []);
    const withEdge = resolveSphere({ x: 5, y: 5 }, 2, [], [sightOnly]);
    expect(withEdge).toEqual(noEdge);
  });
});

// ─── resolveCube ─────────────────────────────────────────────────────────────

describe("resolveCube — Phase 11 shadow filtering", () => {
  it("backward compatible: no obstacles, all cells in footprint included", () => {
    expect(resolveCube({ x: 0, y: 0 }, 3, [], []).length).toBe(9);
    expect(resolveCube({ x: 2, y: 2 }, 2, [], []).length).toBe(4);
  });

  it("cells behind a cell-obstacle within the cube are excluded", () => {
    // 3×3 cube at (0,0). Wall at (1,0). Cells (2,0) is shadowed from (0,0).
    const wall = cellObstacle("c", 1, 0);
    const result = resolveCube({ x: 0, y: 0 }, 3, [wall], []);
    expect(result.some((c) => c.x === 2 && c.y === 0)).toBe(false);
  });

  it("cells behind an effect-blocking edge within the cube are excluded", () => {
    // 3×3 cube at (0,0). Edge at (1,0,E) = between (1,0) and (2,0).
    const wall = edgeObstacle("e", 1, 0, "E");
    const result = resolveCube({ x: 0, y: 0 }, 3, [], [wall]);
    expect(result.some((c) => c.x === 2 && c.y === 0)).toBe(false);
  });

  it("cells adjacent to anchor are never shadowed", () => {
    const wall = edgeObstacle("e", 1, 0, "E");
    const result = resolveCube({ x: 0, y: 0 }, 3, [], [wall]);
    // (0,0) and (1,0) are reachable (adjacent to anchor or anchor itself)
    expect(result.some((c) => c.x === 0 && c.y === 0)).toBe(true);
    expect(result.some((c) => c.x === 1 && c.y === 0)).toBe(true);
  });
});

// ─── filterByEffectReachability ──────────────────────────────────────────────

describe("filterByEffectReachability", () => {
  it("returns all candidates when edgeObstacles is empty (fast path)", () => {
    const candidates = [{ x: 1, y: 0 }, { x: 2, y: 0 }, { x: 3, y: 0 }];
    expect(filterByEffectReachability({ x: 0, y: 0 }, candidates, [], [])).toEqual(candidates);
  });

  it("filters out candidates blocked by an edge", () => {
    const wall = edgeObstacle("e", 1, 0, "E");
    const candidates = [{ x: 1, y: 0 }, { x: 2, y: 0 }, { x: 3, y: 0 }];
    const result = filterByEffectReachability({ x: 0, y: 0 }, candidates, [], [wall]);
    expect(result).toEqual([{ x: 1, y: 0 }]);
  });
});

// ─── Regression: no-obstacle maps identical to pre-Phase-11 ─────────────────

describe("regression — no obstacles maps unchanged", () => {
  it("resolveLine same result with empty edgeObstacles", () => {
    const a = resolveLine({ x: 0, y: 0 }, { x: 3, y: 0 }, 3, []);
    const b = resolveLine({ x: 0, y: 0 }, { x: 3, y: 0 }, 3, [], []);
    expect(b).toEqual(a);
  });

  it("resolveSphere same result with empty edgeObstacles", () => {
    const a = resolveSphere({ x: 3, y: 3 }, 2, []);
    const b = resolveSphere({ x: 3, y: 3 }, 2, [], []);
    expect(b).toEqual(a);
  });

  it("resolveCube same result with empty edgeObstacles", () => {
    const a = resolveCube({ x: 0, y: 0 }, 3, []);
    const b = resolveCube({ x: 0, y: 0 }, 3, [], []);
    expect(b).toEqual(a);
  });

  it("resolveCone same result with empty edgeObstacles", () => {
    const a = resolveCone({ x: 0, y: 0 }, { x: 3, y: 0 }, 3, []);
    const b = resolveCone({ x: 0, y: 0 }, { x: 3, y: 0 }, 3, [], []);
    expect(b).toEqual(a);
  });
});
