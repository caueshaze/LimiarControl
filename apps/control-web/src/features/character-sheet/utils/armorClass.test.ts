import { describe, expect, it } from "vitest";

import { INITIAL_SHEET } from "../model/initialSheet";
import {
  buildCharacterAcStateFromSheet,
  calculateArmorClass,
  getValidAcBases,
  type CharacterAcState,
  type AcArmor,
} from "./armorClass";

const armor = (
  name: string,
  category: AcArmor["category"],
  baseAc: number,
  dexCap: number | null,
): AcArmor => ({
  name,
  category,
  baseAc,
  allowsDex: category !== "heavy",
  dexCap,
});

const createState = (
  overrides: Partial<CharacterAcState> = {},
): CharacterAcState => ({
  dexMod: 0,
  conMod: 0,
  wisMod: 0,
  armorEquipped: null,
  shieldEquipped: false,
  hasBarbarianUnarmoredDefense: false,
  hasMonkUnarmoredDefense: false,
  hasMageArmor: false,
  activeAcEffects: [],
  ...overrides,
});

describe("armorClass", () => {
  it("calculates default unarmored AC", () => {
    const result = calculateArmorClass(
      createState({
        dexMod: 2,
      }),
    );

    expect(result.base.source).toBe("default");
    expect(result.base.value).toBe(12);
    expect(result.total).toBe(12);
  });

  it("calculates light armor AC", () => {
    const result = calculateArmorClass(
      createState({
        armorEquipped: armor("Leather", "light", 11, null),
        dexMod: 3,
      }),
    );

    expect(result.base.source).toBe("light_armor");
    expect(result.base.value).toBe(14);
    expect(result.total).toBe(14);
  });

  it("calculates medium armor with shield", () => {
    const result = calculateArmorClass(
      createState({
        armorEquipped: armor("Half Plate", "medium", 15, 2),
        dexMod: 4,
        shieldEquipped: true,
      }),
    );

    expect(result.base.source).toBe("medium_armor");
    expect(result.base.value).toBe(17);
    expect(result.bonuses.shield).toBe(2);
    expect(result.total).toBe(19);
  });

  it("calculates barbarian unarmored defense with shield", () => {
    const result = calculateArmorClass(
      createState({
        dexMod: 2,
        conMod: 3,
        shieldEquipped: true,
        hasBarbarianUnarmoredDefense: true,
      }),
    );

    expect(result.base.source).toBe("barbarian_unarmored_defense");
    expect(result.base.value).toBe(15);
    expect(result.total).toBe(17);
  });

  it("calculates monk unarmored defense without shield", () => {
    const result = calculateArmorClass(
      createState({
        dexMod: 3,
        wisMod: 4,
        hasMonkUnarmoredDefense: true,
      }),
    );

    expect(result.base.source).toBe("monk_unarmored_defense");
    expect(result.total).toBe(17);
  });

  it("invalidates monk unarmored defense when using a shield", () => {
    const result = calculateArmorClass(
      createState({
        dexMod: 3,
        wisMod: 4,
        shieldEquipped: true,
        hasMonkUnarmoredDefense: true,
      }),
    );

    expect(result.candidateBases.map((base) => base.source)).toEqual(["default"]);
    expect(result.base.source).toBe("default");
    expect(result.total).toBe(15);
  });

  it("chooses the highest valid base AC", () => {
    const result = calculateArmorClass(
      createState({
        dexMod: 3,
        conMod: 2,
        hasBarbarianUnarmoredDefense: true,
        hasMageArmor: true,
      }),
    );

    expect(getValidAcBases(createState({
      dexMod: 3,
      conMod: 2,
      hasBarbarianUnarmoredDefense: true,
      hasMageArmor: true,
    })).map((base) => ({ source: base.source, value: base.value }))).toEqual([
      { source: "mage_armor", value: 16 },
      { source: "barbarian_unarmored_defense", value: 15 },
      { source: "default", value: 13 },
    ]);
    expect(result.base.source).toBe("mage_armor");
    expect(result.total).toBe(16);
  });

  it("derives AC from the current sheet using class features and additive bonuses", () => {
    const result = calculateArmorClass(
      buildCharacterAcStateFromSheet({
        ...INITIAL_SHEET,
        class: "fighter",
        fightingStyle: "defense",
        miscACBonus: 1,
        abilities: {
          ...INITIAL_SHEET.abilities,
          dexterity: 14,
        },
        equippedArmor: {
          name: "Chain Mail",
          armorType: "heavy",
          baseAC: 16,
          dexCap: 0,
          allowsDex: false,
          minStrength: 13,
          stealthDisadvantage: true,
        },
        equippedShield: { name: "Shield", bonus: 2 },
      }),
    );

    expect(result.base.source).toBe("heavy_armor");
    expect(result.bonuses.totalBonus).toBe(4);
    expect(result.total).toBe(20);
  });
});
