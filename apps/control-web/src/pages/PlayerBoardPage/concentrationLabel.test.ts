import { describe, expect, it } from "vitest";
import { formatActiveConcentrationLabel, getConcentrationReplacementNotice } from "./concentrationLabel";

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

describe("getConcentrationReplacementNotice", () => {
  it("returns null when previous is null (initial load)", () => {
    const result = getConcentrationReplacementNotice(null, {
      spellName: "Haste",
      effectIds: ["eff-1"],
      concentrationGroup: "grp-b",
    });
    expect(result).toBeNull();
  });

  it("returns null when next is null (manual clear)", () => {
    const result = getConcentrationReplacementNotice(
      {
        spellName: "Bless",
        effectIds: ["eff-1"],
        concentrationGroup: "grp-a",
      },
      null,
    );
    expect(result).toBeNull();
  });

  it("returns null when group is the same", () => {
    const result = getConcentrationReplacementNotice(
      {
        spellName: "Bless",
        variantLabel: "Ally",
        effectIds: ["eff-1"],
        concentrationGroup: "grp-a",
      },
      {
        spellName: "Bless",
        variantLabel: "Ally",
        effectIds: ["eff-2"],
        concentrationGroup: "grp-a",
      },
    );
    expect(result).toBeNull();
  });

  it("returns notice when group changes", () => {
    const result = getConcentrationReplacementNotice(
      {
        spellName: "Bless",
        variantLabel: "Ally",
        effectIds: ["eff-1"],
        concentrationGroup: "grp-a",
      },
      {
        spellName: "Haste",
        effectIds: ["eff-2"],
        concentrationGroup: "grp-b",
      },
    );
    expect(result).not.toBeNull();
    expect(result?.previousLabel).toBe("Bless — Ally");
    expect(result?.nextLabel).toBe("Haste");
  });

  it("returns null when both are null", () => {
    const result = getConcentrationReplacementNotice(null, null);
    expect(result).toBeNull();
  });

  it("returns null when both lack group key and same label", () => {
    const result = getConcentrationReplacementNotice(
      {
        spellName: "Bless",
        effectIds: ["eff-1"],
      },
      {
        spellName: "Bless",
        effectIds: ["eff-2"],
      },
    );
    expect(result).toBeNull();
  });

  it("returns notice when both lack group key but labels differ", () => {
    const result = getConcentrationReplacementNotice(
      {
        spellName: "Bless",
        effectIds: ["eff-1"],
      },
      {
        spellName: "Haste",
        effectIds: ["eff-2"],
      },
    );
    expect(result).not.toBeNull();
    expect(result?.previousLabel).toBe("Bless");
    expect(result?.nextLabel).toBe("Haste");
  });

  it("returns notice when previous has no label (only effectIds)", () => {
    const result = getConcentrationReplacementNotice(
      {
        effectIds: ["eff-1"],
        concentrationGroup: "grp-a",
      },
      {
        spellName: "Haste",
        effectIds: ["eff-2"],
        concentrationGroup: "grp-b",
      },
    );
    expect(result).not.toBeNull();
    expect(result?.previousLabel).toBeNull();
    expect(result?.nextLabel).toBe("Haste");
  });

  it("returns notice when next has no label (only effectIds)", () => {
    const result = getConcentrationReplacementNotice(
      {
        spellName: "Bless",
        effectIds: ["eff-1"],
        concentrationGroup: "grp-a",
      },
      {
        effectIds: ["eff-2"],
        concentrationGroup: "grp-b",
      },
    );
    expect(result).not.toBeNull();
    expect(result?.previousLabel).toBe("Bless");
    expect(result?.nextLabel).toBeNull();
  });
});
