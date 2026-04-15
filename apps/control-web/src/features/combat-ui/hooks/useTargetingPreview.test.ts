import { describe, expect, it } from "vitest";
import { classifyRange, metersToCells, METERS_PER_CELL } from "./useTargetingPreview";

describe("metersToCells", () => {
  it("converts meters to whole cells using the grid scale", () => {
    expect(metersToCells(1.5)).toBe(1);
    expect(metersToCells(3)).toBe(2);
    expect(metersToCells(9)).toBe(6);
    expect(metersToCells(18)).toBe(12);
  });

  it("rounds to at least one cell", () => {
    expect(metersToCells(0.1)).toBe(1);
  });

  it("uses the exported cell scale", () => {
    expect(METERS_PER_CELL).toBe(1.5);
  });
});

describe("classifyRange", () => {
  it("returns unknown when distance is missing", () => {
    expect(classifyRange(null, 9, 36)).toEqual({ status: "unknown", hasDisadvantage: false });
  });

  it("returns unknown when ranges are absent", () => {
    expect(classifyRange(5, null, null)).toEqual({ status: "unknown", hasDisadvantage: false });
  });

  it("returns normal within the normal range", () => {
    expect(classifyRange(9, 9, 36)).toEqual({ status: "normal", hasDisadvantage: false });
  });

  it("returns long and flags disadvantage within the long range", () => {
    expect(classifyRange(20, 9, 36)).toEqual({ status: "long", hasDisadvantage: true });
  });

  it("returns out of range beyond the long range", () => {
    expect(classifyRange(40, 9, 36)).toEqual({ status: "out", hasDisadvantage: false });
  });

  it("treats distance equal to normal range as still normal", () => {
    expect(classifyRange(9, 9, 36).status).toBe("normal");
  });

  it("returns out when only normal range is set and distance exceeds it", () => {
    expect(classifyRange(10, 9, null).status).toBe("out");
  });
});
