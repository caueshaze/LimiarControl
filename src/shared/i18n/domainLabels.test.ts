import { describe, expect, it } from "vitest";
import {
  formatDamageLabel,
  localizeBaseItemAdminValue,
  localizeBaseItemDexBonusRule,
  localizeDamageType,
  localizeSaveSuccessOutcome,
  localizeSpellAdminValue,
  localizeSpellClass,
  localizeSpellSchool,
} from "./domainLabels";

describe("domainLabels", () => {
  it("localizes damage types in PT and EN", () => {
    expect(localizeDamageType("piercing", "pt")).toBe("Perfurante");
    expect(localizeDamageType("Piercing", "en")).toBe("Piercing");
  });

  it("formats combined damage labels with localized damage type", () => {
    expect(formatDamageLabel("1d8", "slashing", "pt")).toBe("1d8 Cortante");
    expect(formatDamageLabel("2d6", "fire", "en")).toBe("2d6 Fire");
  });

  it("localizes base item admin values", () => {
    expect(localizeBaseItemAdminValue("weapon", "pt")).toBe("Arma");
    expect(localizeBaseItemAdminValue("max_2", "en")).toBe("Max +2 DEX");
    expect(localizeBaseItemDexBonusRule("none", "pt")).toBe("Sem bônus de DEX");
  });

  it("localizes spell admin values", () => {
    expect(localizeSpellSchool("transmutation", "pt")).toBe("Transmutação");
    expect(localizeSpellAdminValue("saving_throw", "en")).toBe("Saving throw");
    expect(localizeSaveSuccessOutcome("half_damage", "pt")).toBe("Metade do dano");
  });

  it("localizes spell classes", () => {
    expect(localizeSpellClass("Wizard", "pt")).toBe("Mago");
    expect(localizeSpellClass("Cleric", "en")).toBe("Cleric");
  });

  it("falls back safely for unknown values", () => {
    expect(localizeBaseItemAdminValue("mystery_value", "pt")).toBe("Mystery Value");
    expect(localizeSpellAdminValue("mystery_value", "en")).toBe("Mystery Value");
  });
});
