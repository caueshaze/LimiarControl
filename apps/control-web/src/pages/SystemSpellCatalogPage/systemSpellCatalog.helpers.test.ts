import { describe, expect, it } from "vitest";

import type { BaseSpell } from "../../entities/base-spell";
import {
  buildPayload,
  createEmptyForm,
  formFromSpell,
} from "./systemSpellCatalog.helpers";

describe("systemSpellCatalog upcast helpers", () => {
  it("builds a structured upcast payload without relying on free text", () => {
    const form = createEmptyForm();
    form.canonicalKey = "cure_wounds";
    form.nameEn = "Cure Wounds";
    form.descriptionEn = "Healing energy restores hit points.";
    form.level = 1;
    form.school = "evocation";
    form.resolutionType = "heal";
    form.healDice = "1d8";
    form.upcastMode = "extra_heal_dice";
    form.upcastDiceCount = "1";
    form.upcastDieSize = "8";
    form.upcastFixedBonus = "";
    form.upcastPerLevel = "1";
    form.upcastMaxLevel = "9";

    const result = buildPayload(form, true);

    expect(result.error).toBeUndefined();
    expect(result.payload?.upcast).toEqual({
      mode: "extra_heal_dice",
      dice: "1d8",
      flat: null,
      perLevel: 1,
      maxLevel: 9,
    });
  });

  it("serializes spell targeting semantics into payloads", () => {
    const form = createEmptyForm();
    form.canonicalKey = "fireball";
    form.nameEn = "Fireball";
    form.descriptionEn = "A bright streak flashes to a point you choose.";
    form.level = 3;
    form.school = "evocation";
    form.targetType = "ranged";
    form.selectionType = "point";
    form.originType = "selected_point";
    form.targetAnchor = "selected_point";
    form.attackType = "none";
    form.rangeKind = "distance";
    form.effectTiming = "immediate";

    const result = buildPayload(form, true);

    expect(result.error).toBeUndefined();
    expect(result.payload).toEqual(
      expect.objectContaining({
        selectionType: "point",
        originType: "selected_point",
        targetAnchor: "selected_point",
        attackType: "none",
        rangeKind: "distance",
        effectTiming: "immediate",
      }),
    );
  });

  it("hydrates the structured upcast back into the form state", () => {
    const spell: BaseSpell = {
      id: "spell-1",
      system: "DND5E",
      canonicalKey: "magic_missile",
      nameEn: "Magic Missile",
      namePt: "Misseis Magicos",
      descriptionEn: "Three glowing darts of magical force.",
      descriptionPt: "Tres dardos de energia magica.",
      level: 1,
      school: "evocation",
      classesJson: ["Wizard"],
      castingTimeType: "action",
      castingTime: "1 action",
      rangeMeters: 36,
      rangeText: "120 ft",
      targetType: "ranged",
      maxTargets: 3,
      selectionType: "creature",
      originType: "caster",
      targetAnchor: "selected_target",
      attackType: "none",
      rangeKind: "distance",
      effectTiming: "immediate",
      duration: "Instantaneous",
      componentsJson: ["V", "S"],
      materialComponentText: null,
      concentration: false,
      ritual: false,
      resolutionType: "damage",
      savingThrow: null,
      saveSuccessOutcome: null,
      damageDice: "3d4+3",
      damageType: "Force",
      healDice: null,
      upcast: {
        mode: "additional_effect_instances",
        dice: "1d4+1",
        perLevel: 1,
        maxLevel: 9,
      },
      source: "admin_panel",
      sourceRef: null,
      isSrd: true,
      isActive: true,
      aliases: [],
    };

    const form = formFromSpell(spell);

    expect(form.upcastMode).toBe("additional_effect_instances");
    expect(form.upcastDice).toBe("1d4+1");
    expect(form.upcastPerLevel).toBe("1");
    expect(form.upcastMaxLevel).toBe("9");
    expect(form.maxTargets).toBe("3");
    expect(form.damageDiceCount).toBe("3");
    expect(form.damageDieSize).toBe("4");
    expect(form.damageFixedBonus).toBe("3");
    expect(form.selectionType).toBe("creature");
    expect(form.originType).toBe("caster");
    expect(form.targetAnchor).toBe("selected_target");
    expect(form.attackType).toBe("none");
    expect(form.rangeKind).toBe("distance");
    expect(form.effectTiming).toBe("immediate");
  });

  it("builds cantrip scaling separately from upcast", () => {
    const form = createEmptyForm();
    form.canonicalKey = "acid_splash";
    form.nameEn = "Acid Splash";
    form.descriptionEn = "A bubble of acid.";
    form.level = 0;
    form.school = "conjuration";
    form.resolutionType = "damage";
    form.damageDiceCount = "1";
    form.damageDieSize = "6";
    form.damageType = "Acid";
    form.upcastMode = "extra_damage_dice";

    const result = buildPayload(form, true);

    expect(result.error).toBeUndefined();
    expect(result.payload?.upcast).toBeNull();
    expect(result.payload?.cantripScaling).toEqual({
      scalingMode: "character_level",
      scalingEffectType: "damage_dice",
      thresholds: [
        { characterLevel: 1, damage: { dice: "1d6" } },
        { characterLevel: 5, damage: { dice: "2d6" } },
        { characterLevel: 11, damage: { dice: "3d6" } },
        { characterLevel: 17, damage: { dice: "4d6" } },
      ],
    });
  });

  it("includes coverAppliesToSave in payload when set", () => {
    const form = createEmptyForm();
    form.canonicalKey = "fireball";
    form.nameEn = "Fireball";
    form.descriptionEn = "A bright streak flashes.";
    form.level = 3;
    form.school = "evocation";
    form.resolutionType = "damage";
    form.savingThrow = "DEX";
    form.coverAppliesToSave = "physical";
    form.damageDiceCount = "8";
    form.damageDieSize = "6";
    form.damageType = "Fire";

    const result = buildPayload(form, true);

    expect(result.error).toBeUndefined();
    expect(result.payload?.coverAppliesToSave).toBe("physical");
  });

  it("defaults coverAppliesToSave to null when empty", () => {
    const form = createEmptyForm();
    form.canonicalKey = "test";
    form.nameEn = "Test";
    form.descriptionEn = "Test.";

    const result = buildPayload(form, true);

    expect(result.error).toBeUndefined();
    expect(result.payload?.coverAppliesToSave).toBeNull();
  });

  it("includes baseEffectInstances in upcast payload for additional_effect_instances", () => {
    const form = createEmptyForm();
    form.canonicalKey = "magic_missile";
    form.nameEn = "Magic Missile";
    form.descriptionEn = "Three glowing darts.";
    form.level = 1;
    form.school = "evocation";
    form.resolutionType = "damage";
    form.damageDiceCount = "3";
    form.damageDieSize = "4";
    form.damageFixedBonus = "3";
    form.damageType = "Force";
    form.upcastMode = "additional_effect_instances";
    form.upcastDiceCount = "1";
    form.upcastDieSize = "4";
    form.upcastFixedBonus = "1";
    form.upcastBaseEffectInstances = "3";

    const result = buildPayload(form, true);

    expect(result.error).toBeUndefined();
    expect(result.payload?.upcast?.baseEffectInstances).toBe(3);
  });

  it("hydrates coverAppliesToSave and baseEffectInstances from spell", () => {
    const spell: BaseSpell = {
      id: "spell-fireball",
      system: "DND5E",
      canonicalKey: "fireball",
      nameEn: "Fireball",
      namePt: "Bola de Fogo",
      descriptionEn: "A bright streak flashes to a point.",
      descriptionPt: null,
      level: 3,
      school: "evocation",
      classesJson: ["Sorcerer", "Wizard"],
      castingTimeType: "action",
      castingTime: "1 action",
      rangeMeters: 45,
      rangeText: "150 ft",
      targetType: "ranged",
      maxTargets: null,
      selectionType: "point",
      originType: "selected_point",
      targetAnchor: "selected_point",
      attackType: "none",
      rangeKind: "distance",
      effectTiming: "immediate",
      areaShape: "sphere",
      radiusMeters: 6,
      lengthMeters: null,
      sideMeters: null,
      duration: "Instantaneous",
      componentsJson: ["V", "S", "M"],
      materialComponentText: "a tiny ball of bat guano and sulfur",
      concentration: false,
      ritual: false,
      resolutionType: "damage",
      savingThrow: "DEX",
      saveSuccessOutcome: "half_damage",
      coverAppliesToSave: "physical",
      damageDice: "8d6",
      damageType: "Fire",
      healDice: null,
      upcast: {
        mode: "extra_damage_dice",
        dice: "1d6",
        perLevel: 1,
      },
      source: "admin_panel",
      sourceRef: null,
      isSrd: true,
      isActive: true,
      aliases: [],
    };

    const form = formFromSpell(spell);

    expect(form.coverAppliesToSave).toBe("physical");
  });
});
