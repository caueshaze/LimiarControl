import { describe, expect, it } from "vitest";

import {
  getDragonbornBreathWeaponDC,
  getDragonbornBreathWeaponDamageDice,
  getDragonbornBreathWeaponSaveType,
  getDragonbornBreathWeaponShape,
  getDragonbornDamageType,
  getDragonbornResistanceType,
  normalizeDragonbornRaceConfig,
  resolveDragonbornLineageState,
} from "./dragonbornAncestries";

describe("dragonbornAncestries", () => {
  const EXPECTED_LINEAGES = {
    black: { damageType: "acid", resistanceType: "acid", breathWeaponShape: "line", breathWeaponSaveType: "dexterity" },
    blue: { damageType: "lightning", resistanceType: "lightning", breathWeaponShape: "line", breathWeaponSaveType: "dexterity" },
    brass: { damageType: "fire", resistanceType: "fire", breathWeaponShape: "line", breathWeaponSaveType: "dexterity" },
    bronze: { damageType: "lightning", resistanceType: "lightning", breathWeaponShape: "line", breathWeaponSaveType: "dexterity" },
    copper: { damageType: "acid", resistanceType: "acid", breathWeaponShape: "line", breathWeaponSaveType: "dexterity" },
    gold: { damageType: "fire", resistanceType: "fire", breathWeaponShape: "cone", breathWeaponSaveType: "constitution" },
    green: { damageType: "poison", resistanceType: "poison", breathWeaponShape: "cone", breathWeaponSaveType: "constitution" },
    red: { damageType: "fire", resistanceType: "fire", breathWeaponShape: "cone", breathWeaponSaveType: "constitution" },
    silver: { damageType: "cold", resistanceType: "cold", breathWeaponShape: "cone", breathWeaponSaveType: "constitution" },
    white: { damageType: "cold", resistanceType: "cold", breathWeaponShape: "cone", breathWeaponSaveType: "constitution" },
  } as const;

  it("normalizes legacy dragonborn ancestry keys into draconicAncestry", () => {
    expect(normalizeDragonbornRaceConfig({ dragonbornAncestry: "red" })).toEqual({
      draconicAncestry: "red",
    });
    expect(normalizeDragonbornRaceConfig({ dragonAncestor: "blue" })).toEqual({
      draconicAncestry: "blue",
    });
  });

  it("keeps the canonical draconicAncestry key unchanged", () => {
    expect(normalizeDragonbornRaceConfig({ draconicAncestry: "silver" })).toEqual({
      draconicAncestry: "silver",
    });
  });

  it("derives dragonborn lineage mechanics for every ancestry", () => {
    Object.entries(EXPECTED_LINEAGES).forEach(([ancestry, expected]) => {
      expect(getDragonbornDamageType(ancestry)).toBe(expected.damageType);
      expect(getDragonbornResistanceType(ancestry)).toBe(expected.resistanceType);
      expect(getDragonbornBreathWeaponShape(ancestry)).toBe(expected.breathWeaponShape);
      expect(getDragonbornBreathWeaponSaveType(ancestry)).toBe(expected.breathWeaponSaveType);
    });
  });

  it("scales dragonborn breath weapon damage by level bracket", () => {
    expect(getDragonbornBreathWeaponDamageDice(1)).toBe("2d6");
    expect(getDragonbornBreathWeaponDamageDice(5)).toBe("3d6");
    expect(getDragonbornBreathWeaponDamageDice(11)).toBe("4d6");
    expect(getDragonbornBreathWeaponDamageDice(17)).toBe("5d6");
  });

  it("computes dragonborn breath weapon DC from proficiency and constitution", () => {
    expect(
      getDragonbornBreathWeaponDC({
        level: 5,
        abilities: { constitution: 16 },
      }),
    ).toBe(14);
  });

  it("exposes the derived dragonborn lineage state", () => {
    expect(
      resolveDragonbornLineageState({
        raceId: "dragonborn",
        raceConfig: { draconicAncestry: "red" },
      }),
    ).toMatchObject({
      ancestry: "red",
      ancestryLabel: "Vermelho",
      damageType: "fire",
      resistanceType: "fire",
      breathWeaponShape: "cone",
      breathWeaponSaveType: "constitution",
      resistances: ["fire"],
    });
  });
});
