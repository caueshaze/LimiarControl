import { describe, expect, it } from "vitest";
import {
  getConditionIndicators,
  type ConditionIndicator
} from "./condition-indicators";

// ─── All 14 known conditions ──────────────────────────────────────────────────

const ALL_14 = [
  "blinded",
  "charmed",
  "deafened",
  "exhausted",
  "frightened",
  "grappled",
  "incapacitated",
  "invisible",
  "paralyzed",
  "petrified",
  "poisoned",
  "prone",
  "restrained",
  "stunned"
] as const;

// ─── Empty input ──────────────────────────────────────────────────────────────

describe("getConditionIndicators — empty", () => {
  it("returns [] for empty array", () => {
    expect(getConditionIndicators([])).toEqual([]);
  });
});

// ─── Label accuracy for all 14 conditions ────────────────────────────────────

describe("getConditionIndicators — known condition labels", () => {
  const EXPECTED_LABELS: Record<string, string> = {
    blinded: "Cego",
    charmed: "Encantado",
    deafened: "Ensurdecido",
    exhausted: "Exausto",
    frightened: "Apavorado",
    grappled: "Agarrado",
    incapacitated: "Incapacitado",
    invisible: "Invisível",
    paralyzed: "Paralisado",
    petrified: "Petrificado",
    poisoned: "Envenenado",
    prone: "Caído",
    restrained: "Imobilizado",
    stunned: "Atordoado"
  };

  for (const code of ALL_14) {
    it(`${code} → correct PT-BR label`, () => {
      const [ind] = getConditionIndicators([code]);
      expect(ind.label).toBe(EXPECTED_LABELS[code]);
    });
  }
});

// ─── Short labels ─────────────────────────────────────────────────────────────

describe("getConditionIndicators — short labels", () => {
  const EXPECTED_SHORT: Record<string, string> = {
    blinded: "CG",
    charmed: "EC",
    deafened: "SD",
    exhausted: "EX",
    frightened: "AP",
    grappled: "AG",
    incapacitated: "IC",
    invisible: "IV",
    paralyzed: "PL",
    petrified: "PT",
    poisoned: "EN",
    prone: "CD",
    restrained: "IM",
    stunned: "AT"
  };

  for (const code of ALL_14) {
    it(`${code} → short label ≤ 2 chars`, () => {
      const [ind] = getConditionIndicators([code]);
      expect(ind.shortLabel.length).toBeLessThanOrEqual(2);
      expect(ind.shortLabel).toBe(EXPECTED_SHORT[code]);
    });
  }
});

// ─── Color tokens are valid CSS hex strings ───────────────────────────────────

describe("getConditionIndicators — colorToken format", () => {
  for (const code of ALL_14) {
    it(`${code} → colorToken is valid CSS hex`, () => {
      const [ind] = getConditionIndicators([code]);
      expect(ind.colorToken).toMatch(/^#[0-9a-f]{6}$/i);
    });
  }
});

// ─── isNegative flag ──────────────────────────────────────────────────────────

describe("getConditionIndicators — isNegative", () => {
  it("invisible is NOT negative (can be beneficial)", () => {
    const [ind] = getConditionIndicators(["invisible"]);
    expect(ind.isNegative).toBe(false);
  });

  it("all other known conditions are negative", () => {
    const others = ALL_14.filter((c) => c !== "invisible");
    for (const code of others) {
      const [ind] = getConditionIndicators([code]);
      expect(ind.isNegative, `${code} should be negative`).toBe(true);
    }
  });
});

// ─── Priority ordering ────────────────────────────────────────────────────────

describe("getConditionIndicators — priority ordering", () => {
  it("returns conditions sorted ascending by priority", () => {
    const indicators = getConditionIndicators([...ALL_14]);
    for (let i = 0; i < indicators.length - 1; i++) {
      expect(indicators[i].priority).toBeLessThanOrEqual(indicators[i + 1].priority);
    }
  });

  it("incapacitated has lowest priority number (highest severity)", () => {
    const indicators = getConditionIndicators([...ALL_14]);
    expect(indicators[0].conditionType).toBe("incapacitated");
  });

  it("prone has highest priority number among the 14 (lowest severity)", () => {
    const indicators = getConditionIndicators([...ALL_14]);
    expect(indicators[indicators.length - 1].conditionType).toBe("prone");
  });

  it("incapacitated appears before paralyzed", () => {
    const indicators = getConditionIndicators(["paralyzed", "incapacitated"]);
    const types = indicators.map((i) => i.conditionType);
    expect(types.indexOf("incapacitated")).toBeLessThan(types.indexOf("paralyzed"));
  });

  it("paralyzed appears before stunned", () => {
    const indicators = getConditionIndicators(["stunned", "paralyzed"]);
    const types = indicators.map((i) => i.conditionType);
    expect(types.indexOf("paralyzed")).toBeLessThan(types.indexOf("stunned"));
  });

  it("stunned appears before blinded", () => {
    const indicators = getConditionIndicators(["blinded", "stunned"]);
    const types = indicators.map((i) => i.conditionType);
    expect(types.indexOf("stunned")).toBeLessThan(types.indexOf("blinded"));
  });

  it("invisible appears before charmed", () => {
    const indicators = getConditionIndicators(["charmed", "invisible"]);
    const types = indicators.map((i) => i.conditionType);
    expect(types.indexOf("invisible")).toBeLessThan(types.indexOf("charmed"));
  });

  it("most-severe subset of 3 are: incapacitated, paralyzed, stunned", () => {
    const indicators = getConditionIndicators([...ALL_14]);
    expect(indicators.slice(0, 3).map((i) => i.conditionType)).toEqual([
      "incapacitated",
      "paralyzed",
      "stunned"
    ]);
  });
});

// ─── Unknown condition degradation ───────────────────────────────────────────

describe("getConditionIndicators — unknown condition codes", () => {
  it("returns an indicator for an unknown code", () => {
    const [ind] = getConditionIndicators(["cursed"]);
    expect(ind).toBeDefined();
    expect(ind.conditionType).toBe("cursed");
  });

  it("unknown code short label is first 2 chars uppercased", () => {
    const [ind] = getConditionIndicators(["cursed"]);
    expect(ind.shortLabel).toBe("CU");
  });

  it("unknown code label falls back to the raw code", () => {
    const [ind] = getConditionIndicators(["cursed"]);
    expect(ind.label).toBe("cursed");
  });

  it("unknown code sorts AFTER all 14 known conditions", () => {
    const indicators = getConditionIndicators([...ALL_14, "cursed"]);
    expect(indicators[indicators.length - 1].conditionType).toBe("cursed");
  });

  it("unknown codes get a fallback gray colorToken", () => {
    const [ind] = getConditionIndicators(["totally_made_up"]);
    expect(ind.colorToken).toMatch(/^#[0-9a-f]{6}$/i);
  });

  it("multiple unknown codes all sort after known ones", () => {
    const indicators = getConditionIndicators(["incapacitated", "zzz_unknown", "aaa_unknown"]);
    const types = indicators.map((i) => i.conditionType);
    expect(types[0]).toBe("incapacitated");
    // Both unknowns are in the tail
    expect(types.slice(1)).toEqual(expect.arrayContaining(["zzz_unknown", "aaa_unknown"]));
  });
});

// ─── Overlay chip truncation helpers ─────────────────────────────────────────
// These tests simulate how drawTokenLayer consumes the indicators: takes first 3,
// rest become overflow. They are logic tests only — no canvas rendering involved.

describe("token chip overlay truncation (simulated)", () => {
  const MAX_VISIBLE = 3;

  function simulate(conditions: string[]): { visible: ConditionIndicator[]; overflow: number } {
    const all = getConditionIndicators(conditions);
    return { visible: all.slice(0, MAX_VISIBLE), overflow: all.length - Math.min(all.length, MAX_VISIBLE) };
  }

  it("1 condition → 1 visible, 0 overflow", () => {
    const { visible, overflow } = simulate(["blinded"]);
    expect(visible).toHaveLength(1);
    expect(overflow).toBe(0);
  });

  it("3 conditions → 3 visible, 0 overflow", () => {
    const { visible, overflow } = simulate(["blinded", "prone", "stunned"]);
    expect(visible).toHaveLength(3);
    expect(overflow).toBe(0);
  });

  it("4 conditions → 3 visible, 1 overflow", () => {
    const { visible, overflow } = simulate(["blinded", "prone", "stunned", "charmed"]);
    expect(visible).toHaveLength(3);
    expect(overflow).toBe(1);
  });

  it("all 14 → 3 visible, 11 overflow", () => {
    const { visible, overflow } = simulate([...ALL_14]);
    expect(visible).toHaveLength(3);
    expect(overflow).toBe(11);
  });

  it("visible chips are the highest-severity 3", () => {
    const { visible } = simulate([...ALL_14]);
    expect(visible.map((i) => i.conditionType)).toEqual([
      "incapacitated",
      "paralyzed",
      "stunned"
    ]);
  });

  it("no overflow badge when exactly MAX_VISIBLE conditions", () => {
    const { overflow } = simulate(["incapacitated", "paralyzed", "stunned"]);
    expect(overflow).toBe(0);
  });
});
