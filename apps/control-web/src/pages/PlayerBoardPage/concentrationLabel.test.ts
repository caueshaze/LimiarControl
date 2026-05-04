import { describe, expect, it } from "vitest";
import { formatActiveConcentrationLabel } from "./concentrationLabel";

describe("formatActiveConcentrationLabel", () => {
  it("returns null when concentration is null", () => {
    expect(formatActiveConcentrationLabel(null)).toBeNull();
  });

  it("returns null when concentration is undefined", () => {
    expect(formatActiveConcentrationLabel(undefined)).toBeNull();
  });

  it("prefers spellName + variantLabel format", () => {
    const result = formatActiveConcentrationLabel({
      spellName: "Bless",
      variantLabel: "Ally",
      effectIds: ["eff-1"],
    });
    expect(result).toBe("Bless — Ally");
  });

  it("falls back to variantLabel alone when spellName is missing", () => {
    const result = formatActiveConcentrationLabel({
      variantLabel: "Ally",
      effectIds: ["eff-1"],
    });
    expect(result).toBe("Ally");
  });

  it("falls back to spellName alone when variantLabel is missing", () => {
    const result = formatActiveConcentrationLabel({
      spellName: "Bless",
      effectIds: ["eff-1"],
    });
    expect(result).toBe("Bless");
  });

  it("falls back to spellKey when both names are missing", () => {
    const result = formatActiveConcentrationLabel({
      spellKey: "bless",
      effectIds: ["eff-1"],
    });
    expect(result).toBe("bless");
  });

  it("returns null when only effectIds are present", () => {
    const result = formatActiveConcentrationLabel({
      effectIds: ["eff-1"],
    });
    expect(result).toBeNull();
  });
});
