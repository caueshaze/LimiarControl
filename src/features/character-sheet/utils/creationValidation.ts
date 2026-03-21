import { getClass, isSubclassUnlocked } from "../data/classes";
import { getClassCreationConfig } from "../data/classCreation";
import { getRace } from "../data/races";
import { getBackground } from "../data/backgrounds";
import { LANGUAGE_CHOICE_SLOT } from "../data/languages";
import type { CharacterSheet } from "../model/characterSheet.types";
import { getStartingSpellLimits } from "./creationSpells";

export type RequiredField =
  | "name"
  | "class"
  | "subclass"
  | "race"
  | "background"
  | "alignment"
  | "playerName"
  | "classSkills"
  | "classToolProficiencies"
  | "equipmentChoices"
  | "languageChoices"
  | "cantrips"
  | "leveledSpells";

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
  if (cls && sheet.classSkillChoices.length < cls.skillCount) {
    missingRequiredFields.push("classSkills");
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
  const raceLanguages = getRace(sheet.race)?.languages ?? [];
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

    const needCantrips = selectedCantrips < spellLimits.cantrips;
    const needLeveled = selectedLevelOneSpells < spellLimits.leveledSpells;

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
