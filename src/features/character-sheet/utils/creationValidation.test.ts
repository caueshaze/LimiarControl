import { beforeAll, describe, expect, it } from "vitest";
import { nanoid } from "nanoid";

import { getClass } from "../data/classes";
import { getClassCreationConfig } from "../data/classCreation";
import { INITIAL_SHEET } from "../model/initialSheet";
import { seedSpellCatalogCache } from "../../../entities/dnd-base";
import { getAvailableStartingSpells } from "./creationSpells";
import { validateCreationSheet } from "./creationValidation";
import { getInitialClassEquipmentSelections } from "./creationEquipment";

// Seed the API-backed spell catalog cache with test data
// so that getAvailableStartingSpells works without a backend.
beforeAll(() => {
  seedSpellCatalogCache([
    { name: "Guidance", level: 0, school: "Divination", castingTime: "1 action", range: "Touch", components: "V, S", duration: "Up to 1 minute", concentration: true, ritual: false, description: "", damageType: null, savingThrow: null, classes: ["Cleric", "Druid"] },
    { name: "Light", level: 0, school: "Evocation", castingTime: "1 action", range: "Touch", components: "V, M", duration: "1 hour", concentration: false, ritual: false, description: "", damageType: null, savingThrow: null, classes: ["Bard", "Cleric", "Sorcerer", "Wizard"] },
    { name: "Sacred Flame", level: 0, school: "Evocation", castingTime: "1 action", range: "60 feet", components: "V, S", duration: "Instantaneous", concentration: false, ritual: false, description: "", damageType: "Radiant", savingThrow: "DEX", classes: ["Cleric"] },
    { name: "Thaumaturgy", level: 0, school: "Transmutation", castingTime: "1 action", range: "30 feet", components: "V", duration: "Up to 1 minute", concentration: false, ritual: false, description: "", damageType: null, savingThrow: null, classes: ["Cleric"] },
    { name: "Bless", level: 1, school: "Enchantment", castingTime: "1 action", range: "30 feet", components: "V, S, M", duration: "Up to 1 minute", concentration: true, ritual: false, description: "", damageType: null, savingThrow: null, classes: ["Cleric", "Paladin"] },
    { name: "Cure Wounds", level: 1, school: "Evocation", castingTime: "1 action", range: "Touch", components: "V, S", duration: "Instantaneous", concentration: false, ritual: false, description: "", damageType: null, savingThrow: null, classes: ["Bard", "Cleric", "Druid", "Paladin", "Ranger"] },
    { name: "Healing Word", level: 1, school: "Evocation", castingTime: "1 bonus action", range: "60 feet", components: "V", duration: "Instantaneous", concentration: false, ritual: false, description: "", damageType: null, savingThrow: null, classes: ["Bard", "Cleric", "Druid"] },
  ]);
});

const buildSpellSelection = (className: string, cantripCount: number, leveledCount: number) => {
  const cls = getClass(className);
  const spells = getAvailableStartingSpells(className);
  const mode = getClassCreationConfig(className)?.startingSpells?.leveledMode ?? "known";

  return {
    ability: cls?.spellcastingAbility ?? "intelligence",
    mode,
    slots: { 1: { max: 2, used: 0 } },
    spells: [
      ...spells.cantrips.slice(0, cantripCount).map((spell) => ({
        id: nanoid(),
        name: spell.name,
        level: spell.level,
        school: spell.school || "Evocation",
        prepared: true,
        notes: "",
      })),
      ...spells.leveled.slice(0, leveledCount).map((spell) => ({
        id: nanoid(),
        name: spell.name,
        level: spell.level,
        school: spell.school || "Evocation",
        prepared: true,
        notes: "",
      })),
    ],
  };
};

describe("validateCreationSheet", () => {
  it("marks the basic creation fields as required", () => {
    const result = validateCreationSheet(INITIAL_SHEET);

    expect(result.isValid).toBe(false);
    expect(result.missingRequiredFields).toEqual([
      "name",
      "class",
      "race",
      "background",
      "alignment",
      "playerName",
    ]);
  });

  it("requires the full number of class skill picks", () => {
    const result = validateCreationSheet({
      ...INITIAL_SHEET,
      name: "Alaric",
      class: "fighter",
      race: "human",
      background: "soldier",
      alignment: "Lawful Good",
      playerName: "Player One",
      classSkillChoices: ["athletics"],
    });

    expect(result.isValid).toBe(false);
    expect(result.missingRequiredFields).toContain("classSkills");
  });

  it("requires starting spell picks for creation casters", () => {
    const result = validateCreationSheet({
      ...INITIAL_SHEET,
      name: "Mira",
      class: "cleric",
      race: "human",
      background: "acolyte",
      alignment: "Neutral Good",
      playerName: "Player Two",
      classSkillChoices: ["history", "religion"],
      spellcasting: buildSpellSelection("cleric", 2, 0),
    });

    expect(result.isValid).toBe(false);
    expect(result.missingRequiredFields).toContain("cantrips");
    expect(result.missingRequiredFields).toContain("leveledSpells");
    expect(result.spellDetails).toMatchObject({
      selectedCantrips: 2,
      totalCantrips: 3,
      selectedLeveled: 0,
      totalLeveled: 1,
    });
  });

  it("accepts a creation sheet once all required fields are filled", () => {
    const result = validateCreationSheet({
      ...INITIAL_SHEET,
      name: "Mira",
      class: "cleric",
      race: "human",
      background: "acolyte",
      alignment: "Neutral Good",
      playerName: "Player Two",
      classSkillChoices: ["history", "religion"],
      classEquipmentSelections: getInitialClassEquipmentSelections("cleric"),
      languageChoices: ["Élfico", "Anão", "Gnomo"],
      spellcasting: buildSpellSelection("cleric", 3, 1),
    });

    expect(result.isValid).toBe(true);
    expect(result.missingRequiredFields).toEqual([]);
  });
});
