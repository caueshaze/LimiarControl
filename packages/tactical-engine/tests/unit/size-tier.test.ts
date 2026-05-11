import { describe, expect, it } from "vitest";
import {
  getEffectiveSize,
  getEffectiveFootprint,
  sizeTierToFootprint,
  DEFAULT_CREATURE_SIZE,
  creatureSizeSchema,
} from "@limiarmap/shared-contracts";

describe("size tier enum", () => {
  it("has correct values", () => {
    expect(creatureSizeSchema.enum.Tiny).toBe("Tiny");
    expect(creatureSizeSchema.enum.Small).toBe("Small");
    expect(creatureSizeSchema.enum.Medium).toBe("Medium");
    expect(creatureSizeSchema.enum.Large).toBe("Large");
    expect(creatureSizeSchema.enum.Huge).toBe("Huge");
    expect(creatureSizeSchema.enum.Gargantuan).toBe("Gargantuan");
  });
});

describe("getEffectiveSize", () => {
  it("resolve Medium +1 step = Large", () => {
    expect(getEffectiveSize("Medium", [1])).toBe("Large");
  });

  it("resolve Large -1 step = Medium", () => {
    expect(getEffectiveSize("Large", [-1])).toBe("Medium");
  });

  it("clamps Tiny -1 step to Tiny", () => {
    expect(getEffectiveSize("Tiny", [-1])).toBe("Tiny");
  });

  it("resolve Huge +1 step = Gargantuan", () => {
    expect(getEffectiveSize("Huge", [1])).toBe("Gargantuan");
  });

  it("clamp to ceiling: Medium +99 → Gargantuan", () => {
    expect(getEffectiveSize("Medium", [99])).toBe("Gargantuan");
  });

  it("clamp to floor: Gargantuan -99 → Tiny", () => {
    expect(getEffectiveSize("Gargantuan", [-99])).toBe("Tiny");
  });

  it("sum simple: +1 + +1 = +2 (Medium → Large → Huge)", () => {
    expect(getEffectiveSize("Medium", [1, 1])).toBe("Huge");
  });

  it("empty step_deltas returns base", () => {
    expect(getEffectiveSize("Large", [])).toBe("Large");
  });

  it("ignores non-numeric step_deltas via caller", () => {
    expect(getEffectiveSize("Medium", [])).toBe("Medium");
  });
});

describe("getEffectiveFootprint", () => {
  it("Tiny → 1x1", () => {
    expect(getEffectiveFootprint("Tiny")).toEqual({ width: 1, height: 1 });
  });

  it("Small → 1x1", () => {
    expect(getEffectiveFootprint("Small")).toEqual({ width: 1, height: 1 });
  });

  it("Medium → 1x1", () => {
    expect(getEffectiveFootprint("Medium")).toEqual({ width: 1, height: 1 });
  });

  it("Large → 2x2", () => {
    expect(getEffectiveFootprint("Large")).toEqual({ width: 2, height: 2 });
  });

  it("Huge → 3x3", () => {
    expect(getEffectiveFootprint("Huge")).toEqual({ width: 3, height: 3 });
  });

  it("Gargantuan → 4x4", () => {
    expect(getEffectiveFootprint("Gargantuan")).toEqual({ width: 4, height: 4 });
  });
});

describe("sizeTierToFootprint", () => {
  it("1x1 for Tiny, Small, Medium", () => {
    for (const size of ["Tiny", "Small", "Medium"] as const) {
      expect(sizeTierToFootprint[size]).toEqual({ width: 1, height: 1 });
    }
  });

  it("2x2 for Large", () => {
    expect(sizeTierToFootprint["Large"]).toEqual({ width: 2, height: 2 });
  });

  it("3x3 for Huge", () => {
    expect(sizeTierToFootprint["Huge"]).toEqual({ width: 3, height: 3 });
  });

  it("4x4 for Gargantuan", () => {
    expect(sizeTierToFootprint["Gargantuan"]).toEqual({ width: 4, height: 4 });
  });
});

describe("DEFAULT_CREATURE_SIZE", () => {
  it("is Medium", () => {
    expect(DEFAULT_CREATURE_SIZE).toBe("Medium");
  });
});
