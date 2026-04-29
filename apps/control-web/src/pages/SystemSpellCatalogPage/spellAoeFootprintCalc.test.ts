import { describe, expect, it } from "vitest";
import {
  computeAoeFootprint,
  getRequiredDimensionField,
} from "./spellAoeFootprintCalc";

describe("getRequiredDimensionField", () => {
  it("returns radiusMeters for sphere", () => {
    expect(getRequiredDimensionField("sphere")).toBe("radiusMeters");
  });

  it("returns radiusMeters for cylinder", () => {
    expect(getRequiredDimensionField("cylinder")).toBe("radiusMeters");
  });

  it("returns lengthMeters for cone", () => {
    expect(getRequiredDimensionField("cone")).toBe("lengthMeters");
  });

  it("returns lengthMeters for line", () => {
    expect(getRequiredDimensionField("line")).toBe("lengthMeters");
  });

  it("returns sideMeters for cube", () => {
    expect(getRequiredDimensionField("cube")).toBe("sideMeters");
  });
});

describe("computeAoeFootprint", () => {
  describe("sphere", () => {
    it("includes origin and cardinal edge cells for radius 4", () => {
      // Fireball: 6m radius / 1.5m per cell = 4 cells
      const cells = computeAoeFootprint("sphere", 4);
      const coordSet = new Set(cells.map((c) => `${c.x},${c.y}`));
      expect(coordSet.has("0,0")).toBe(true);
      expect(coordSet.has("0,-4")).toBe(true);
      expect(coordSet.has("4,0")).toBe(true);
      expect(coordSet.has("0,4")).toBe(true);
      expect(coordSet.has("-4,0")).toBe(true);
    });

    it("does not return 81 cells for radius 4 (not a Chebyshev square)", () => {
      const cells = computeAoeFootprint("sphere", 4);
      expect(cells).not.toHaveLength(81);
    });

    it("does not render sphere/cylinder as Chebyshev squares", () => {
      const cells4 = computeAoeFootprint("sphere", 4);
      const coords = new Set(cells4.map((c) => `${c.x},${c.y}`));
      // Chebyshev corners would be included in a square; euclidean must exclude them
      expect(coords.has("-4,-4")).toBe(false);
      expect(coords.has("4,4")).toBe(false);
      expect(coords.has("-4,4")).toBe(false);
      expect(coords.has("4,-4")).toBe(false);
    });

    it("uses euclidean distance: cells satisfy x²+y² ≤ r²", () => {
      const r = 3;
      const cells = computeAoeFootprint("sphere", r);
      for (const { x, y } of cells) {
        expect(x * x + y * y).toBeLessThanOrEqual(r * r);
      }
    });
  });

  describe("cylinder", () => {
    it("produces same footprint as sphere", () => {
      expect(computeAoeFootprint("cylinder", 2)).toEqual(
        computeAoeFootprint("sphere", 2),
      );
    });
  });

  describe("cone", () => {
    it("does not include origin (matches combat behavior)", () => {
      const cells = computeAoeFootprint("cone", 2);
      expect(cells).not.toContainEqual({ x: 0, y: 0 });
    });

    it("step 1 has width 1 (only center cell, matching resolveCone spread)", () => {
      const cells = computeAoeFootprint("cone", 2);
      const coordSet = new Set(cells.map((c) => `${c.x},${c.y}`));
      // at x=1: spread -(1-1)..+(1-1) = 0..0 → only (1,0)
      expect(coordSet.has("1,0")).toBe(true);
      expect(coordSet.has("1,-1")).toBe(false);
      expect(coordSet.has("1,1")).toBe(false);
    });

    it("step 2 has width 3 (matching resolveCone spread)", () => {
      const cells = computeAoeFootprint("cone", 2);
      const coordSet = new Set(cells.map((c) => `${c.x},${c.y}`));
      // at x=2: spread -(2-1)..+(2-1) = -1..1
      expect(coordSet.has("2,-1")).toBe(true);
      expect(coordSet.has("2,0")).toBe(true);
      expect(coordSet.has("2,1")).toBe(true);
      expect(coordSet.has("2,-2")).toBe(false);
      expect(coordSet.has("2,2")).toBe(false);
    });

    it("does not include cells beyond the size", () => {
      const cells = computeAoeFootprint("cone", 2);
      expect(cells.some((c) => c.x > 2)).toBe(false);
    });
  });

  describe("line", () => {
    it("returns cells in a straight horizontal line", () => {
      const cells = computeAoeFootprint("line", 3);
      expect(cells).toEqual([
        { x: 1, y: 0 },
        { x: 2, y: 0 },
        { x: 3, y: 0 },
      ]);
    });

    it("has length equal to sizeCells", () => {
      expect(computeAoeFootprint("line", 4)).toHaveLength(4);
    });

    it("does not include origin", () => {
      const cells = computeAoeFootprint("line", 2);
      expect(cells).not.toContainEqual({ x: 0, y: 0 });
    });
  });

  describe("cube", () => {
    it("size 2 produces a 2x2 square anchored at (0,0)", () => {
      const cells = computeAoeFootprint("cube", 2);
      expect(cells).toHaveLength(4);
      expect(cells).toContainEqual({ x: 0, y: 0 });
      expect(cells).toContainEqual({ x: 1, y: 1 });
    });

    it("size 3 produces 9 cells", () => {
      expect(computeAoeFootprint("cube", 3)).toHaveLength(9);
    });
  });

  it("returns empty array for unknown shape", () => {
    expect(computeAoeFootprint("unknown_shape", 3)).toEqual([]);
  });
});
