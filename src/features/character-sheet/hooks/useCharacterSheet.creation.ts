import {
  computeMaxHpAtLevel,
} from "../utils/calculations";
import {
  getStartingSpellLimits,
  normalizeCreationSpellSelection,
} from "../utils/creationSpells";
import { getClass } from "../data/classes";
import { getBackground } from "../data/backgrounds";
import { getClassCreationConfig } from "../data/classCreation";
import { getRace } from "../data/races";
import { LANGUAGE_CHOICE_SLOT } from "../data/languages";
import {
  buildCreationLoadout,
  getInitialClassEquipmentSelections,
} from "../utils/creationEquipment";
import type {
  AbilityName,
  CharacterSheet,
  SkillName,
  SpellcastingData,
} from "../model/characterSheet.types";

const clampAbilityScore = (value: number) => Math.max(0, Math.min(30, value));

const ABILITY_ORDER: AbilityName[] = [
  "strength",
  "dexterity",
  "constitution",
  "intelligence",
  "wisdom",
  "charisma",
];

const EMPTY_SAVES: CharacterSheet["savingThrowProficiencies"] = {
  strength: false,
  dexterity: false,
  constitution: false,
  intelligence: false,
  wisdom: false,
  charisma: false,
};

export const createEmptySpellcasting = (
  ability: AbilityName = "intelligence",
  mode: SpellcastingData["mode"] = "known",
): SpellcastingData => ({
  ability,
  mode,
  slots: Object.fromEntries(Array.from({ length: 9 }, (_, i) => [i + 1, { max: 0, used: 0 }])),
  spells: [],
});

export const applyRaceBonusesToAbilities = (
  abilities: CharacterSheet["abilities"],
  raceName: string,
) => {
  const race = getRace(raceName);
  if (!race) return { ...abilities };
  const next = { ...abilities };
  for (const [key, bonus] of Object.entries(race.abilityBonuses)) {
    const abilityKey = key as AbilityName;
    next[abilityKey] = clampAbilityScore((next[abilityKey] ?? 0) + (bonus ?? 0));
  }
  return next;
};

export const stripRaceBonusesFromAbilities = (
  abilities: CharacterSheet["abilities"],
  raceName: string,
) => {
  const race = getRace(raceName);
  if (!race) return { ...abilities };
  const next = { ...abilities };
  for (const [key, bonus] of Object.entries(race.abilityBonuses)) {
    const abilityKey = key as AbilityName;
    next[abilityKey] = clampAbilityScore((next[abilityKey] ?? 0) - (bonus ?? 0));
  }
  return next;
};

export const applyRaceBonusSwap = (
  abilities: CharacterSheet["abilities"],
  previousRaceName: string,
  nextRaceName: string,
) =>
  applyRaceBonusesToAbilities(
    stripRaceBonusesFromAbilities(abilities, previousRaceName),
    nextRaceName,
  );

export const buildCreationSkillProficiencies = (
  current: CharacterSheet["skillProficiencies"],
  backgroundName: string,
  classChoices: SkillName[],
) => {
  const next = { ...current };
  for (const key of Object.keys(next) as SkillName[]) next[key] = 0;
  const bg = getBackground(backgroundName);
  bg?.skillProficiencies.forEach((skill) => { next[skill] = 1; });
  classChoices.forEach((skill) => { if (next[skill] === 0) next[skill] = 1; });
  return next;
};

export const deriveLanguages = (
  raceName: string,
  backgroundName: string,
  languageChoices: string[] = [],
): string[] => {
  const race = getRace(raceName);
  const background = getBackground(backgroundName);
  const allEntries = [...(race?.languages ?? []), ...(background?.languages ?? [])];

  const fixed: string[] = [];
  let choiceSlotIndex = 0;
  for (const entry of allEntries) {
    if (entry === LANGUAGE_CHOICE_SLOT) {
      const chosen = languageChoices[choiceSlotIndex];
      if (chosen) fixed.push(chosen);
      choiceSlotIndex++;
    } else {
      fixed.push(entry);
    }
  }

  return [...new Set(fixed)];
};

const countLanguageChoiceSlots = (raceName: string, backgroundName: string): number => {
  const race = getRace(raceName);
  const background = getBackground(backgroundName);
  return [...(race?.languages ?? []), ...(background?.languages ?? [])]
    .filter((entry) => entry === LANGUAGE_CHOICE_SLOT).length;
};

const buildCreationSpellcasting = (
  className: string,
  spellcastingAbility: AbilityName | null,
  abilities: CharacterSheet["abilities"],
  level: number,
  existing: SpellcastingData | null,
  campaignId?: string | null,
) => {
  const limits = getStartingSpellLimits(className, abilities, level);
  if (!limits || !spellcastingAbility) return null;
  const creationConfig = getClassCreationConfig(className);
  return normalizeCreationSpellSelection(
    existing ?? createEmptySpellcasting(
      spellcastingAbility,
      creationConfig?.startingSpells?.leveledMode ?? "known",
    ),
    className,
    abilities,
    level,
    campaignId,
  );
};

export const mergeToolProficiencies = (bgTools: string[], classTools: string[]): string[] => {
  const unique = new Set([...bgTools, ...classTools]);
  return [...unique];
};

export const normalizeCreationAfterClassChange = (
  sheet: CharacterSheet,
  className: string,
  campaignId?: string | null,
): CharacterSheet => {
  const cls = getClass(className);
  const classEquipmentSelections = getInitialClassEquipmentSelections(className);
  const loadout = buildCreationLoadout(className, sheet.background, classEquipmentSelections);
  if (!cls) {
    return {
      ...sheet,
      class: className,
      classSkillChoices: [],
      classEquipmentSelections,
      skillProficiencies: buildCreationSkillProficiencies(sheet.skillProficiencies, sheet.background, []),
      savingThrowProficiencies: { ...EMPTY_SAVES },
      armorProficiencies: [],
      weaponProficiencies: [],
      hitDiceType: "",
      hitDiceTotal: sheet.level,
      hitDiceRemaining: sheet.level,
      maxHP: 0,
      currentHP: 0,
      spellcasting: null,
      inventory: loadout.inventory,
      currency: loadout.currency,
      equippedArmor: loadout.equippedArmor,
      equippedShield: loadout.equippedShield,
      weapons: loadout.weapons,
    };
  }

  const filteredChoices = sheet.classSkillChoices.filter((skill) => cls.skillChoices.includes(skill));
  const trimmedChoices = filteredChoices.slice(0, cls.skillCount);
  const savingThrowProficiencies = { ...EMPTY_SAVES };
  cls.savingThrows.forEach((ability) => { savingThrowProficiencies[ability] = true; });
  const skillProficiencies = buildCreationSkillProficiencies(sheet.skillProficiencies, sheet.background, trimmedChoices);
  const maxHP = computeMaxHpAtLevel(cls.hitDice, sheet.level, sheet.abilities.constitution);

  return {
    ...sheet,
    class: className,
    subclass: null,
    classSkillChoices: trimmedChoices,
    classEquipmentSelections,
    skillProficiencies,
    savingThrowProficiencies,
    armorProficiencies: [...cls.armorProficiencies],
    weaponProficiencies: [...cls.weaponProficiencies],
    classToolProficiencyChoices: [],
    toolProficiencies: [...(getBackground(sheet.background)?.toolProficiencies ?? [])],
    languages: deriveLanguages(sheet.race, sheet.background, sheet.languageChoices),
    hitDiceType: cls.hitDice,
    hitDiceTotal: sheet.level,
    hitDiceRemaining: sheet.level,
    maxHP,
    currentHP: maxHP,
    spellcasting: buildCreationSpellcasting(
      className,
      cls.spellcastingAbility,
      sheet.abilities,
      sheet.level,
      null,
      campaignId,
    ),
    inventory: loadout.inventory,
    currency: loadout.currency,
    equippedArmor: loadout.equippedArmor,
    equippedShield: loadout.equippedShield,
    weapons: loadout.weapons,
  };
};

export const normalizeCreationAfterBackgroundChange = (
  sheet: CharacterSheet,
  backgroundName: string,
): CharacterSheet => {
  const bg = getBackground(backgroundName);
  const classTools = sheet.classToolProficiencyChoices;
  const toolProficiencies = mergeToolProficiencies(bg?.toolProficiencies ?? [], classTools);
  const skillProficiencies = buildCreationSkillProficiencies(
    sheet.skillProficiencies,
    backgroundName,
    sheet.classSkillChoices,
  );
  const loadout = buildCreationLoadout(sheet.class, backgroundName, sheet.classEquipmentSelections);

  return {
    ...sheet,
    background: backgroundName,
    skillProficiencies,
    toolProficiencies,
    languages: deriveLanguages(sheet.race, backgroundName, sheet.languageChoices),
    inventory: loadout.inventory,
    currency: loadout.currency,
    equippedArmor: loadout.equippedArmor,
    equippedShield: loadout.equippedShield,
    weapons: loadout.weapons,
  };
};

export const normalizeCreationAfterRaceChange = (
  sheet: CharacterSheet,
  raceName: string,
  campaignId?: string | null,
): CharacterSheet => {
  const race = getRace(raceName);
  const abilities = applyRaceBonusSwap(sheet.abilities, sheet.race, raceName);
  const cls = getClass(sheet.class);
  const maxHP = cls ? computeMaxHpAtLevel(cls.hitDice, sheet.level, abilities.constitution) : sheet.maxHP;
  const totalLanguageSlots = countLanguageChoiceSlots(raceName, sheet.background);
  const nextLanguageChoices = sheet.languageChoices.slice(0, totalLanguageSlots);

  return {
    ...sheet,
    race: raceName,
    abilities,
    speed: race?.speed ?? 0,
    maxHP,
    currentHP: cls ? maxHP : sheet.currentHP,
    languages: deriveLanguages(raceName, sheet.background, nextLanguageChoices),
    languageChoices: nextLanguageChoices,
    spellcasting: normalizeCreationSpellSelection(
      sheet.spellcasting,
      sheet.class,
      abilities,
      sheet.level,
      campaignId,
    ),
  };
};
