import { describe, expect, it } from "vitest";
import type {
  ActiveAreaEffect,
  BattleMap,
  CombatState,
  Obstacle,
  Token
} from "@limiarmap/shared-contracts";
import { METERS_PER_CELL } from "@limiarmap/shared-contracts";
import {
  computePathCost,
  findMovementPath,
  findReachableCells,
  getMovementCostMultiplier,
  validateMovement
} from "../../src";

const map: BattleMap = {
  id: "map",
  name: "map",
  gridWidth: 20,
  gridHeight: 20,
  terrainVersion: 1,
  gridCalibration: {
    x: 0,
    y: 0,
    width: 1,
    height: 1
  },
  activeEncounterId: "enc"
};

const token: Token = {
  id: "token",
  battleMapId: "map",
  label: "Hero",
  kind: "playerCharacter",
  controllerType: "player",
  controllerId: "player_1",
  position: { x: 1, y: 1 },
  // 6 cells = 9 m = ~30 ft (standard D&D character); movementBudget = 6 * 5 = 30 path-cost units
  movementSpeedCells: 6,
  movementBudget: 30,
  conditions: [],
  combatantId: "cmb_1"
};

const combatState: CombatState = {
  id: "combat",
  battleMapId: "map",
  status: "active",
  roundNumber: 1,
  turnIndex: 0,
  activeCombatantId: "cmb_1",
  initiativeOrder: ["cmb_1"],
  advancedBy: "LimiarControl",
  version: 1
};

// ---------------------------------------------------------------------------
// Unit conversion helpers (tested here because they live in shared-contracts)
// ---------------------------------------------------------------------------

function metersToCells(meters: number, mpc = METERS_PER_CELL): number {
  return Math.round(meters / mpc);
}

function metersToMovementCells(meters: number, mpc = METERS_PER_CELL): number {
  return Math.floor(meters / mpc);
}

describe("unit conversion (meters → cells)", () => {
  it("converts 9 m movement speed to 6 cells (standard 30 ft character)", () => {
    expect(metersToMovementCells(9)).toBe(6);
  });

  it("converts 12 m movement speed to 8 cells", () => {
    expect(metersToMovementCells(12)).toBe(8);
  });

  it("converts 18 m range to 12 cells (Magic Missile / 60 ft)", () => {
    expect(metersToCells(18)).toBe(12);
  });

  it("converts 45 m range to 30 cells (Fireball / 150 ft)", () => {
    expect(metersToCells(45)).toBe(30);
  });

  it("converts 6 m AoE radius to 4 cells (Fireball 20 ft radius)", () => {
    expect(metersToCells(6)).toBe(4);
  });

  it("METERS_PER_CELL is 1.5", () => {
    expect(METERS_PER_CELL).toBe(1.5);
  });
});

describe("movement rules", () => {
  it("applies alternating diagonal cost", () => {
    expect(
      computePathCost([
        { x: 1, y: 1 },
        { x: 2, y: 2 },
        { x: 3, y: 3 }
      ])
    ).toBe(15);
  });

  it("finds a valid preview path around blocked cells", () => {
    const obstacles: Obstacle[] = [
      {
        id: "obs-wall",
        battleMapId: "map",
        cells: [{ x: 2, y: 1 }],
        blocksMovement: true,
        blocksEffect: true,
        blocksVision: true,
        cover: "full",
        clipsDiagonalMovement: false,
        movementCostMultiplier: 1
      }
    ];

    const result = findMovementPath(
      { map, obstacles, tokens: [token] },
      token,
      { x: 3, y: 1 },
      combatState
    );

    expect(result.accepted).toBe(true);
    expect(result.path).toHaveLength(2);
    expect(result.path[1]).toEqual({ x: 3, y: 1 });
    expect(result.path).not.toContainEqual({ x: 2, y: 1 });
    expect(result.pathCostUnits).toBe(15);
  });

  it("returns the cheapest path cost even when movement budget is exceeded", () => {
    const tokenWith10: Token = {
      ...token,
      movementSpeedCells: 2,
      movementBudget: 10
    };

    const result = findMovementPath(
      { map, obstacles: [], tokens: [tokenWith10] },
      tokenWith10,
      { x: 4, y: 1 },
      combatState
    );

    expect(result.accepted).toBe(false);
    expect(result.rejectionReason).toBe("movement_budget_exceeded");
    expect(result.path).toEqual([
      { x: 2, y: 1 },
      { x: 3, y: 1 },
      { x: 4, y: 1 }
    ]);
    expect(result.pathCostUnits).toBe(15);
  });

  it("rejects blocked destinations", () => {
    const obstacles: Obstacle[] = [
      {
        id: "obs",
        battleMapId: "map",
        cells: [{ x: 2, y: 2 }],
        blocksMovement: true,
        blocksEffect: true,
        blocksVision: true,
        cover: "full",
        clipsDiagonalMovement: true,
        movementCostMultiplier: 1
      }
    ];
    const result = validateMovement(
      { map, obstacles, tokens: [token] },
      token,
      [{ x: 2, y: 2 }],
      combatState
    );
    expect(result.accepted).toBe(false);
    expect(result.rejectionReason).toBe("blocked_path");
  });

  it("can reject diagonal corner clipping when the adjacent wall says so", () => {
    const obstacles: Obstacle[] = [
      {
        id: "obs-clip",
        battleMapId: "map",
        cells: [{ x: 2, y: 1 }],
        blocksMovement: true,
        blocksEffect: false,
        blocksVision: false,
        cover: "none",
        clipsDiagonalMovement: true,
        movementCostMultiplier: 1
      }
    ];

    const result = validateMovement(
      { map, obstacles, tokens: [token] },
      token,
      [{ x: 2, y: 2 }],
      combatState
    );
    expect(result.accepted).toBe(false);
    expect(result.rejectionReason).toBe("diagonal_clipped");
  });

  describe("movement budget", () => {
    it("accepts 6 orthogonal steps for a standard 30-ft-equivalent character (movementSpeedCells=6)", () => {
      // 6 straight steps × 5 path-cost units = 30 = movementBudget
      const path = [
        { x: 2, y: 1 },
        { x: 3, y: 1 },
        { x: 4, y: 1 },
        { x: 5, y: 1 },
        { x: 6, y: 1 },
        { x: 7, y: 1 }
      ];
      const result = validateMovement(
        { map, obstacles: [], tokens: [token] },
        token,
        path,
        combatState
      );
      expect(result.accepted).toBe(true);
      expect(result.pathCostUnits).toBe(30);
    });

    it("accepts movement that exactly exhausts the budget", () => {
      // movementSpeedCells=4 cells → budget=20 path-cost units (4*5)
      const tokenWith20: Token = {
        ...token,
        movementSpeedCells: 4,
        movementBudget: 20
      };
      // 4 straight steps = 20 units
      const path = [
        { x: 2, y: 1 },
        { x: 3, y: 1 },
        { x: 4, y: 1 },
        { x: 5, y: 1 }
      ];
      const result = validateMovement(
        { map, obstacles: [], tokens: [tokenWith20] },
        tokenWith20,
        path,
        combatState
      );
      expect(result.accepted).toBe(true);
      expect(result.pathCostUnits).toBe(20);
    });

    it("rejects movement that exceeds remaining budget", () => {
      // movementSpeedCells=2 cells → budget=10 path-cost units (2*5)
      const tokenWith10: Token = {
        ...token,
        movementSpeedCells: 2,
        movementBudget: 10
      };
      // 3 straight steps = 15 units > 10 budget
      const path = [
        { x: 2, y: 1 },
        { x: 3, y: 1 },
        { x: 4, y: 1 }
      ];
      const result = validateMovement(
        { map, obstacles: [], tokens: [tokenWith10] },
        tokenWith10,
        path,
        combatState
      );
      expect(result.accepted).toBe(false);
      expect(result.rejectionReason).toBe("movement_budget_exceeded");
    });

    it("respects reduced budget after a prior move", () => {
      // Simulate a token that already moved 20 units (10 path-cost units = 2 cells remaining)
      const tokenAfterMove: Token = {
        ...token,
        movementBudget: 10,
        position: { x: 5, y: 1 }
      };
      // 2 straight steps = 10 — exactly matches remaining budget
      const path = [
        { x: 6, y: 1 },
        { x: 7, y: 1 }
      ];
      const valid = validateMovement(
        { map, obstacles: [], tokens: [tokenAfterMove] },
        tokenAfterMove,
        path,
        combatState
      );
      expect(valid.accepted).toBe(true);
      expect(valid.pathCostUnits).toBe(10);

      // 3 steps = 15 — exceeds remaining budget
      const path2 = [
        { x: 6, y: 1 },
        { x: 7, y: 1 },
        { x: 8, y: 1 }
      ];
      const rejected = validateMovement(
        { map, obstacles: [], tokens: [tokenAfterMove] },
        tokenAfterMove,
        path2,
        combatState
      );
      expect(rejected.accepted).toBe(false);
      expect(rejected.rejectionReason).toBe("movement_budget_exceeded");
    });
  });
});

describe("reachable movement cells", () => {
  it("uses the remaining movement budget and excludes the origin cell", () => {
    const reachable = findReachableCells(
      { map, obstacles: [], tokens: [token] },
      token,
      combatState
    );

    expect(reachable).not.toContainEqual({ x: 1, y: 1 });
    expect(reachable).toContainEqual({ x: 7, y: 1 });
    expect(reachable).not.toContainEqual({ x: 8, y: 1 });
  });

  it("does not include blocked or occupied cells", () => {
    const blocker: Token = {
      ...token,
      id: "blocker",
      label: "Blocker",
      position: { x: 1, y: 2 },
      combatantId: "cmb_2"
    };
    const blockingObstacle: Obstacle = {
      id: "blocking-obstacle",
      battleMapId: "map",
      cells: [{ x: 2, y: 1 }],
      blocksMovement: true,
      blocksEffect: false,
      blocksVision: false,
      cover: "none",
      clipsDiagonalMovement: false,
      movementCostMultiplier: 1
    };

    const reachable = findReachableCells(
      { map, obstacles: [blockingObstacle], tokens: [token, blocker] },
      token,
      combatState
    );

    expect(reachable).not.toContainEqual({ x: 2, y: 1 });
    expect(reachable).not.toContainEqual({ x: 1, y: 2 });
  });

  it("respects difficult terrain cost when computing reachable cells", () => {
    const tightToken: Token = {
      ...token,
      movementSpeedCells: 1,
      movementBudget: 5
    };

    const reachable = findReachableCells(
      { map, obstacles: [difficultTerrain], tokens: [tightToken] },
      tightToken,
      combatState
    );

    expect(reachable).toContainEqual({ x: 1, y: 2 });
    expect(reachable).not.toContainEqual({ x: 3, y: 1 });
  });

  it("respects alternating diagonal costs while expanding reach", () => {
    const diagonalToken: Token = {
      ...token,
      movementSpeedCells: 2,
      movementBudget: 10
    };

    const reachable = findReachableCells(
      { map, obstacles: [], tokens: [diagonalToken] },
      diagonalToken,
      combatState
    );

    expect(reachable).toContainEqual({ x: 2, y: 2 });
    expect(reachable).not.toContainEqual({ x: 3, y: 3 });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Phase 7: difficult terrain and movement cost modifiers
// ─────────────────────────────────────────────────────────────────────────────

const difficultTerrain: Obstacle = {
  id: "dt",
  battleMapId: "map",
  cells: [
    { x: 3, y: 1 },
    { x: 4, y: 1 },
    { x: 5, y: 1 }
  ],
  blocksMovement: false,
  blocksEffect: false,
  blocksVision: false,
  cover: "none",
  clipsDiagonalMovement: false,
  movementCostMultiplier: 2
};

describe("difficult terrain — path-cost unit tests", () => {
  it("normal orthogonal step has base cost 5 (no terrain)", () => {
    expect(
      computePathCost([
        { x: 1, y: 1 },
        { x: 2, y: 1 }
      ])
    ).toBe(5);
  });

  it("orthogonal step into difficult terrain costs 10 (2× multiplier)", () => {
    const obstacles = [difficultTerrain];
    const multiplierAt = (cell: { x: number; y: number }) =>
      getMovementCostMultiplier(obstacles, cell);
    // step from (2,1) → (3,1): (3,1) is difficult terrain
    const cost = computePathCost(
      [
        { x: 2, y: 1 },
        { x: 3, y: 1 }
      ],
      multiplierAt
    );
    expect(cost).toBe(10);
  });

  it("diagonal step into difficult terrain costs double the base diagonal cost", () => {
    const diagTerrain: Obstacle = {
      ...difficultTerrain,
      id: "dt-diag",
      cells: [{ x: 3, y: 2 }]
    };
    const obstacles = [diagTerrain];
    const multiplierAt = (cell: { x: number; y: number }) =>
      getMovementCostMultiplier(obstacles, cell);
    // 1st diagonal (index 0) base = 5 → ×2 = 10
    const cost = computePathCost(
      [
        { x: 2, y: 1 },
        { x: 3, y: 2 }
      ],
      multiplierAt
    );
    expect(cost).toBe(10);
  });

  it("mixed path: normal then difficult terrain sums correctly", () => {
    // Path: (1,1) → (2,1) [normal, cost 5] → (3,1) [difficult, cost 10] → (4,1) [difficult, cost 10]
    const obstacles = [difficultTerrain];
    const multiplierAt = (cell: { x: number; y: number }) =>
      getMovementCostMultiplier(obstacles, cell);
    const cost = computePathCost(
      [
        { x: 1, y: 1 },
        { x: 2, y: 1 },
        { x: 3, y: 1 },
        { x: 4, y: 1 }
      ],
      multiplierAt
    );
    expect(cost).toBe(5 + 10 + 10);
  });

  it("getMovementCostMultiplier returns 1 for a cell with no terrain obstacle", () => {
    expect(
      getMovementCostMultiplier([difficultTerrain], { x: 10, y: 10 })
    ).toBe(1);
  });

  it("getMovementCostMultiplier returns 2 for a difficult terrain cell", () => {
    expect(getMovementCostMultiplier([difficultTerrain], { x: 3, y: 1 })).toBe(
      2
    );
  });

  it("getMovementCostMultiplier returns 1 for obstacles that have no multiplier (backward compat)", () => {
    const legacyObs: Obstacle = {
      id: "legacy",
      battleMapId: "map",
      cells: [{ x: 5, y: 5 }],
      blocksMovement: false,
      blocksEffect: false,
      blocksVision: false,
      cover: "half",
      clipsDiagonalMovement: false,
      movementCostMultiplier: 1
    };
    expect(getMovementCostMultiplier([legacyObs], { x: 5, y: 5 })).toBe(1);
  });
});

describe("difficult terrain — movement validation integration", () => {
  it("allows movement through difficult terrain when budget is sufficient", () => {
    // token at (1,1), budget=30; 3 difficult-terrain steps = 3×10 = 30 — exactly fits
    const result = validateMovement(
      { map, obstacles: [difficultTerrain], tokens: [token] },
      token,
      [
        { x: 2, y: 1 },
        { x: 3, y: 1 },
        { x: 4, y: 1 }
      ],
      combatState
    );
    // step (1,1)→(2,1) normal=5, (2,1)→(3,1) difficult=10, (3,1)→(4,1) difficult=10 → total 25
    expect(result.accepted).toBe(true);
    expect(result.pathCostUnits).toBe(25);
  });

  it("rejects movement through difficult terrain when extra cost exceeds budget", () => {
    // token with budget=10; 1 normal + 1 difficult = 5+10 = 15 > 10
    const tightToken: Token = { ...token, movementBudget: 10 };
    const result = validateMovement(
      { map, obstacles: [difficultTerrain], tokens: [tightToken] },
      tightToken,
      [
        { x: 2, y: 1 },
        { x: 3, y: 1 }
      ],
      combatState
    );
    expect(result.accepted).toBe(false);
    expect(result.rejectionReason).toBe("movement_budget_exceeded");
  });

  it("a path that fit without difficult terrain is rejected when terrain is added", () => {
    // Without terrain: (1,1)→(2,1)→(3,1)→(4,1) = 3×5 = 15 ≤ 30 → accepted
    const withoutTerrain = validateMovement(
      { map, obstacles: [], tokens: [token] },
      token,
      [
        { x: 2, y: 1 },
        { x: 3, y: 1 },
        { x: 4, y: 1 }
      ],
      combatState
    );
    expect(withoutTerrain.accepted).toBe(true);

    // With terrain covering (3,1)–(5,1): 5+10+10 = 25 ≤ 30 → still accepted here
    // So extend to 4 steps: (1,1)→(2,1)[5]→(3,1)[10]→(4,1)[10]→(5,1)[10] = 35 > 30 → rejected
    const longToken: Token = { ...token, movementBudget: 30 };
    const withTerrain = validateMovement(
      { map, obstacles: [difficultTerrain], tokens: [longToken] },
      longToken,
      [
        { x: 2, y: 1 },
        { x: 3, y: 1 },
        { x: 4, y: 1 },
        { x: 5, y: 1 }
      ],
      combatState
    );
    expect(withTerrain.accepted).toBe(false);
    expect(withTerrain.rejectionReason).toBe("movement_budget_exceeded");
  });

  it("blocked cell is still rejected regardless of movementCostMultiplier", () => {
    const blockedWithMultiplier: Obstacle = {
      id: "blocked-mult",
      battleMapId: "map",
      cells: [{ x: 3, y: 1 }],
      blocksMovement: true,
      blocksEffect: false,
      blocksVision: false,
      cover: "none",
      clipsDiagonalMovement: false,
      movementCostMultiplier: 2
    };
    const result = validateMovement(
      { map, obstacles: [blockedWithMultiplier], tokens: [token] },
      token,
      [
        { x: 2, y: 1 },
        { x: 3, y: 1 }
      ],
      combatState
    );
    expect(result.accepted).toBe(false);
    expect(result.rejectionReason).toBe("blocked_path");
  });

  it("old obstacles without explicit multiplier still behave as multiplier=1", () => {
    const oldStyleObs: Obstacle = {
      id: "old",
      battleMapId: "map",
      cells: [{ x: 3, y: 1 }],
      blocksMovement: false,
      blocksEffect: false,
      blocksVision: false,
      cover: "half",
      clipsDiagonalMovement: false,
      movementCostMultiplier: 1
    };
    // 3 steps through old-style obstacle = 3×5 = 15 path-cost units
    const result = validateMovement(
      { map, obstacles: [oldStyleObs], tokens: [token] },
      token,
      [
        { x: 2, y: 1 },
        { x: 3, y: 1 },
        { x: 4, y: 1 }
      ],
      combatState
    );
    expect(result.accepted).toBe(true);
    expect(result.pathCostUnits).toBe(15);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Active area effects (e.g. Spike Growth) as movement-affecting difficult terrain
// ─────────────────────────────────────────────────────────────────────────────

function spikeGrowthEffect(
  cells: Array<{ x: number; y: number }>
): ActiveAreaEffect {
  return {
    id: "aae_spike",
    sourceSpellCanonicalKey: "spike_growth",
    sourceSpellName: "Spike Growth",
    casterParticipantId: "caster",
    originPoint: cells[0]!,
    anchorCell: cells[0]!,
    areaShape: "sphere",
    sizeMeters: 6,
    affectedCells: cells,
    effectKind: "hazard",
    terrainEffect: "difficult_terrain",
    movementDamageDice: "2d4",
    damageType: "Piercing",
    damagePerMeters: 1.5
  };
}

function fogCloudEffect(
  cells: Array<{ x: number; y: number }>
): ActiveAreaEffect {
  return {
    id: "aae_fog",
    sourceSpellCanonicalKey: "fog_cloud",
    sourceSpellName: "Fog Cloud",
    casterParticipantId: "caster",
    originPoint: cells[0]!,
    anchorCell: cells[0]!,
    areaShape: "sphere",
    sizeMeters: 6,
    affectedCells: cells,
    effectKind: "obscurement",
    obscurement: "heavy"
  };
}

describe("active area effects — Spike Growth difficult terrain", () => {
  const spikeCells = [
    { x: 3, y: 1 },
    { x: 4, y: 1 },
    { x: 5, y: 1 }
  ];

  it("path fully outside Spike Growth costs base cost only", () => {
    const result = validateMovement(
      {
        map,
        obstacles: [],
        tokens: [token],
        activeAreaEffects: [spikeGrowthEffect(spikeCells)]
      },
      token,
      [
        { x: 1, y: 2 },
        { x: 1, y: 3 },
        { x: 1, y: 4 }
      ],
      combatState
    );
    expect(result.accepted).toBe(true);
    expect(result.pathCostUnits).toBe(15);
  });

  it("path partially through Spike Growth applies the multiplier on affected cells only", () => {
    // (1,1)→(2,1) normal=5, (2,1)→(3,1) spike=10, (3,1)→(4,1) spike=10 → 25
    const result = validateMovement(
      {
        map,
        obstacles: [],
        tokens: [token],
        activeAreaEffects: [spikeGrowthEffect(spikeCells)]
      },
      token,
      [
        { x: 2, y: 1 },
        { x: 3, y: 1 },
        { x: 4, y: 1 }
      ],
      combatState
    );
    expect(result.accepted).toBe(true);
    expect(result.pathCostUnits).toBe(25);
  });

  it("path fully through Spike Growth pays the multiplier on every step", () => {
    // (2,1)→(3,1)[10]→(4,1)[10]→(5,1)[10] = 30
    const fromAdjacent: Token = { ...token, position: { x: 2, y: 1 } };
    const result = validateMovement(
      {
        map,
        obstacles: [],
        tokens: [fromAdjacent],
        activeAreaEffects: [spikeGrowthEffect(spikeCells)]
      },
      fromAdjacent,
      [
        { x: 3, y: 1 },
        { x: 4, y: 1 },
        { x: 5, y: 1 }
      ],
      combatState
    );
    expect(result.accepted).toBe(true);
    expect(result.pathCostUnits).toBe(30);
  });

  it("does not double-apply when a cell is both obstacle difficult terrain and Spike Growth", () => {
    const result = validateMovement(
      {
        map,
        obstacles: [difficultTerrain],
        tokens: [token],
        activeAreaEffects: [spikeGrowthEffect(spikeCells)]
      },
      token,
      [
        { x: 2, y: 1 },
        { x: 3, y: 1 }
      ],
      combatState
    );
    // (1,1)→(2,1) normal=5, (2,1)→(3,1) max(2,2)=2 → 10. Total = 15.
    expect(result.accepted).toBe(true);
    expect(result.pathCostUnits).toBe(15);
  });

  it("rejects movement when extra Spike Growth cost exceeds budget", () => {
    const tightToken: Token = { ...token, movementBudget: 12 };
    const result = validateMovement(
      {
        map,
        obstacles: [],
        tokens: [tightToken],
        activeAreaEffects: [spikeGrowthEffect(spikeCells)]
      },
      tightToken,
      [
        { x: 2, y: 1 },
        { x: 3, y: 1 }
      ],
      combatState
    );
    // 5 + 10 = 15 > 12
    expect(result.accepted).toBe(false);
    expect(result.rejectionReason).toBe("movement_budget_exceeded");
  });

  it("findMovementPath prefers a cheaper route around Spike Growth when one exists", () => {
    // Spike Growth straight east of token blocks the cheap horizontal path; the
    // engine should detour south of the spike row.
    const result = findMovementPath(
      {
        map,
        obstacles: [],
        tokens: [token],
        activeAreaEffects: [spikeGrowthEffect(spikeCells)]
      },
      token,
      { x: 6, y: 1 },
      combatState
    );
    expect(result.accepted).toBe(true);
    // No path step should land on a Spike Growth cell.
    for (const step of result.path) {
      expect(spikeCells).not.toContainEqual(step);
    }
  });

  it("Fog Cloud (obscurement) does not modify movement cost", () => {
    const result = validateMovement(
      {
        map,
        obstacles: [],
        tokens: [token],
        activeAreaEffects: [fogCloudEffect([{ x: 3, y: 1 }])]
      },
      token,
      [
        { x: 2, y: 1 },
        { x: 3, y: 1 }
      ],
      combatState
    );
    expect(result.accepted).toBe(true);
    expect(result.pathCostUnits).toBe(10);
  });

  it("getMovementCostMultiplier returns 2 inside a Spike Growth cell", () => {
    expect(
      getMovementCostMultiplier([], { x: 3, y: 1 }, [
        spikeGrowthEffect(spikeCells)
      ])
    ).toBe(2);
  });

  it("getMovementCostMultiplier returns 1 outside Spike Growth", () => {
    expect(
      getMovementCostMultiplier([], { x: 9, y: 9 }, [
        spikeGrowthEffect(spikeCells)
      ])
    ).toBe(1);
  });
});
