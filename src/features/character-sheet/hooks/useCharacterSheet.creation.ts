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
import {
  getRace,
  getRaceFixedToolProficiencies,
  normalizeRaceState,
} from "../data/races";
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
  raceConfig: CharacterSheet["raceConfig"] = null,
) => {
  const race = getRace(raceName, raceConfig);
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
  raceConfig: CharacterSheet["raceConfig"] = null,
) => {
  const race = getRace(raceName, raceConfig);
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
  previousRaceConfig: CharacterSheet["raceConfig"] = null,
  nextRaceConfig: CharacterSheet["raceConfig"] = null,
) =>
  applyRaceBonusesToAbilities(
    stripRaceBonusesFromAbilities(abilities, previousRaceName, previousRaceConfig),
    nextRaceName,
    nextRaceConfig,
  );

export const buildCreationSkillProficiencies = (
  current: CharacterSheet["skillProficiencies"],
  backgroundName: string,
  classChoices: SkillName[],
  expertiseChoices: SkillName[] = [],
  raceFixedSkills: SkillName[] = [],
) => {
  const next = { ...current };
  for (const key of Object.keys(next) as SkillName[]) next[key] = 0;
  const bg = getBackground(backgroundName);
  bg?.skillProficiencies.forEach((skill) => { next[skill] = 1; });
  raceFixedSkills.forEach((skill) => { if (next[skill] === 0) next[skill] = 1; });
  classChoices.forEach((skill) => { if (next[skill] === 0) next[skill] = 1; });
  // Expertise only applies to already-proficient skills
  expertiseChoices.forEach((skill) => { if (next[skill] === 1) next[skill] = 2; });
  return next;
};

const buildWeaponProficiencies = (
  raceName: string,
  className: string,
  raceConfig: CharacterSheet["raceConfig"] = null,
): string[] => {
  const derivedRace = getRace(raceName, raceConfig);
  const cls = getClass(className);
  return [...new Set([...(derivedRace?.weaponProficiencies ?? []), ...(cls?.weaponProficiencies ?? [])])];
};

const buildArmorProficiencies = (
  raceName: string,
  className: string,
  raceConfig: CharacterSheet["raceConfig"] = null,
): string[] => {
  const race = getRace(raceName, raceConfig);
  const cls = getClass(className);
  return [...new Set([...(race?.armorProficiencies ?? []), ...(cls?.armorProficiencies ?? [])])];
};

export const deriveLanguages = (
  raceName: string,
  backgroundName: string,
  languageChoices: string[] = [],
  raceConfig: CharacterSheet["raceConfig"] = null,
): string[] => {
  const race = getRace(raceName, raceConfig);
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

const countLanguageChoiceSlots = (
  raceName: string,
  backgroundName: string,
  raceConfig: CharacterSheet["raceConfig"] = null,
): number => {
  const race = getRace(raceName, raceConfig);
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

export const mergeToolProficiencies = (bgTools: string[], classTools: string[], raceTools: string[] = []): string[] => {
  const unique = new Set([...bgTools, ...raceTools, ...classTools]);
  return [...unique];
};

const normalizeRaceConfigForRace = (
  raceName: string,
  raceConfig: CharacterSheet["raceConfig"],
): CharacterSheet["raceConfig"] => normalizeRaceState(raceName, raceConfig).raceConfig;

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
      expertiseChoices: [],
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
  const raceFixedSkills = getRace(sheet.race, sheet.raceConfig)?.skillProficiencies ?? [];
  const skillProficiencies = buildCreationSkillProficiencies(sheet.skillProficiencies, sheet.background, trimmedChoices, [], raceFixedSkills);
  const maxHP = computeMaxHpAtLevel(cls.hitDice, sheet.level, sheet.abilities.constitution);

  return {
    ...sheet,
    class: className,
    subclass: null,
    subclassConfig: null,
    fightingStyle: null,
    expertiseChoices: [],
    classSkillChoices: trimmedChoices,
    classEquipmentSelections,
    skillProficiencies,
    savingThrowProficiencies,
    armorProficiencies: buildArmorProficiencies(sheet.race, className, sheet.raceConfig),
    weaponProficiencies: buildWeaponProficiencies(sheet.race, className, sheet.raceConfig),
    classToolProficiencyChoices: [],
    toolProficiencies: mergeToolProficiencies(getBackground(sheet.background)?.toolProficiencies ?? [], [], [
      ...getRaceFixedToolProficiencies(sheet.race, sheet.raceConfig),
      ...sheet.raceToolProficiencyChoices,
    ]),
    languages: deriveLanguages(sheet.race, sheet.background, sheet.languageChoices, sheet.raceConfig),
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
  const nextBackgroundId = bg?.id ?? backgroundName;
  const classTools = sheet.classToolProficiencyChoices;
  const raceFixedSkills = getRace(sheet.race, sheet.raceConfig)?.skillProficiencies ?? [];
  const toolProficiencies = mergeToolProficiencies(bg?.toolProficiencies ?? [], classTools, [
    ...getRaceFixedToolProficiencies(sheet.race, sheet.raceConfig),
    ...sheet.raceToolProficiencyChoices,
  ]);
  const skillProficiencies = buildCreationSkillProficiencies(
    sheet.skillProficiencies,
    nextBackgroundId,
    sheet.classSkillChoices,
    sheet.expertiseChoices,
    raceFixedSkills,
  );
  const loadout = buildCreationLoadout(sheet.class, nextBackgroundId, sheet.classEquipmentSelections);

  return {
    ...sheet,
    background: nextBackgroundId,
    skillProficiencies,
    toolProficiencies,
    languages: deriveLanguages(sheet.race, nextBackgroundId, sheet.languageChoices, sheet.raceConfig),
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
  const normalizedRace = normalizeRaceState(raceName, sheet.raceConfig);
  const nextRaceName = normalizedRace.raceId;
  const nextRaceConfig = normalizeRaceConfigForRace(nextRaceName, normalizedRace.raceConfig);
  const race = getRace(nextRaceName, nextRaceConfig);
  const abilities = applyRaceBonusSwap(sheet.abilities, sheet.race, nextRaceName, sheet.raceConfig, nextRaceConfig);
  const cls = getClass(sheet.class);
  const maxHP = cls ? computeMaxHpAtLevel(cls.hitDice, sheet.level, abilities.constitution) : sheet.maxHP;
  const totalLanguageSlots = countLanguageChoiceSlots(nextRaceName, sheet.background, nextRaceConfig);
  const nextLanguageChoices = sheet.languageChoices.slice(0, totalLanguageSlots);

  // Race tool choices: keep only those still valid for the new race
  const newRaceToolOptions = race?.toolProficiencyChoices?.options ?? [];
  const nextRaceToolChoices = sheet.raceToolProficiencyChoices.filter((t) => newRaceToolOptions.includes(t));

  const raceFixedSkills = race?.skillProficiencies ?? [];
  const skillProficiencies = buildCreationSkillProficiencies(
    sheet.skillProficiencies,
    sheet.background,
    sheet.classSkillChoices,
    sheet.expertiseChoices,
    raceFixedSkills,
  );

  return {
    ...sheet,
    race: nextRaceName,
    abilities,
    speedMeters: race?.speedMeters ?? 0,
    maxHP,
    currentHP: cls ? maxHP : sheet.currentHP,
    languages: deriveLanguages(nextRaceName, sheet.background, nextLanguageChoices, nextRaceConfig),
    languageChoices: nextLanguageChoices,
    raceConfig: nextRaceConfig,
    skillProficiencies,
    weaponProficiencies: buildWeaponProficiencies(nextRaceName, sheet.class, nextRaceConfig),
    armorProficiencies: buildArmorProficiencies(nextRaceName, sheet.class, nextRaceConfig),
    raceToolProficiencyChoices: nextRaceToolChoices,
    toolProficiencies: mergeToolProficiencies(
      getBackground(sheet.background)?.toolProficiencies ?? [],
      sheet.classToolProficiencyChoices,
      [...getRaceFixedToolProficiencies(nextRaceName, nextRaceConfig), ...nextRaceToolChoices],
    ),
    spellcasting: normalizeCreationSpellSelection(
      sheet.spellcasting,
      sheet.class,
      abilities,
      sheet.level,
      campaignId,
    ),
  };
};

export const normalizeCreationAfterRaceConfigChange = (
  sheet: CharacterSheet,
  nextRaceConfig: CharacterSheet["raceConfig"],
  campaignId?: string | null,
): CharacterSheet => {
  const normalizedRaceConfig = normalizeRaceConfigForRace(sheet.race, nextRaceConfig);
  const race = getRace(sheet.race, normalizedRaceConfig);
  const abilities = applyRaceBonusSwap(
    sheet.abilities,
    sheet.race,
    sheet.race,
    sheet.raceConfig,
    normalizedRaceConfig,
  );
  const cls = getClass(sheet.class);
  const maxHP = cls ? computeMaxHpAtLevel(cls.hitDice, sheet.level, abilities.constitution) : sheet.maxHP;
  const totalLanguageSlots = countLanguageChoiceSlots(sheet.race, sheet.background, normalizedRaceConfig);
  const nextLanguageChoices = sheet.languageChoices.slice(0, totalLanguageSlots);
  const raceFixedSkills = race?.skillProficiencies ?? [];
  const skillProficiencies = buildCreationSkillProficiencies(
    sheet.skillProficiencies,
    sheet.background,
    sheet.classSkillChoices,
    sheet.expertiseChoices,
    raceFixedSkills,
  );

  return {
    ...sheet,
    abilities,
    maxHP,
    currentHP: cls ? maxHP : sheet.currentHP,
    languages: deriveLanguages(sheet.race, sheet.background, nextLanguageChoices, normalizedRaceConfig),
    languageChoices: nextLanguageChoices,
    raceConfig: normalizedRaceConfig,
    skillProficiencies,
    weaponProficiencies: buildWeaponProficiencies(sheet.race, sheet.class, normalizedRaceConfig),
    armorProficiencies: buildArmorProficiencies(sheet.race, sheet.class, normalizedRaceConfig),
    toolProficiencies: mergeToolProficiencies(
      getBackground(sheet.background)?.toolProficiencies ?? [],
      sheet.classToolProficiencyChoices,
      [...getRaceFixedToolProficiencies(sheet.race, normalizedRaceConfig), ...sheet.raceToolProficiencyChoices],
    ),
    spellcasting: normalizeCreationSpellSelection(
      sheet.spellcasting,
      sheet.class,
      abilities,
      sheet.level,
      campaignId,
    ),
  };
};
