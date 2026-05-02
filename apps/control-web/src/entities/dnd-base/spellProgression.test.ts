import { describe, expect, it } from "vitest";
import {
  getCantripCountForClassLevel,
  getMaxUnlockedSpellLevel,
  getSlotProgressionForLevel,
} from "./spellProgression";

/**
 * Contract/sanity tests: frontend spell progression tables (spellProgression.ts).
 *
 * These are NOT a shared source of truth — TS and Python are separate implementations.
 * They ensure behavioral equivalence, not code reuse. Do not attempt to unify them.
 *
 * Each scenario here must have an equivalent test on the backend side in:
 *   apps/control-server/tests/test_class_progression.py  (SpellcastingProgressionContractTests)
 *
 * If you change a slot table here and these tests still pass but the backend
 * tests fail (or vice versa), that is a FE/BE drift signal.
 */

describe("getSlotProgressionForLevel — contract scenarios", () => {
  it("sorcerer level 3: full caster, unlocks 2nd level slots", () => {
    expect(getSlotProgressionForLevel("sorcerer", 3)).toEqual({ 1: 4, 2: 2 });
  });

  it("wizard level 5: full caster, unlocks 3rd level slots", () => {
    expect(getSlotProgressionForLevel("wizard", 5)).toEqual({ 1: 4, 2: 3, 3: 2 });
  });

  it("cleric level 7: full caster, unlocks 4th level slots", () => {
    expect(getSlotProgressionForLevel("cleric", 7)).toEqual({ 1: 4, 2: 3, 3: 3, 4: 1 });
  });

  it("paladin level 5: half caster, unlocks 2nd level slots", () => {
    expect(getSlotProgressionForLevel("paladin", 5)).toEqual({ 1: 4, 2: 2 });
  });

  it("warlock level 3: pact magic upgrades to 2nd level slot", () => {
    expect(getSlotProgressionForLevel("warlock", 3)).toEqual({ 2: 2 });
  });

  it("ranger level 5: half caster, unlocks 2nd level slots", () => {
    expect(getSlotProgressionForLevel("ranger", 5)).toEqual({ 1: 4, 2: 2 });
  });

  it("guardian level 5: inherits ranger half-caster progression", () => {
    expect(getSlotProgressionForLevel("guardian", 5)).toEqual(
      getSlotProgressionForLevel("ranger", 5)
    );
  });
});

describe("getMaxUnlockedSpellLevel — contract scenarios", () => {
  it("sorcerer level 3: max spell level 2", () => {
    expect(getMaxUnlockedSpellLevel("sorcerer", 3)).toBe(2);
  });

  it("wizard level 5: max spell level 3", () => {
    expect(getMaxUnlockedSpellLevel("wizard", 5)).toBe(3);
  });

  it("cleric level 7: max spell level 4", () => {
    expect(getMaxUnlockedSpellLevel("cleric", 7)).toBe(4);
  });

  it("paladin level 5: max spell level 2", () => {
    expect(getMaxUnlockedSpellLevel("paladin", 5)).toBe(2);
  });

  it("warlock level 3: max spell level 2", () => {
    expect(getMaxUnlockedSpellLevel("warlock", 3)).toBe(2);
  });

  it("ranger level 5: max spell level 2", () => {
    expect(getMaxUnlockedSpellLevel("ranger", 5)).toBe(2);
  });

  it("guardian level 5: max spell level matches ranger level 5", () => {
    expect(getMaxUnlockedSpellLevel("guardian", 5)).toBe(
      getMaxUnlockedSpellLevel("ranger", 5)
    );
  });

  it("paladin level 1: no slots yet, max spell level 0", () => {
    expect(getMaxUnlockedSpellLevel("paladin", 1)).toBe(0);
  });
});

describe("getCantripCountForClassLevel", () => {
  it("sorcerer level 1: 4 cantrips", () => {
    expect(getCantripCountForClassLevel("sorcerer", 1)).toBe(4);
  });

  it("wizard level 1: 3 cantrips", () => {
    expect(getCantripCountForClassLevel("wizard", 1)).toBe(3);
  });

  it("cleric level 1: 3 cantrips", () => {
    expect(getCantripCountForClassLevel("cleric", 1)).toBe(3);
  });

  it("ranger level 1: no cantrips (undefined)", () => {
    expect(getCantripCountForClassLevel("ranger", 1)).toBeUndefined();
  });
});
