import { getBackground } from "../data/backgrounds";
import { getRace } from "../data/races";
import type { CharacterSheet, SkillName } from "../model/characterSheet.types";

export const getBlockedRaceConfigSkills = (
  sheet: CharacterSheet,
  fieldKey: "halfElfSkillChoices",
): Set<SkillName> => {
  if (fieldKey !== "halfElfSkillChoices" || sheet.race !== "half-elf") {
    return new Set();
  }

  const backgroundSkills = getBackground(sheet.background)?.skillProficiencies ?? [];
  const raceWithoutVersatilitySkills = getRace(sheet.race, {
    ...(sheet.raceConfig ?? {}),
    halfElfSkillChoices: [],
  })?.skillProficiencies ?? [];

  return new Set([
    ...backgroundSkills,
    ...sheet.classSkillChoices,
    ...raceWithoutVersatilitySkills,
  ]);
};

export const hasBlockedRaceConfigSkillSelections = (
  sheet: CharacterSheet,
  fieldKey: "halfElfSkillChoices",
): boolean => {
  const selectedSkills = sheet.raceConfig?.[fieldKey] ?? [];
  if (!Array.isArray(selectedSkills) || selectedSkills.length === 0) {
    return false;
  }

  const blockedSkills = getBlockedRaceConfigSkills(sheet, fieldKey);
  return selectedSkills.some((skill) => blockedSkills.has(skill));
};
