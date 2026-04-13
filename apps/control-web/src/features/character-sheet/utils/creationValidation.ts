import { getClass, getSubclassConfigFields, hasFightingStyleAtCreation, hasExpertiseAtCreation, isSubclassUnlocked } from "../data/classes";
import { getClassCreationConfig } from "../data/classCreation";
import { getRace, getRaceConfigFields, isRaceConfigValid } from "../data/races";
import { getBackground } from "../data/backgrounds";
import { LANGUAGE_CHOICE_SLOT } from "../data/languages";
import type { CharacterSheet } from "../model/characterSheet.types";
import { getFixedStartingSpellCanonicalKeys, getStartingSpellLimits } from "./creationSpells";
import { hasBlockedRaceConfigSkillSelections } from "./raceConfigSkills";

export type RequiredField =
  | "name"
  | "class"
  | "subclass"
  | "subclassConfig"
  | "race"
  | "background"
  | "alignment"
  | "playerName"
  | "fightingStyle"
  | "classSkills"
  | "classToolProficiencies"
  | "raceToolProficiency"
  | "equipmentChoices"
  | "languageChoices"
  | "raceConfig"
  | "cantrips"
  | "leveledSpells"
  | "expertise";

export type CreationValidationResult = {
  isValid: boolean;
  /** Stable field identifiers — use for form highlighting and i18n display */
  missingRequiredFields: RequiredField[];
  /** Extra detail for spell counts, populated when cantrips/leveledSpells are missing */
  spellDetails?: {
    selectedCantrips: number;
    totalCantrips: number;
    selectedLeveled: number;
    totalLeveled: number;
  };
};

const isBlank = (value: string | null | undefined) => !value || value.trim().length === 0;

export const validateCreationSheet = (
  sheet: CharacterSheet,
): CreationValidationResult => {
  const missingRequiredFields: RequiredField[] = [];

  if (isBlank(sheet.name)) missingRequiredFields.push("name");
  if (isBlank(sheet.class)) missingRequiredFields.push("class");
  if (isBlank(sheet.race)) missingRequiredFields.push("race");
  if (isBlank(sheet.background)) missingRequiredFields.push("background");
  if (isBlank(sheet.alignment)) missingRequiredFields.push("alignment");
  if (isBlank(sheet.playerName)) missingRequiredFields.push("playerName");

  const cls = getClass(sheet.class);
  if (cls && isSubclassUnlocked(cls, sheet.level) && isBlank(sheet.subclass)) {
    missingRequiredFields.push("subclass");
  }
  if (sheet.subclass) {
    const configFields = getSubclassConfigFields(sheet.class, sheet.subclass);
    const missingConfig = configFields.some((field) => {
      const value = sheet.subclassConfig?.[field.key];
      if (!value) return true;
      return !field.options.some((option) => option.id === value);
    });
    if (missingConfig) missingRequiredFields.push("subclassConfig");
  }
  if (cls && hasFightingStyleAtCreation(cls, sheet.level) && !sheet.fightingStyle) {
    missingRequiredFields.push("fightingStyle");
  }
  if (cls && sheet.classSkillChoices.length < cls.skillCount) {
    missingRequiredFields.push("classSkills");
  }
  if (cls && hasExpertiseAtCreation(cls, sheet.level) && sheet.expertiseChoices.length < cls.expertiseCount) {
    missingRequiredFields.push("expertise");
  }

  // Race tool proficiency choice validation (e.g. Dwarf: artisan tool)
  const raceData = getRace(sheet.race, sheet.raceConfig);
  const raceConfigFields = getRaceConfigFields(sheet.race);
  if (raceConfigFields.length > 0 && !isRaceConfigValid(sheet.race, sheet.raceConfig)) {
    missingRequiredFields.push("raceConfig");
  }
  if (
    sheet.race === "half-elf" &&
    hasBlockedRaceConfigSkillSelections(sheet, "halfElfSkillChoices") &&
    !missingRequiredFields.includes("raceConfig")
  ) {
    missingRequiredFields.push("raceConfig");
  }
  if (raceData?.toolProficiencyChoices) {
    if (sheet.raceToolProficiencyChoices.length < raceData.toolProficiencyChoices.count) {
      missingRequiredFields.push("raceToolProficiency");
    }
  }

  // Tool proficiency choice validation (e.g. Bard: 3 musical instruments)
  const creationConfig = getClassCreationConfig(sheet.class);
  if (creationConfig?.toolProficiencyChoices) {
    const needed = creationConfig.toolProficiencyChoices.count;
    if (sheet.classToolProficiencyChoices.length < needed) {
      missingRequiredFields.push("classToolProficiencies");
    }
  }

  // Equipment choice validation: every choice group must have a selection
  if (creationConfig) {
    const hasUnselectedGroup = creationConfig.equipmentChoices.some((group) => {
      if (group.options.length === 0) return false;
      const selection = sheet.classEquipmentSelections[group.id];
      if (!selection) return true;
      return !group.options.some((opt) => opt.id === selection);
    });
    if (hasUnselectedGroup) {
      missingRequiredFields.push("equipmentChoices");
    }
  }

  // Language choice validation: all choice slots must be filled
  const raceLanguages = getRace(sheet.race, sheet.raceConfig)?.languages ?? [];
  const bgLanguages = getBackground(sheet.background)?.languages ?? [];
  const totalLanguageSlots = [...raceLanguages, ...bgLanguages]
    .filter((e) => e === LANGUAGE_CHOICE_SLOT).length;
  if (totalLanguageSlots > 0) {
    const filledSlots = sheet.languageChoices
      .slice(0, totalLanguageSlots)
      .filter((l) => l.trim().length > 0).length;
    if (filledSlots < totalLanguageSlots) {
      missingRequiredFields.push("languageChoices");
    }
  }

  let spellDetails: CreationValidationResult["spellDetails"];
  const spellLimits = getStartingSpellLimits(sheet.class, sheet.abilities, sheet.level);
  if (spellLimits) {
    const selectedCantrips = sheet.spellcasting?.spells.filter((spell) => spell.level === 0).length ?? 0;
    const selectedLevelOneSpells = sheet.spellcasting?.spells.filter((spell) => spell.level === 1).length ?? 0;
    const selectedSpellKeys = new Set(
      (sheet.spellcasting?.spells ?? [])
        .map((spell) => spell.canonicalKey?.toLowerCase())
        .filter((spellKey): spellKey is string => Boolean(spellKey)),
    );
    const missingRequiredSpells = getFixedStartingSpellCanonicalKeys(sheet.class, sheet.level)
      .some((spellKey) => !selectedSpellKeys.has(spellKey.toLowerCase()));

    const needCantrips = selectedCantrips < spellLimits.cantrips;
    const needLeveled = selectedLevelOneSpells < spellLimits.leveledSpells || missingRequiredSpells;

    if (needCantrips) missingRequiredFields.push("cantrips");
    if (needLeveled) missingRequiredFields.push("leveledSpells");

    if (needCantrips || needLeveled) {
      spellDetails = {
        selectedCantrips,
        totalCantrips: spellLimits.cantrips,
        selectedLeveled: selectedLevelOneSpells,
        totalLeveled: spellLimits.leveledSpells,
      };
    }
  }

  return {
    isValid: missingRequiredFields.length === 0,
    missingRequiredFields,
    spellDetails,
  };
};
