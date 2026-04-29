import { describe, expect, it } from "vitest";
import { buildPlayerBoardWeaponSummary } from "./playerBoardWeaponSummary";
import { INITIAL_SHEET } from "../../features/character-sheet/model/initialSheet";
import type { CharacterSheet } from "../../features/character-sheet/model/characterSheet.types";

const baseSheet: CharacterSheet = {
  ...INITIAL_SHEET,
  level: 1,
  abilities: {
    ...INITIAL_SHEET.abilities,
    strength: 10,
    dexterity: 10,
    constitution: 10,
    intelligence: 10,
    wisdom: 10,
    charisma: 10,
  },
  currentWeaponId: null,
};

describe("buildPlayerBoardWeaponSummary — unarmed strike (no weapon equipped)", () => {
  it("returns null when playerSheet is null", () => {
    expect(
      buildPlayerBoardWeaponSummary({
        inventory: [],
        itemsById: {},
        locale: "pt",
        unarmedStrikeName: "Ataque desarmado",
        playerSheet: null,
      }),
    ).toBeNull();
  });

  it("uses the provided unarmedStrikeName as name", () => {
    const result = buildPlayerBoardWeaponSummary({
      inventory: [],
      itemsById: {},
      locale: "pt",
      unarmedStrikeName: "Ataque desarmado",
      playerSheet: baseSheet,
    });
    expect(result!.name).toBe("Ataque desarmado");
  });

  it("STR 16 (mod +3), level 5 (prof +3) → attackBonus 6, rangeMeters 1.5, proficient, melee", () => {
    const sheet: CharacterSheet = {
      ...baseSheet,
      abilities: { ...baseSheet.abilities, strength: 16 },
      level: 5,
    };
    const result = buildPlayerBoardWeaponSummary({
      inventory: [],
      itemsById: {},
      locale: "pt",
      unarmedStrikeName: "Ataque desarmado",
      playerSheet: sheet,
    });
    expect(result).not.toBeNull();
    expect(result!.attackBonus).toBe(6);
    expect(result!.rangeMeters).toBe(1.5);
    expect(result!.rangeLongMeters).toBeNull();
    expect(result!.proficient).toBe(true);
    expect(result!.isRanged).toBe(false);
    expect(result!.name).toBe("Ataque desarmado");
  });

  it("STR 16 (mod +3), level 5 — damageLabel contains '1 + 3' and localized damage type", () => {
    const sheet: CharacterSheet = {
      ...baseSheet,
      abilities: { ...baseSheet.abilities, strength: 16 },
      level: 5,
    };
    const result = buildPlayerBoardWeaponSummary({
      inventory: [],
      itemsById: {},
      locale: "pt",
      unarmedStrikeName: "Ataque desarmado",
      playerSheet: sheet,
    });
    expect(result!.damageLabel).toContain("1 + 3");
    expect(result!.damageLabel).toMatch(/contundente/i);
  });

  it("STR 8 (mod −1), level 1 (prof +2) → attackBonus 1, damageLabel contains '1 - 1'", () => {
    const sheet: CharacterSheet = {
      ...baseSheet,
      abilities: { ...baseSheet.abilities, strength: 8 },
      level: 1,
    };
    const result = buildPlayerBoardWeaponSummary({
      inventory: [],
      itemsById: {},
      locale: "pt",
      unarmedStrikeName: "Ataque desarmado",
      playerSheet: sheet,
    });
    expect(result!.attackBonus).toBe(1);
    expect(result!.damageLabel).toContain("1 - 1");
  });

  it("STR 10 (mod 0), level 1 — damageLabel has no sign", () => {
    const result = buildPlayerBoardWeaponSummary({
      inventory: [],
      itemsById: {},
      locale: "pt",
      unarmedStrikeName: "Ataque desarmado",
      playerSheet: baseSheet,
    });
    expect(result!.damageLabel).not.toContain("+");
    expect(result!.damageLabel).not.toContain("-");
    expect(result!.damageLabel).toMatch(/^1 /);
  });

  it("locale en-US returns English name", () => {
    const result = buildPlayerBoardWeaponSummary({
      inventory: [],
      itemsById: {},
      locale: "en",
      unarmedStrikeName: "Unarmed Strike",
      playerSheet: baseSheet,
    });
    expect(result!.name).toBe("Unarmed Strike");
    expect(result!.damageLabel).toContain("Bludgeoning");
  });
});

describe("buildPlayerBoardWeaponSummary — weapon equipped (regression)", () => {
  it("returns null when weapon id set but inventory is empty", () => {
    const sheet: CharacterSheet = { ...baseSheet, currentWeaponId: "inv-123" };
    const result = buildPlayerBoardWeaponSummary({
      inventory: [],
      itemsById: {},
      locale: "pt",
      unarmedStrikeName: "Ataque desarmado",
      playerSheet: sheet,
    });
    expect(result).toBeNull();
  });
});
