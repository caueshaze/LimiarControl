import { describe, expect, it } from "vitest";
import { computeAbilityScoreTotal } from "./calculations";
import {
  computeBaseAbilitiesForPointAccounting,
  computeBaseAbilityScoreTotal,
} from "./abilityScoreAccounting";
import { ABILITY_SCORE_POOL } from "../constants";
import type { AbilityName } from "../model/characterSheet.types";

// Standard Array: 15+14+13+12+10+8 = 72
const BASE_ABILITIES: Record<AbilityName, number> = {
  strength: 15,
  dexterity: 14,
  constitution: 13,
  intelligence: 12,
  wisdom: 10,
  charisma: 8,
};

describe("computeBaseAbilitiesForPointAccounting", () => {
  it("returns abilities unchanged when no race or class bonuses", () => {
    const result = computeBaseAbilitiesForPointAccounting(
      BASE_ABILITIES,
      null,
      null,
      "",
      1,
    );
    expect(result).toEqual(BASE_ABILITIES);
  });

  it("handles raceConfig = undefined without throwing", () => {
    const result = computeBaseAbilitiesForPointAccounting(
      BASE_ABILITIES,
      null,
      undefined,
      "",
      1,
    );
    expect(result).toEqual(BASE_ABILITIES);
  });

  it("strips race bonuses per attribute — hill-dwarf: constitution −2, wisdom −1, others unchanged", () => {
    const abilitiesWithRace: Record<AbilityName, number> = {
      ...BASE_ABILITIES,
      constitution: BASE_ABILITIES.constitution + 2,
      wisdom: BASE_ABILITIES.wisdom + 1,
    };
    const result = computeBaseAbilitiesForPointAccounting(
      abilitiesWithRace,
      "hill-dwarf",
      null,
      "",
      1,
    );
    expect(result.strength).toBe(BASE_ABILITIES.strength);
    expect(result.dexterity).toBe(BASE_ABILITIES.dexterity);
    expect(result.constitution).toBe(BASE_ABILITIES.constitution);
    expect(result.intelligence).toBe(BASE_ABILITIES.intelligence);
    expect(result.wisdom).toBe(BASE_ABILITIES.wisdom);
    expect(result.charisma).toBe(BASE_ABILITIES.charisma);
  });

  it("strips Guardian level-4 class bonus per attribute — dexterity −2, others unchanged", () => {
    const abilitiesWithClass: Record<AbilityName, number> = {
      ...BASE_ABILITIES,
      dexterity: BASE_ABILITIES.dexterity + 2,
    };
    const result = computeBaseAbilitiesForPointAccounting(
      abilitiesWithClass,
      null,
      null,
      "Guardian",
      4,
    );
    expect(result.dexterity).toBe(BASE_ABILITIES.dexterity);
    expect(result.strength).toBe(BASE_ABILITIES.strength);
    expect(result.constitution).toBe(BASE_ABILITIES.constitution);
  });

  it("Guardian below level 4 — class bonus not yet active, dexterity unchanged", () => {
    const abilitiesAtLevel3: Record<AbilityName, number> = { ...BASE_ABILITIES };
    const result = computeBaseAbilitiesForPointAccounting(
      abilitiesAtLevel3,
      null,
      null,
      "Guardian",
      3,
    );
    expect(result.dexterity).toBe(BASE_ABILITIES.dexterity);
  });

  it("strips both race and class bonuses together — each attribute correct", () => {
    const abilitiesWithBoth: Record<AbilityName, number> = {
      ...BASE_ABILITIES,
      dexterity: BASE_ABILITIES.dexterity + 2,
      constitution: BASE_ABILITIES.constitution + 2,
      wisdom: BASE_ABILITIES.wisdom + 1,
    };
    const result = computeBaseAbilitiesForPointAccounting(
      abilitiesWithBoth,
      "hill-dwarf",
      null,
      "Guardian",
      4,
    );
    expect(result).toEqual(BASE_ABILITIES);
  });
});

describe("computeBaseAbilityScoreTotal", () => {
  it("valid character — base sums 72, race +3 → usedPoints 72, remaining 0", () => {
    const abilitiesWithRace: Record<AbilityName, number> = {
      ...BASE_ABILITIES,
      constitution: BASE_ABILITIES.constitution + 2,
      wisdom: BASE_ABILITIES.wisdom + 1,
    };
    const usedPoints = computeBaseAbilityScoreTotal(
      abilitiesWithRace,
      "hill-dwarf",
      null,
      "",
      1,
    );
    expect(usedPoints).toBe(ABILITY_SCORE_POOL);
    expect(ABILITY_SCORE_POOL - usedPoints).toBe(0);
  });

  it("valid character — base sums 70, race +3 → usedPoints 70, remaining 2", () => {
    const lowBase: Record<AbilityName, number> = {
      ...BASE_ABILITIES,
      charisma: 6, // 8 → 6: total drops by 2 → 70
    };
    const abilitiesWithRace: Record<AbilityName, number> = {
      ...lowBase,
      constitution: lowBase.constitution + 2,
      wisdom: lowBase.wisdom + 1,
    };
    const usedPoints = computeBaseAbilityScoreTotal(
      abilitiesWithRace,
      "hill-dwarf",
      null,
      "",
      1,
    );
    expect(usedPoints).toBe(70);
    expect(ABILITY_SCORE_POOL - usedPoints).toBe(2);
  });

  it("valid character — Guardian lv4 +2 DEX does not inflate used points", () => {
    const abilitiesWithClass: Record<AbilityName, number> = {
      ...BASE_ABILITIES,
      dexterity: BASE_ABILITIES.dexterity + 2,
    };
    const usedPoints = computeBaseAbilityScoreTotal(
      abilitiesWithClass,
      null,
      null,
      "Guardian",
      4,
    );
    expect(usedPoints).toBe(ABILITY_SCORE_POOL);
  });

  it("invalid character — base exceeds 72 → remaining is negative", () => {
    const overLimit: Record<AbilityName, number> = {
      ...BASE_ABILITIES,
      charisma: 12, // 8 → 12: total goes from 72 to 76
    };
    const usedPoints = computeBaseAbilityScoreTotal(
      overLimit,
      null,
      null,
      "",
      1,
    );
    expect(usedPoints).toBeGreaterThan(ABILITY_SCORE_POOL);
    expect(ABILITY_SCORE_POOL - usedPoints).toBeLessThan(0);
  });

  it("no race or class — same result as computeAbilityScoreTotal", () => {
    const usedPoints = computeBaseAbilityScoreTotal(
      BASE_ABILITIES,
      null,
      null,
      "",
      1,
    );
    expect(usedPoints).toBe(computeAbilityScoreTotal(BASE_ABILITIES));
  });
});
