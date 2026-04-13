import { describe, expect, it } from "vitest";
import { obstacleSchema, type Obstacle } from "@limiarmap/shared-contracts";
import { hasLineOfEffect, hasLineOfSight, evaluateCover } from "../../src";

describe("line of sight and effect", () => {
  it("blocks line of sight on vision blockers only", () => {
    const obstacles: Obstacle[] = [
      {
        id: "vision-wall",
        battleMapId: "map",
        cells: [{ x: 1, y: 0 }],
        blocksMovement: false,
        blocksEffect: false,
        blocksVision: true,
        cover: "none",
        clipsDiagonalMovement: false,
        movementCostMultiplier: 1
      }
    ];

    expect(hasLineOfSight(obstacles, { x: 0, y: 0 }, { x: 3, y: 0 })).toBe(false);
    expect(hasLineOfEffect(obstacles, { x: 0, y: 0 }, { x: 3, y: 0 })).toBe(true);
  });

  it("blocks line of effect on effect blockers only", () => {
    const obstacles: Obstacle[] = [
      {
        id: "effect-wall",
        battleMapId: "map",
        cells: [{ x: 1, y: 0 }],
        blocksMovement: false,
        blocksEffect: true,
        blocksVision: false,
        cover: "none",
        clipsDiagonalMovement: false,
        movementCostMultiplier: 1
      }
    ];

    expect(hasLineOfSight(obstacles, { x: 0, y: 0 }, { x: 3, y: 0 })).toBe(true);
    expect(hasLineOfEffect(obstacles, { x: 0, y: 0 }, { x: 3, y: 0 })).toBe(false);
  });

  it("solid obstacles block both sight and effect", () => {
    const obstacles: Obstacle[] = [
      {
        id: "solid-wall",
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

    expect(hasLineOfSight(obstacles, { x: 0, y: 0 }, { x: 3, y: 3 })).toBe(false);
    expect(hasLineOfEffect(obstacles, { x: 0, y: 0 }, { x: 3, y: 3 })).toBe(false);
  });

  it("accepts legacy obstacle payloads and maps them to blocksEffect", () => {
    const legacyObstacle = obstacleSchema.parse({
      id: "legacy-wall",
      battleMapId: "map",
      cells: [{ x: 1, y: 0 }],
      blocksMovement: false,
      blocksTargeting: false,
      blocksSpell: true,
      blocksVision: false,
      cover: "none",
      clipsDiagonalMovement: false,
      movementCostMultiplier: 1
    });

    expect(legacyObstacle.blocksEffect).toBe(true);
    expect(hasLineOfEffect([legacyObstacle], { x: 0, y: 0 }, { x: 3, y: 0 })).toBe(false);
  });
});

describe("evaluateCover", () => {
  it("returns none when no obstacles exist", () => {
    expect(evaluateCover([], { x: 0, y: 0 }, { x: 3, y: 0 })).toBe("none");
  });

  it("returns half when a half-cover obstacle is on an intermediate cell", () => {
    const obstacles: Obstacle[] = [
      {
        id: "barricade",
        battleMapId: "map",
        cells: [{ x: 2, y: 0 }],
        blocksMovement: false,
        blocksEffect: false,
        blocksVision: false,
        cover: "half",
        clipsDiagonalMovement: false,
        movementCostMultiplier: 1
      }
    ];
    expect(evaluateCover(obstacles, { x: 0, y: 0 }, { x: 3, y: 0 })).toBe("half");
  });

  it("returns threeQuarters when a three-quarters-cover obstacle is intermediate", () => {
    const obstacles: Obstacle[] = [
      {
        id: "dense-cover",
        battleMapId: "map",
        cells: [{ x: 1, y: 0 }],
        blocksMovement: false,
        blocksEffect: false,
        blocksVision: false,
        cover: "threeQuarters",
        clipsDiagonalMovement: false,
        movementCostMultiplier: 1
      }
    ];
    expect(evaluateCover(obstacles, { x: 0, y: 0 }, { x: 3, y: 0 })).toBe("threeQuarters");
  });

  it("returns full when a full-cover obstacle is on the target cell", () => {
    const obstacles: Obstacle[] = [
      {
        id: "wall-at-target",
        battleMapId: "map",
        cells: [{ x: 3, y: 0 }],
        blocksMovement: true,
        blocksEffect: false,
        blocksVision: false,
        cover: "full",
        clipsDiagonalMovement: false,
        movementCostMultiplier: 1
      }
    ];
    expect(evaluateCover(obstacles, { x: 0, y: 0 }, { x: 3, y: 0 })).toBe("full");
  });

  it("aggregates to the strongest cover when multiple obstacles are present", () => {
    const obstacles: Obstacle[] = [
      {
        id: "barricade",
        battleMapId: "map",
        cells: [{ x: 1, y: 0 }],
        blocksMovement: false,
        blocksEffect: false,
        blocksVision: false,
        cover: "half",
        clipsDiagonalMovement: false,
        movementCostMultiplier: 1
      },
      {
        id: "dense-cover",
        battleMapId: "map",
        cells: [{ x: 2, y: 0 }],
        blocksMovement: false,
        blocksEffect: false,
        blocksVision: false,
        cover: "threeQuarters",
        clipsDiagonalMovement: false,
        movementCostMultiplier: 1
      }
    ];
    // Strongest wins: threeQuarters > half
    expect(evaluateCover(obstacles, { x: 0, y: 0 }, { x: 3, y: 0 })).toBe("threeQuarters");
  });

  it("does not consider the origin cell for cover", () => {
    const obstacles: Obstacle[] = [
      {
        id: "origin-obstacle",
        battleMapId: "map",
        cells: [{ x: 0, y: 0 }],
        blocksMovement: false,
        blocksEffect: false,
        blocksVision: false,
        cover: "full",
        clipsDiagonalMovement: false,
        movementCostMultiplier: 1
      }
    ];
    // Origin cell is excluded: an obstacle at (0,0) when attacking from (0,0)
    // should not contribute cover for the target
    expect(evaluateCover(obstacles, { x: 0, y: 0 }, { x: 1, y: 0 })).toBe("none");
  });

  it("includes the target cell when evaluating cover", () => {
    const obstacles: Obstacle[] = [
      {
        id: "target-shelter",
        battleMapId: "map",
        cells: [{ x: 1, y: 0 }],
        blocksMovement: false,
        blocksEffect: false,
        blocksVision: false,
        cover: "half",
        clipsDiagonalMovement: false,
        movementCostMultiplier: 1
      }
    ];
    // Adjacent attack: from (0,0) to (1,0). No intermediate cells from traceLine,
    // but target cell is included by evaluateCover policy
    expect(evaluateCover(obstacles, { x: 0, y: 0 }, { x: 1, y: 0 })).toBe("half");
  });

  it("evaluates cover independently from LoS/LoE", () => {
    // An obstacle that blocks vision but has no cover should not affect cover result
    const obstacles: Obstacle[] = [
      {
        id: "vision-blocker",
        battleMapId: "map",
        cells: [{ x: 1, y: 0 }],
        blocksMovement: false,
        blocksEffect: false,
        blocksVision: true,
        cover: "none",
        clipsDiagonalMovement: false,
        movementCostMultiplier: 1
      }
    ];
    // LoS fails but cover is still none
    expect(hasLineOfSight(obstacles, { x: 0, y: 0 }, { x: 3, y: 0 })).toBe(false);
    expect(evaluateCover(obstacles, { x: 0, y: 0 }, { x: 3, y: 0 })).toBe("none");
  });

  it("handles diagonal trace with cover on intermediate cell", () => {
    const obstacles: Obstacle[] = [
      {
        id: "diagonal-cover",
        battleMapId: "map",
        cells: [{ x: 1, y: 1 }],
        blocksMovement: false,
        blocksEffect: false,
        blocksVision: false,
        cover: "threeQuarters",
        clipsDiagonalMovement: false,
        movementCostMultiplier: 1
      }
    ];
    // Diagonal from (0,0) to (2,2) passes through (1,1)
    expect(evaluateCover(obstacles, { x: 0, y: 0 }, { x: 2, y: 2 })).toBe("threeQuarters");
  });
});

