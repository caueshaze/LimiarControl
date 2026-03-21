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
    { canonicalKey: "guidance", name: "Guidance", level: 0, school: "Divination", castingTime: "1 action", range: "Touch", components: "V, S", duration: "Up to 1 minute", concentration: true, ritual: false, description: "", damageType: null, savingThrow: null, classes: ["Cleric", "Druid"] },
    { canonicalKey: "light", name: "Light", level: 0, school: "Evocation", castingTime: "1 action", range: "Touch", components: "V, M", duration: "1 hour", concentration: false, ritual: false, description: "", damageType: null, savingThrow: null, classes: ["Bard", "Cleric", "Sorcerer", "Wizard"] },
    { canonicalKey: "sacred_flame", name: "Sacred Flame", level: 0, school: "Evocation", castingTime: "1 action", range: "60 feet", components: "V, S", duration: "Instantaneous", concentration: false, ritual: false, description: "", damageType: "Radiant", savingThrow: "DEX", classes: ["Cleric"] },
    { canonicalKey: "thaumaturgy", name: "Thaumaturgy", level: 0, school: "Transmutation", castingTime: "1 action", range: "30 feet", components: "V", duration: "Up to 1 minute", concentration: false, ritual: false, description: "", damageType: null, savingThrow: null, classes: ["Cleric"] },
    { canonicalKey: "bless", name: "Bless", level: 1, school: "Enchantment", castingTime: "1 action", range: "30 feet", components: "V, S, M", duration: "Up to 1 minute", concentration: true, ritual: false, description: "", damageType: null, savingThrow: null, classes: ["Cleric", "Paladin"] },
    { canonicalKey: "cure_wounds", name: "Cure Wounds", level: 1, school: "Evocation", castingTime: "1 action", range: "Touch", components: "V, S", duration: "Instantaneous", concentration: false, ritual: false, description: "", damageType: null, savingThrow: null, classes: ["Bard", "Cleric", "Druid", "Paladin", "Ranger"] },
    { canonicalKey: "healing_word", name: "Healing Word", level: 1, school: "Evocation", castingTime: "1 bonus action", range: "60 feet", components: "V", duration: "Instantaneous", concentration: false, ritual: false, description: "", damageType: null, savingThrow: null, classes: ["Bard", "Cleric", "Druid"] },
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

const buildBaseCreationSheet = (className: string, level = 1) => {
  const cls = getClass(className);

  return {
    ...INITIAL_SHEET,
    name: "Teste",
    class: className,
    level,
    race: "human",
    background: "soldier",
    alignment: "Neutral",
    playerName: "Player",
    classSkillChoices: cls?.skillChoices.slice(0, cls.skillCount) ?? [],
    classEquipmentSelections: getInitialClassEquipmentSelections(className),
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
      subclass: "life",
      classSkillChoices: ["history", "religion"],
      classEquipmentSelections: getInitialClassEquipmentSelections("cleric"),
      languageChoices: ["Élfico", "Anão", "Gnomo"],
      spellcasting: buildSpellSelection("cleric", 3, 1),
    });

    expect(result.isValid).toBe(true);
    expect(result.missingRequiredFields).toEqual([]);
  });

  it("requires a cleric subclass at level 1", () => {
    const result = validateCreationSheet({
      ...buildBaseCreationSheet("cleric"),
      background: "acolyte",
      classSkillChoices: ["history", "religion"],
    });

    expect(result.missingRequiredFields).toContain("subclass");
  });

  it("does not require a fighter subclass at level 1", () => {
    const result = validateCreationSheet(buildBaseCreationSheet("fighter", 1));

    expect(result.missingRequiredFields).not.toContain("subclass");
  });

  it("requires a fighter subclass at level 3", () => {
    const result = validateCreationSheet(buildBaseCreationSheet("fighter", 3));

    expect(result.missingRequiredFields).toContain("subclass");
  });

  it("does not require a wizard subclass at level 1", () => {
    const result = validateCreationSheet(buildBaseCreationSheet("wizard", 1));

    expect(result.missingRequiredFields).not.toContain("subclass");
  });

  it("requires a wizard subclass at level 2", () => {
    const result = validateCreationSheet(buildBaseCreationSheet("wizard", 2));

    expect(result.missingRequiredFields).toContain("subclass");
  });

  it("requires a dragonborn ancestry during creation", () => {
    const result = validateCreationSheet({
      ...buildBaseCreationSheet("fighter", 1),
      race: "dragonborn",
      raceConfig: null,
    });

    expect(result.isValid).toBe(false);
    expect(result.missingRequiredFields).toContain("raceConfig");
  });

  it("accepts a valid dragonborn ancestry during creation", () => {
    const result = validateCreationSheet({
      ...buildBaseCreationSheet("fighter", 1),
      race: "dragonborn",
      raceConfig: { dragonbornAncestry: "red" },
    });

    expect(result.missingRequiredFields).not.toContain("raceConfig");
  });

  it("requires a gnome subrace during creation", () => {
    const result = validateCreationSheet({
      ...buildBaseCreationSheet("fighter", 1),
      race: "gnome",
      raceConfig: null,
    });

    expect(result.isValid).toBe(false);
    expect(result.missingRequiredFields).toContain("raceConfig");
  });

  it("accepts a valid gnome subrace during creation", () => {
    const result = validateCreationSheet({
      ...buildBaseCreationSheet("fighter", 1),
      race: "gnome",
      raceConfig: { gnomeSubrace: "forest" },
    });

    expect(result.missingRequiredFields).not.toContain("raceConfig");
  });

  it("requires half-elf attribute and skill choices during creation", () => {
    const result = validateCreationSheet({
      ...buildBaseCreationSheet("fighter", 1),
      race: "half-elf",
      raceConfig: null,
      languageChoices: ["Gnomo"],
    });

    expect(result.isValid).toBe(false);
    expect(result.missingRequiredFields).toContain("raceConfig");
  });

  it("rejects invalid half-elf raceConfig choices during creation", () => {
    const result = validateCreationSheet({
      ...buildBaseCreationSheet("fighter", 1),
      race: "half-elf",
      raceConfig: {
        halfElfAbilityChoices: ["charisma", "wisdom"],
        halfElfSkillChoices: ["insight", "insight"],
      },
      languageChoices: ["Gnomo"],
    });

    expect(result.isValid).toBe(false);
    expect(result.missingRequiredFields).toContain("raceConfig");
  });

  it("accepts valid half-elf choices during creation", () => {
    const result = validateCreationSheet({
      ...buildBaseCreationSheet("fighter", 1),
      race: "half-elf",
      raceConfig: {
        halfElfAbilityChoices: ["constitution", "wisdom"],
        halfElfSkillChoices: ["insight", "persuasion"],
      },
      languageChoices: ["Gnomo"],
    });

    expect(result.missingRequiredFields).not.toContain("raceConfig");
  });
});
