import { beforeAll, describe, expect, it } from "vitest";
import { nanoid } from "nanoid";

import { getClass } from "../data/classes";
import { getClassCreationConfig } from "../data/classCreation";
import { INITIAL_SHEET } from "../model/initialSheet";
import { seedSpellCatalogCache } from "../../../entities/dnd-base";
import { getAvailableStartingSpells } from "./creationSpells";
import { getStartingSpellLimits } from "./creationSpells";
import { validateCreationSheet } from "./creationValidation";
import { getInitialClassEquipmentSelections } from "./creationEquipment";

// Seed the API-backed spell catalog cache with test data
// so that getAvailableStartingSpells works without a backend.
beforeAll(() => {
  seedSpellCatalogCache([
    { canonicalKey: "guidance", name: "Guidance", level: 0, school: "Divination", castingTime: "1 action", range: "Touch", components: "V, S", duration: "Up to 1 minute", concentration: true, ritual: false, description: "", damageType: null, savingThrow: null, classes: ["Cleric", "Druid"] },
    { canonicalKey: "light", name: "Light", level: 0, school: "Evocation", castingTime: "1 action", range: "Touch", components: "V, M", duration: "1 hour", concentration: false, ritual: false, description: "", damageType: null, savingThrow: null, classes: ["Bard", "Cleric", "Sorcerer", "Wizard"] },
    { canonicalKey: "sacred_flame", name: "Sacred Flame", level: 0, school: "Evocation", castingTime: "1 action", range: "18 m", components: "V, S", duration: "Instantaneous", concentration: false, ritual: false, description: "", damageType: "Radiant", savingThrow: "DEX", classes: ["Cleric"] },
    { canonicalKey: "thaumaturgy", name: "Thaumaturgy", level: 0, school: "Transmutation", castingTime: "1 action", range: "9 m", components: "V", duration: "Up to 1 minute", concentration: false, ritual: false, description: "", damageType: null, savingThrow: null, classes: ["Cleric"] },
    { canonicalKey: "bless", name: "Bless", level: 1, school: "Enchantment", castingTime: "1 action", range: "9 m", components: "V, S, M", duration: "Up to 1 minute", concentration: true, ritual: false, description: "", damageType: null, savingThrow: null, classes: ["Cleric", "Paladin"] },
    { canonicalKey: "animal_friendship", name: "Animal Friendship", level: 1, school: "Enchantment", castingTime: "1 action", range: "9 m", components: "V, S, M", duration: "24 hours", concentration: false, ritual: false, description: "", damageType: null, savingThrow: "WIS", classes: ["Bard", "Druid", "Ranger"] },
    { canonicalKey: "cure_wounds", name: "Cure Wounds", level: 1, school: "Evocation", castingTime: "1 action", range: "Touch", components: "V, S", duration: "Instantaneous", concentration: false, ritual: false, description: "", damageType: null, savingThrow: null, classes: ["Bard", "Cleric", "Druid", "Paladin", "Ranger"] },
    { canonicalKey: "goodberry", name: "Goodberry", level: 1, school: "Transmutation", castingTime: "1 action", range: "Touch", components: "V, S, M", duration: "Instantaneous", concentration: false, ritual: false, description: "", damageType: null, savingThrow: null, classes: ["Druid", "Ranger"] },
    { canonicalKey: "healing_word", name: "Healing Word", level: 1, school: "Evocation", castingTime: "1 bonus action", range: "18 m", components: "V", duration: "Instantaneous", concentration: false, ritual: false, description: "", damageType: null, savingThrow: null, classes: ["Bard", "Cleric", "Druid"] },
    { canonicalKey: "hunters_mark", name: "Hunter's Mark", level: 1, school: "Divination", castingTime: "1 bonus action", range: "27 m", components: "V", duration: "Up to 1 hour", concentration: true, ritual: false, description: "", damageType: null, savingThrow: null, classes: ["Ranger"] },
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
        canonicalKey: spell.canonicalKey,
        level: spell.level,
        school: spell.school || "Evocation",
        prepared: true,
        notes: "",
      })),
      ...spells.leveled.slice(0, leveledCount).map((spell) => ({
        id: nanoid(),
        name: spell.name,
        canonicalKey: spell.canonicalKey,
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

  it("uses the ranger spell list and level-aware slot limits for guardian", () => {
    expect(getAvailableStartingSpells("guardian").leveled.map((spell) => spell.canonicalKey)).toEqual([
      "animal_friendship",
      "cure_wounds",
      "goodberry",
      "hunters_mark",
    ]);
    expect(getStartingSpellLimits("guardian", INITIAL_SHEET.abilities, 1)).toBeNull();
    expect(getStartingSpellLimits("guardian", INITIAL_SHEET.abilities, 2)).toMatchObject({
      cantrips: 0,
      leveledSpells: 2,
      levelOneSlots: 2,
    });
    expect(getStartingSpellLimits("guardian", INITIAL_SHEET.abilities, 3)).toMatchObject({
      leveledSpells: 3,
      levelOneSlots: 3,
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

  it("does not require manual subclass or fighting style picks for guardian", () => {
    const result = validateCreationSheet({
      ...buildBaseCreationSheet("guardian", 3),
      subclass: "hunter",
      fightingStyle: "archery",
      spellcasting: buildSpellSelection("guardian", 0, 1),
    });

    expect(result.missingRequiredFields).not.toContain("subclass");
    expect(result.missingRequiredFields).not.toContain("fightingStyle");
    expect(result.missingRequiredFields).toContain("leveledSpells");
    expect(result.spellDetails).toMatchObject({
      selectedLeveled: 1,
      totalLeveled: 3,
    });
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

  it("requires draconic ancestry for Draconic Bloodline", () => {
    const result = validateCreationSheet({
      ...buildBaseCreationSheet("sorcerer", 1),
      subclass: "draconic_bloodline",
    });

    expect(result.isValid).toBe(false);
    expect(result.missingRequiredFields).toContain("subclassConfig");
  });

  it("accepts a valid draconic ancestry for Draconic Bloodline", () => {
    const result = validateCreationSheet({
      ...buildBaseCreationSheet("sorcerer", 1),
      subclass: "draconic_bloodline",
      subclassConfig: { draconicAncestry: "red" },
      spellcasting: buildSpellSelection("sorcerer", 4, 2),
    });

    expect(result.missingRequiredFields).not.toContain("subclassConfig");
  });

  it("rejects invalid draconic ancestry values", () => {
    const result = validateCreationSheet({
      ...buildBaseCreationSheet("sorcerer", 1),
      subclass: "draconic_bloodline",
      subclassConfig: { draconicAncestry: "shadow" },
    });

    expect(result.isValid).toBe(false);
    expect(result.missingRequiredFields).toContain("subclassConfig");
  });

  it("accepts a valid dragonborn ancestry during creation", () => {
    const result = validateCreationSheet({
      ...buildBaseCreationSheet("fighter", 1),
      race: "dragonborn",
      raceConfig: { draconicAncestry: "red" },
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

  it("rejects half-elf skill versatility choices that overlap with class skills", () => {
    const result = validateCreationSheet({
      ...buildBaseCreationSheet("guardian", 1),
      race: "half-elf",
      raceConfig: {
        halfElfAbilityChoices: ["constitution", "wisdom"],
        halfElfSkillChoices: ["animalHandling", "persuasion"],
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
