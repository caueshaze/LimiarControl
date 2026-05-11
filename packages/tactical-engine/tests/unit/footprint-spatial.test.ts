import { describe, expect, it } from "vitest";
import type { Token } from "@limiarmap/shared-contracts";
import {
  getOccupiedCells,
  findTokensOccupyingCell,
  canGrowTo,
  getTokenFootprint as fp,
} from "../../src";
import { makeGridState } from "./helpers/grid-state-fixture";

function token(position: { x: number; y: number }, baseSize?: string): Token {
  return {
    id: "t",
    battleMapId: "m",
    label: "T",
    kind: "playerCharacter",
    controllerType: "player",
    controllerId: "p1",
    position,
    movementSpeedCells: 6,
    movementBudget: 30,
    conditions: [],
    ...(baseSize ? { base_size: baseSize as any } : {}),
  };
}

describe("getOccupiedCells", () => {
  it("1x1 token occupies only anchor cell", () => {
    const cells = getOccupiedCells({ x: 3, y: 4 }, { width: 1, height: 1 });
    expect(cells).toEqual([{ x: 3, y: 4 }]);
  });

  it("2x2 token occupies 4 cells from anchor (3,3)", () => {
    const cells = getOccupiedCells({ x: 3, y: 3 }, { width: 2, height: 2 });
    expect(cells).toEqual([
      { x: 3, y: 3 },
      { x: 4, y: 3 },
      { x: 3, y: 4 },
      { x: 4, y: 4 },
    ]);
  });

  it("3x3 token occupies 9 cells", () => {
    const cells = getOccupiedCells({ x: 0, y: 0 }, { width: 3, height: 3 });
    expect(cells).toHaveLength(9);
  });
});

describe("getTokenFootprint", () => {
  it("token without base_size defaults to 1x1", () => {
    const t = token({ x: 5, y: 5 });
    expect(fp(t)).toEqual({ width: 1, height: 1 });
  });

  it("Large token returns 2x2", () => {
    const t = token({ x: 5, y: 5 }, "Large");
    expect(fp(t)).toEqual({ width: 2, height: 2 });
  });

  it("returns to base footprint when temporary effective footprint is removed", () => {
    const enlarged = {
      ...token({ x: 5, y: 5 }, "Medium"),
      effective_size: "Large",
      effective_footprint: { width: 2, height: 2 },
    } as Token;
    const reverted = {
      ...enlarged,
      effective_size: undefined,
      effective_footprint: undefined,
    } as Token;

    expect(fp(enlarged)).toEqual({ width: 2, height: 2 });
    expect(fp(reverted)).toEqual({ width: 1, height: 1 });
  });
});

describe("findTokensOccupyingCell", () => {
  it("finds token whose anchor cell matches", () => {
    const gs = makeGridState({
      tokens: [token({ x: 3, y: 3 })],
      obstacles: [],
    });
    const found = findTokensOccupyingCell(gs, { x: 3, y: 3 });
    expect(found).toHaveLength(1);
  });

  it("finds Large token by any cell of its footprint", () => {
    const largeToken: Token = {
      id: "large",
      battleMapId: "m",
      label: "Large",
      kind: "enemy",
      controllerType: "gm",
      controllerId: "gm",
      position: { x: 3, y: 3 },
      movementSpeedCells: 6,
      movementBudget: 30,
      conditions: [],
      base_size: "Large",
    } as Token;
    const gs = makeGridState({ tokens: [largeToken], obstacles: [] });

    expect(findTokensOccupyingCell(gs, { x: 3, y: 3 })).toHaveLength(1);
    expect(findTokensOccupyingCell(gs, { x: 4, y: 3 })).toHaveLength(1);
    expect(findTokensOccupyingCell(gs, { x: 3, y: 4 })).toHaveLength(1);
    expect(findTokensOccupyingCell(gs, { x: 4, y: 4 })).toHaveLength(1);
  });

  it("does NOT find token on cells outside footprint", () => {
    const largeToken: Token = {
      id: "large",
      battleMapId: "m",
      label: "Large",
      kind: "enemy",
      controllerType: "gm",
      controllerId: "gm",
      position: { x: 3, y: 3 },
      movementSpeedCells: 6,
      movementBudget: 30,
      conditions: [],
      base_size: "Large",
    } as Token;
    const gs = makeGridState({ tokens: [largeToken], obstacles: [] });

    expect(findTokensOccupyingCell(gs, { x: 5, y: 5 })).toHaveLength(0);
  });

  it("stops occupying extra cells after temporary footprint reverts", () => {
    const enlarged = {
      ...token({ x: 3, y: 3 }, "Medium"),
      id: "hero",
      effective_size: "Large",
      effective_footprint: { width: 2, height: 2 },
    } as Token;
    const reverted = {
      ...enlarged,
      effective_size: undefined,
      effective_footprint: undefined,
    } as Token;

    expect(findTokensOccupyingCell(makeGridState({ tokens: [enlarged], obstacles: [] }), { x: 4, y: 4 })).toHaveLength(1);
    expect(findTokensOccupyingCell(makeGridState({ tokens: [reverted], obstacles: [] }), { x: 4, y: 4 })).toHaveLength(0);
  });

  it("excludeTokenId excludes the token itself", () => {
    const t = token({ x: 3, y: 3 });
    const gs = makeGridState({ tokens: [t], obstacles: [] });
    expect(findTokensOccupyingCell(gs, { x: 3, y: 3 }, "t")).toHaveLength(0);
  });
});

describe("canGrowTo", () => {
  it("allows growth when all cells are free", () => {
    const gs = makeGridState({
      tokens: [],
      obstacles: [],
    });
    expect(canGrowTo({ x: 3, y: 3 }, { width: 2, height: 2 }, gs)).toBe(true);
  });

  it("rejects growth against blocked cell", () => {
    const gs = makeGridState({
      tokens: [],
      obstacles: [
        {
          id: "obs",
          battleMapId: "m",
          cells: [{ x: 4, y: 3 }],
          blocksMovement: true,
          blocksEffect: true,
          blocksVision: false,
          cover: "none" as const,
          clipsDiagonalMovement: false,
          movementCostMultiplier: 1,
        },
      ],
    });
    expect(canGrowTo({ x: 3, y: 3 }, { width: 2, height: 2 }, gs)).toBe(false);
  });

  it("rejects growth outside map bounds", () => {
    const gs = makeGridState({ tokens: [], obstacles: [], map: { gridWidth: 5, gridHeight: 5 } });
    expect(canGrowTo({ x: 4, y: 4 }, { width: 2, height: 2 }, gs)).toBe(false);
  });

  it("rejects growth over another token", () => {
    const gs = makeGridState({
      tokens: [token({ x: 4, y: 3 })],
      obstacles: [],
    });
    expect(canGrowTo({ x: 3, y: 3 }, { width: 2, height: 2 }, gs)).toBe(false);
  });

  it("does NOT reject growth just because anchor cell has the token itself", () => {
    const t = token({ x: 3, y: 3 }, "Medium");
    const gs = makeGridState({ tokens: [t], obstacles: [] });
    expect(canGrowTo({ x: 3, y: 3 }, { width: 2, height: 2 }, gs, "t")).toBe(true);
  });
});
