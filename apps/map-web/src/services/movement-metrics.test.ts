import { describe, expect, it } from "vitest";
import {
  formatMeters,
  formatMovementSpeedCellsAsMeters,
  formatPathCostUnitsAsMeters,
  movementSpeedCellsToMeters,
  pathCostUnitsToMeters,
} from "./movement-metrics";

describe("movement metrics formatting", () => {
  it("converts path-cost units to meters using the shared map scale", () => {
    expect(pathCostUnitsToMeters(30)).toBe(9);
    expect(pathCostUnitsToMeters(15)).toBe(4.5);
  });

  it("converts movement speed cells to meters", () => {
    expect(movementSpeedCellsToMeters(6)).toBe(9);
    expect(movementSpeedCellsToMeters(8)).toBe(12);
  });

  it("formats meter values for the pt-BR combat UI", () => {
    expect(formatMeters(9)).toBe("9");
    expect(formatMeters(4.5)).toBe("4,5");
    expect(formatPathCostUnitsAsMeters(15)).toBe("4,5");
    expect(formatMovementSpeedCellsAsMeters(6)).toBe("9");
  });
});
