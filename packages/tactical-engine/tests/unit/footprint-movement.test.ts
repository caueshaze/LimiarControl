import { describe, expect, it } from "vitest";
import type { Token } from "@limiarmap/shared-contracts";
import {
  validateMovement,
  findReachableCells,
  findMovementPath,
} from "../../src";
import { makeGridState } from "./helpers/grid-state-fixture";

function token(overrides: Partial<Token> = {}): Token {
  return {
    id: "t1",
    battleMapId: "m",
    label: "Hero",
    kind: "playerCharacter",
    controllerType: "player",
    controllerId: "p1",
    position: { x: 5, y: 5 },
    movementSpeedCells: 6,
    movementBudget: 30,
    conditions: [],
    combatantId: "cmb_1",
    ...overrides,
  };
}

describe("validateMovement with Large footprint", () => {
  it("rejects move to cell occupied by Medium token", () => {
    const hero = token({ id: "hero", position: { x: 5, y: 5 }, base_size: "Large" as any });
    const medium = token({ id: "medium", position: { x: 6, y: 5 } });

    const gs = makeGridState({ tokens: [hero, medium], obstacles: [] });
    const result = validateMovement(gs, hero, [{ x: 6, y: 5 }]);

    expect(result.accepted).toBe(false);
    expect(result.rejectionReason).toBe("occupied_cell");
  });

  it("accepts move when all footprint cells are free", () => {
    const hero = token({ id: "hero", position: { x: 5, y: 5 }, base_size: "Large" as any });

    const gs = makeGridState({ tokens: [hero], obstacles: [] });
    const result = validateMovement(gs, hero, [{ x: 6, y: 5 }, { x: 7, y: 5 }]);

    expect(result.accepted).toBe(true);
  });

  it("rejects move if any footprint cell is blocked", () => {
    const hero = token({ id: "hero", position: { x: 5, y: 5 }, base_size: "Large" as any });
    const obstacle = {
      id: "obs",
      battleMapId: "m",
      cells: [{ x: 7, y: 5 }],
      blocksMovement: true,
      blocksEffect: true,
      blocksVision: false,
      cover: "none" as const,
      clipsDiagonalMovement: false,
      movementCostMultiplier: 1,
    };

    const gs = makeGridState({ tokens: [hero], obstacles: [obstacle] });
    const result = validateMovement(gs, hero, [{ x: 6, y: 5 }, { x: 7, y: 5 }]);

    expect(result.accepted).toBe(false);
    expect(result.rejectionReason).toBe("blocked_path");
  });

  it("rejects move that would go outside map bounds", () => {
    const hero = token({ id: "hero", position: { x: 9, y: 9 }, base_size: "Large" as any });

    const gs = makeGridState({ tokens: [hero], obstacles: [], map: { gridWidth: 10, gridHeight: 10 } });
    const result = validateMovement(gs, hero, [{ x: 10, y: 9 }]);

    expect(result.accepted).toBe(false);
    expect(result.rejectionReason).toBe("outside_map");
  });

  it("Medium token (1x1) unchanged behavior: move accepted to empty cell", () => {
    const hero = token({ id: "hero", position: { x: 5, y: 5 } });

    const gs = makeGridState({ tokens: [hero], obstacles: [] });
    const result = validateMovement(gs, hero, [{ x: 6, y: 5 }]);

    expect(result.accepted).toBe(true);
  });

  it("Medium token (1x1) unchanged behavior: move rejected to occupied cell", () => {
    const hero = token({ id: "hero", position: { x: 5, y: 5 } });
    const other = token({ id: "other", position: { x: 6, y: 5 } });

    const gs = makeGridState({ tokens: [hero, other], obstacles: [] });
    const result = validateMovement(gs, hero, [{ x: 6, y: 5 }]);

    expect(result.accepted).toBe(false);
    expect(result.rejectionReason).toBe("occupied_cell");
  });
});

describe("findReachableCells with Large footprint", () => {
  it("Large token cannot enter corridor of width 1", () => {
    const large = token({ id: "large", position: { x: 1, y: 1 }, base_size: "Large" as any });
    const wall = {
      id: "wall",
      battleMapId: "m",
      cells: [{ x: 2, y: 0 }, { x: 2, y: 2 }],
      blocksMovement: true,
      blocksEffect: true,
      blocksVision: false,
      cover: "none" as const,
      clipsDiagonalMovement: false,
      movementCostMultiplier: 1,
    };

    const gs = makeGridState({ tokens: [large], obstacles: [wall] });
    const reachable = findReachableCells(gs, large);

    expect(reachable.some((c) => c.x === 2 && c.y === 1)).toBe(false);
  });

  it("Large token can traverse corridor of width 2", () => {
    const large = token({ id: "large", position: { x: 1, y: 1 }, base_size: "Large" as any });

    const gs = makeGridState({ tokens: [large], obstacles: [] });
    const reachable = findReachableCells(gs, large);

    expect(reachable).toContainEqual({ x: 3, y: 1 });
  });
});

describe("findMovementPath with Large footprint", () => {
  it("rejects path to cell occupied by another token", () => {
    const hero = token({ id: "hero", position: { x: 5, y: 5 }, base_size: "Large" as any });
    const enemy = token({ id: "enemy", position: { x: 6, y: 5 } });

    const gs = makeGridState({ tokens: [hero, enemy], obstacles: [] });
    const result = findMovementPath(gs, hero, { x: 6, y: 5 });

    expect(result.accepted).toBe(false);
    expect(result.rejectionReason).toBe("occupied_cell");
  });

  it("accepts path to empty destination", () => {
    const hero = token({ id: "hero", position: { x: 5, y: 5 }, base_size: "Large" as any });

    const gs = makeGridState({ tokens: [hero], obstacles: [] });
    const result = findMovementPath(gs, hero, { x: 7, y: 5 });

    expect(result.accepted).toBe(true);
  });
});
