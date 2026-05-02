import { describe, expect, it } from "vitest";

import { fromLocalTables } from "./spellProgressionBackendAdapter";
import { resolveProgressionState } from "./useClassSpellProgression";

const WIZARD_L5_LOCAL = {
  className: "wizard",
  level: 5,
  slots: { 1: 4, 2: 3, 3: 2 },
  maxSpellLevel: 3,
  cantrips: 4,
  leveledSpellsKnown: null,
  spellcastingType: "spellbook" as const,
};

describe("fromLocalTables", () => {
  it("returns correct progression for wizard level 5", () => {
    expect(fromLocalTables("wizard", 5)).toEqual(WIZARD_L5_LOCAL);
  });

  it("returns null for non-caster class", () => {
    expect(fromLocalTables("fighter", 5)).toBeNull();
  });

  it("clamps level to 1–20 range", () => {
    const result = fromLocalTables("wizard", 0);
    expect(result).not.toBeNull();
    expect(result!.level).toBe(1);
  });

  it("returns spells-known for known caster classes", () => {
    const result = fromLocalTables("bard", 1);
    expect(result).not.toBeNull();
    expect(result!.leveledSpellsKnown).toBe(4);
    expect(result!.spellcastingType).toBe("known");
  });
});

describe("resolveProgressionState", () => {
  it("returns local data when backend flag is off", () => {
    const result = resolveProgressionState(WIZARD_L5_LOCAL, null, null, false, false);

    expect(result.progression).toBe(WIZARD_L5_LOCAL);
    expect(result.source).toBe("local");
    expect(result.isLoading).toBe(false);
    expect(result.error).toBeNull();
  });

  it("returns loading state with local fallback when backend flag is on and loading", () => {
    const result = resolveProgressionState(WIZARD_L5_LOCAL, null, null, true, true);

    expect(result.progression).toBe(WIZARD_L5_LOCAL);
    expect(result.source).toBe("local");
    expect(result.isLoading).toBe(true);
    expect(result.error).toBeNull();
  });

  it("returns backend data when backend flag is on and fetch succeeded", () => {
    const backendData = { ...WIZARD_L5_LOCAL, maxSpellLevel: 3 };
    const result = resolveProgressionState(WIZARD_L5_LOCAL, backendData, null, true, false);

    expect(result.progression).toBe(backendData);
    expect(result.source).toBe("backend");
    expect(result.isLoading).toBe(false);
    expect(result.error).toBeNull();
  });

  it("returns local data when backend flag is on and fetch returned null", () => {
    const result = resolveProgressionState(WIZARD_L5_LOCAL, null, null, true, false);

    expect(result.progression).toBe(WIZARD_L5_LOCAL);
    expect(result.source).toBe("local");
    expect(result.isLoading).toBe(false);
    expect(result.error).toBeNull();
  });

  it("returns local data with error when backend flag is on and fetch threw", () => {
    const err = new Error("network failure");
    const result = resolveProgressionState(WIZARD_L5_LOCAL, null, err, true, false);

    expect(result.progression).toBe(WIZARD_L5_LOCAL);
    expect(result.source).toBe("local");
    expect(result.isLoading).toBe(false);
    expect(result.error).toBe(err);
  });
});
