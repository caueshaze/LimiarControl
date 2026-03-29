import {
  getStartingSpellLimits,
  normalizeCreationSpellSelection,
} from "../utils/creationSpells";
import { getClass } from "../data/classes";
import { getBackground } from "../data/backgrounds";
import { getClassCreationConfig } from "../data/classCreation";
import {
  getRace,
  normalizeRaceState,
} from "../data/races";
import { LANGUAGE_CHOICE_SLOT } from "../data/languages";
import { createEmptySpellcasting } from "./creationAbilities";
import type {
  AbilityName,
  CharacterSheet,
  SkillName,
  SpellcastingData,
} from "../model/characterSheet.types";

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

export const buildWeaponProficiencies = (
  raceName: string,
  className: string,
  raceConfig: CharacterSheet["raceConfig"] = null,
): string[] => {
  const derivedRace = getRace(raceName, raceConfig);
  const cls = getClass(className);
  return [...new Set([...(derivedRace?.weaponProficiencies ?? []), ...(cls?.weaponProficiencies ?? [])])];
};

export const buildArmorProficiencies = (
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

export const countLanguageChoiceSlots = (
  raceName: string,
  backgroundName: string,
  raceConfig: CharacterSheet["raceConfig"] = null,
): number => {
  const race = getRace(raceName, raceConfig);
  const background = getBackground(backgroundName);
  return [...(race?.languages ?? []), ...(background?.languages ?? [])]
    .filter((entry) => entry === LANGUAGE_CHOICE_SLOT).length;
};

export const buildCreationSpellcasting = (
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

export const normalizeRaceConfigForRace = (
  raceName: string,
  raceConfig: CharacterSheet["raceConfig"],
): CharacterSheet["raceConfig"] => normalizeRaceState(raceName, raceConfig).raceConfig;
