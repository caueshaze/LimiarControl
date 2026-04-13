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
    form.upcastDice = "1d8";
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
      targetMode: "ranged",
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
        mode: "additional_targets",
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

    expect(form.upcastMode).toBe("additional_targets");
    expect(form.upcastDice).toBe("1d4+1");
    expect(form.upcastPerLevel).toBe("1");
    expect(form.upcastMaxLevel).toBe("9");
  });
});
