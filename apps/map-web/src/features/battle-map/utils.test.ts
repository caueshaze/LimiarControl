import { describe, expect, it } from "vitest";
import type { Token } from "@limiarmap/shared-contracts";
import {
  deriveGridCalibrationFromTwoPoints,
  findTokenAtCell,
  tokenOccupiesCell
} from "./utils";

function token(overrides: Partial<Token> = {}): Token {
  return {
    id: "t1",
    battleMapId: "m",
    label: "Hero",
    kind: "playerCharacter",
    controllerType: "player",
    controllerId: "p1",
    position: { x: 3, y: 3 },
    movementSpeedCells: 6,
    movementBudget: 30,
    conditions: [],
    ...overrides,
  };
}

describe("tokenOccupiesCell", () => {
  it("stops matching extra cells after temporary footprint is removed", () => {
    const enlarged = token({
      base_size: "Medium",
      effective_size: "Large",
      effective_footprint: { width: 2, height: 2 },
    });
    const reverted = token({ base_size: "Medium" });

    expect(tokenOccupiesCell(enlarged, { x: 4, y: 4 })).toBe(true);
    expect(tokenOccupiesCell(reverted, { x: 4, y: 4 })).toBe(false);
  });
});

describe("findTokenAtCell", () => {
  it("does not select a reverted token from a former extra footprint cell", () => {
    const enlarged = token({
      id: "hero",
      base_size: "Medium",
      effective_size: "Large",
      effective_footprint: { width: 2, height: 2 },
    });
    const reverted = token({ id: "hero", base_size: "Medium" });

    expect(findTokenAtCell([enlarged], { x: 4, y: 4 })?.id).toBe("hero");
    expect(findTokenAtCell([reverted], { x: 4, y: 4 })).toBeUndefined();
  });
});

describe("deriveGridCalibrationFromTwoPoints", () => {
  it("derives calibration from two points in normal order", () => {
    const result = deriveGridCalibrationFromTwoPoints(
      { x: 100, y: 80 },
      { x: 900, y: 680 },
      10,
      12,
      1000,
      800
    );

    expect(result).toEqual({
      gridCalibration: {
        x: 0.1,
        y: 0.1,
        width: 0.8,
        height: 0.75
      },
      gridWidth: 10,
      gridHeight: 12
    });
  });

  it("normalizes point order before deriving calibration", () => {
    const result = deriveGridCalibrationFromTwoPoints(
      { x: 900, y: 680 },
      { x: 100, y: 80 },
      10,
      12,
      1000,
      800
    );

    expect(result.gridCalibration).toEqual({
      x: 0.1,
      y: 0.1,
      width: 0.8,
      height: 0.75
    });
  });

  it("supports calibrating only a partial map segment", () => {
    const result = deriveGridCalibrationFromTwoPoints(
      { x: 200, y: 150 },
      { x: 500, y: 390 },
      6,
      8,
      1200,
      900
    );

    expect(result.gridCalibration).toEqual({
      x: 200 / 1200,
      y: 150 / 900,
      width: 300 / 1200,
      height: 240 / 900
    });
    expect(result.gridWidth).toBe(6);
    expect(result.gridHeight).toBe(8);
  });

  it("rejects invalid dimensions and degenerate segments", () => {
    expect(() =>
      deriveGridCalibrationFromTwoPoints(
        { x: 100, y: 100 },
        { x: 100, y: 300 },
        0,
        4,
        1000,
        800
      )
    ).toThrow("invalid_grid_dimensions");

    expect(() =>
      deriveGridCalibrationFromTwoPoints(
        { x: 100, y: 100 },
        { x: 100, y: 300 },
        4,
        4,
        1000,
        800
      )
    ).toThrow("invalid_calibration_segment");
  });
});
