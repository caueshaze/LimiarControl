import { describe, expect, it } from "vitest";
import type { UpcastMode } from "../../../entities/base-spell";
import {
  computeUpcastPreviewRows,
  computeUpcastValidationWarnings,
  type UpcastPreviewParams,
  type UpcastValidationParams,
} from "./upcastPreview";

describe("computeUpcastPreviewRows", () => {
  it("returns empty rows when no mode is selected", () => {
    const rows = computeUpcastPreviewRows({
      spellLevel: 3,
      upcastMode: "",
      upcastDice: null,
      upcastFlat: null,
      perLevel: 1,
      maxLevel: null,
      baseEffectInstances: null,
      baseDice: "8d6",
      baseMaxTargets: null,
    });
    expect(rows).toEqual([]);
  });

  it("returns empty rows for cantrips (level 0)", () => {
    const rows = computeUpcastPreviewRows({
      spellLevel: 0,
      upcastMode: "extra_damage_dice",
      upcastDice: "1d6",
      upcastFlat: null,
      perLevel: 1,
      maxLevel: null,
      baseEffectInstances: null,
      baseDice: "1d8",
      baseMaxTargets: null,
    });
    expect(rows).toEqual([]);
  });

  it("computes Fireball-style damage dice preview", () => {
    const rows = computeUpcastPreviewRows({
      spellLevel: 3,
      upcastMode: "extra_damage_dice" as UpcastMode,
      upcastDice: "1d6",
      upcastFlat: null,
      perLevel: 1,
      maxLevel: null,
      baseEffectInstances: null,
      baseDice: "8d6",
      baseMaxTargets: null,
    });

    expect(rows).toHaveLength(4);
    expect(rows[0]).toEqual({
      slotLevel: 3,
      isBase: true,
      label: "3rd (base)",
      value: "8d6",
    });
    expect(rows[1]).toEqual({
      slotLevel: 4,
      isBase: false,
      label: "4th",
      value: "9d6",
    });
    expect(rows[2]).toEqual({
      slotLevel: 5,
      isBase: false,
      label: "5th",
      value: "10d6",
    });
    expect(rows[3]).toEqual({
      slotLevel: 6,
      isBase: false,
      label: "6th",
      value: "11d6",
    });
  });

  it("computes Cure Wounds-style heal dice preview", () => {
    const rows = computeUpcastPreviewRows({
      spellLevel: 1,
      upcastMode: "extra_heal_dice" as UpcastMode,
      upcastDice: "1d8",
      upcastFlat: null,
      perLevel: 1,
      maxLevel: null,
      baseEffectInstances: null,
      baseDice: "1d8",
      baseMaxTargets: null,
    });

    expect(rows).toHaveLength(4);
    expect(rows[0].value).toBe("1d8");
    expect(rows[1].value).toBe("2d8");
    expect(rows[2].value).toBe("3d8");
    expect(rows[3].value).toBe("4d8");
  });

  it("computes Magic Missile-style instance preview", () => {
    const rows = computeUpcastPreviewRows({
      spellLevel: 1,
      upcastMode: "additional_effect_instances" as UpcastMode,
      upcastDice: "1d4+1",
      upcastFlat: null,
      perLevel: 1,
      maxLevel: null,
      baseEffectInstances: 3,
      baseDice: "3d4+3",
      baseMaxTargets: null,
    });

    expect(rows).toHaveLength(4);
    expect(rows[0].value).toBe("no change");
    expect(rows[1].value).toBe("+1 (4 instances)");
    expect(rows[2].value).toBe("+2 (5 instances)");
    expect(rows[3].value).toBe("+3 (6 instances)");
  });

  it("computes Hold Person-style target preview", () => {
    const rows = computeUpcastPreviewRows({
      spellLevel: 2,
      upcastMode: "additional_targets" as UpcastMode,
      upcastDice: null,
      upcastFlat: null,
      perLevel: 1,
      maxLevel: null,
      baseEffectInstances: null,
      baseDice: null,
      baseMaxTargets: 1,
    });

    expect(rows).toHaveLength(4);
    expect(rows[0].value).toBe("no change");
    expect(rows[1].value).toBe("+1 (2 targets)");
    expect(rows[2].value).toBe("+2 (3 targets)");
    expect(rows[3].value).toBe("+3 (4 targets)");
  });

  it("computes flat bonus preview", () => {
    const rows = computeUpcastPreviewRows({
      spellLevel: 1,
      upcastMode: "flat_bonus" as UpcastMode,
      upcastDice: null,
      upcastFlat: 2,
      perLevel: 1,
      maxLevel: null,
      baseEffectInstances: null,
      baseDice: null,
      baseMaxTargets: null,
    });

    expect(rows).toHaveLength(4);
    expect(rows[0].value).toBe("—");
    expect(rows[1].value).toBe("+2");
    expect(rows[2].value).toBe("+4");
    expect(rows[3].value).toBe("+6");
  });

  it("respects maxLevel cap", () => {
    const rows = computeUpcastPreviewRows({
      spellLevel: 1,
      upcastMode: "extra_damage_dice" as UpcastMode,
      upcastDice: "1d6",
      upcastFlat: null,
      perLevel: 1,
      maxLevel: 3,
      baseEffectInstances: null,
      baseDice: "2d6",
      baseMaxTargets: null,
    });

    expect(rows).toHaveLength(3);
    expect(rows[0].slotLevel).toBe(1);
    expect(rows[1].slotLevel).toBe(2);
    expect(rows[2].slotLevel).toBe(3);
  });

  it("handles perLevel > 1", () => {
    const rows = computeUpcastPreviewRows({
      spellLevel: 1,
      upcastMode: "additional_targets" as UpcastMode,
      upcastDice: null,
      upcastFlat: null,
      perLevel: 2,
      maxLevel: null,
      baseEffectInstances: null,
      baseDice: null,
      baseMaxTargets: 1,
    });

    expect(rows[0].value).toBe("no change");
    expect(rows[1].value).toBe("+2 (3 targets)");
    expect(rows[2].value).toBe("+4 (5 targets)");
  });

  it("shows placeholder when base dice is missing", () => {
    const rows = computeUpcastPreviewRows({
      spellLevel: 1,
      upcastMode: "extra_damage_dice" as UpcastMode,
      upcastDice: "1d6",
      upcastFlat: null,
      perLevel: 1,
      maxLevel: null,
      baseEffectInstances: null,
      baseDice: null,
      baseMaxTargets: null,
    });

    expect(rows[0].value).toBe("—");
    expect(rows[1].value).toBe("1d6");
  });

  it("shows duration scaling preview", () => {
    const rows = computeUpcastPreviewRows({
      spellLevel: 1,
      upcastMode: "duration_scaling" as UpcastMode,
      upcastDice: null,
      upcastFlat: null,
      perLevel: 1,
      maxLevel: null,
      baseEffectInstances: null,
      baseDice: null,
      baseMaxTargets: null,
    });

    expect(rows[0].value).toBe("Base duration");
    expect(rows[1].value).toBe("+1 level");
    expect(rows[2].value).toBe("+2 levels");
  });

  it("shows effect scaling preview", () => {
    const rows = computeUpcastPreviewRows({
      spellLevel: 1,
      upcastMode: "effect_scaling" as UpcastMode,
      upcastDice: null,
      upcastFlat: null,
      perLevel: 1,
      maxLevel: null,
      baseEffectInstances: null,
      baseDice: null,
      baseMaxTargets: null,
    });

    expect(rows[0].value).toBe("Base effect");
    expect(rows[1].value).toBe("Scales at +1 level");
    expect(rows[2].value).toBe("Scales at +2 levels");
  });

  it("shows extra effect preview", () => {
    const rows = computeUpcastPreviewRows({
      spellLevel: 1,
      upcastMode: "extra_effect" as UpcastMode,
      upcastDice: null,
      upcastFlat: null,
      perLevel: 1,
      maxLevel: null,
      baseEffectInstances: null,
      baseDice: null,
      baseMaxTargets: null,
    });

    expect(rows[0].value).toBe("Base effect");
    expect(rows[1].value).toBe("Additional effect unlocked");
  });

  it("handles damage dice upcast with flat bonus and no dice", () => {
    const rows = computeUpcastPreviewRows({
      spellLevel: 1,
      upcastMode: "extra_damage_dice" as UpcastMode,
      upcastDice: null,
      upcastFlat: 2,
      perLevel: 1,
      maxLevel: null,
      baseEffectInstances: null,
      baseDice: "2d6",
      baseMaxTargets: null,
    });

    expect(rows[0].value).toBe("2d6");
    expect(rows[1].value).toBe("2d6+2");
    expect(rows[2].value).toBe("2d6+4");
  });
});

describe("computeUpcastValidationWarnings", () => {
  const baseParams: UpcastValidationParams = {
    resolutionType: "damage",
    upcastMode: "",
    upcastDiceCount: "",
    upcastDieSize: "",
    upcastFlat: "",
    upcastScalingKey: "",
    upcastScalingSummary: "",
    upcastUnlockKey: "",
    upcastUnlockSummary: "",
  };

  it("returns no warnings when no mode is selected", () => {
    expect(computeUpcastValidationWarnings(baseParams)).toEqual([]);
  });

  it("warns when extra_damage_dice with non-damage resolution", () => {
    const warnings = computeUpcastValidationWarnings({
      ...baseParams,
      upcastMode: "extra_damage_dice",
      upcastDiceCount: "1",
      upcastDieSize: "6",
      resolutionType: "heal",
    });
    expect(warnings).toEqual([
      { key: "catalog.spells.validation.upcastModeRequiresDamage" },
    ]);
  });

  it("warns when extra_heal_dice with non-heal resolution", () => {
    const warnings = computeUpcastValidationWarnings({
      ...baseParams,
      upcastMode: "extra_heal_dice",
      upcastDiceCount: "1",
      upcastDieSize: "8",
      resolutionType: "damage",
    });
    expect(warnings).toEqual([
      { key: "catalog.spells.validation.upcastModeRequiresHeal" },
    ]);
  });

  it("warns when dice mode has no dice or flat", () => {
    const warnings = computeUpcastValidationWarnings({
      ...baseParams,
      upcastMode: "extra_damage_dice",
      resolutionType: "damage",
    });
    expect(warnings).toEqual([
      { key: "catalog.spells.validation.upcastDiceOrBonusRequired" },
    ]);
  });

  it("does not warn when dice mode has dice configured", () => {
    const warnings = computeUpcastValidationWarnings({
      ...baseParams,
      upcastMode: "extra_damage_dice",
      resolutionType: "damage",
      upcastDiceCount: "1",
      upcastDieSize: "6",
    });
    expect(warnings).toEqual([]);
  });

  it("does not warn when dice mode has flat configured", () => {
    const warnings = computeUpcastValidationWarnings({
      ...baseParams,
      upcastMode: "extra_heal_dice",
      resolutionType: "heal",
      upcastFlat: "2",
    });
    expect(warnings).toEqual([]);
  });

  it("warns when flat_bonus has no flat value", () => {
    const warnings = computeUpcastValidationWarnings({
      ...baseParams,
      upcastMode: "flat_bonus",
    });
    expect(warnings).toEqual([
      { key: "catalog.spells.validation.upcastFlatRequired" },
    ]);
  });

  it("warns when effect_scaling has no scaling key", () => {
    const warnings = computeUpcastValidationWarnings({
      ...baseParams,
      upcastMode: "effect_scaling",
      upcastScalingSummary: "some summary",
    });
    expect(warnings).toEqual([
      { key: "catalog.spells.validation.upcastScalingKeyRequired" },
    ]);
  });

  it("warns when effect_scaling has no scaling summary", () => {
    const warnings = computeUpcastValidationWarnings({
      ...baseParams,
      upcastMode: "effect_scaling",
      upcastScalingKey: "radius",
    });
    expect(warnings).toEqual([
      { key: "catalog.spells.validation.upcastScalingSummaryRequired" },
    ]);
  });

  it("warns when extra_effect has no unlock key", () => {
    const warnings = computeUpcastValidationWarnings({
      ...baseParams,
      upcastMode: "extra_effect",
      upcastUnlockSummary: "extra beam",
    });
    expect(warnings).toEqual([
      { key: "catalog.spells.validation.upcastUnlockKeyRequired" },
    ]);
  });

  it("warns when extra_effect has no unlock summary", () => {
    const warnings = computeUpcastValidationWarnings({
      ...baseParams,
      upcastMode: "extra_effect",
      upcastUnlockKey: "beam",
    });
    expect(warnings).toEqual([
      { key: "catalog.spells.validation.upcastUnlockSummaryRequired" },
    ]);
  });

  it("returns multiple warnings simultaneously", () => {
    const warnings = computeUpcastValidationWarnings({
      ...baseParams,
      upcastMode: "extra_damage_dice",
      resolutionType: "heal",
    });
    expect(warnings).toHaveLength(2);
    expect(warnings[0].key).toBe("catalog.spells.validation.upcastModeRequiresDamage");
    expect(warnings[1].key).toBe("catalog.spells.validation.upcastDiceOrBonusRequired");
  });

  it("warns for additional_effect_instances without dice or flat", () => {
    const warnings = computeUpcastValidationWarnings({
      ...baseParams,
      upcastMode: "additional_effect_instances",
    });
    expect(warnings).toEqual([
      { key: "catalog.spells.validation.upcastDiceOrBonusRequired" },
    ]);
  });
});
