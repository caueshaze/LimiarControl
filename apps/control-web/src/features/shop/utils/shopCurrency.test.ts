import { describe, expect, it } from "vitest";
import { getItemPriceCopperValue } from "./shopCurrency";

describe("shopCurrency", () => {
  it("prioritizes explicit copper value when available", () => {
    expect(getItemPriceCopperValue(12, 155)).toBe(155);
  });

  it("falls back to gp price converted to copper", () => {
    expect(getItemPriceCopperValue(2.5, null)).toBe(250);
  });

  it("returns zero for invalid values", () => {
    expect(getItemPriceCopperValue(undefined, undefined)).toBe(0);
    expect(getItemPriceCopperValue(-1, null)).toBe(0);
  });
});
