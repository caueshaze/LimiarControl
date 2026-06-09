import type { LocaleKey } from "../../../shared/i18n";
import type { RequiredField } from "./creationValidation";

export const REQUIRED_FIELD_LABEL_KEY: Record<RequiredField, LocaleKey> = {
  name: "sheet.basicInfo.characterName",
  class: "sheet.basicInfo.class",
  subclass: "sheet.basicInfo.subclass",
  subclassConfig: "sheet.basicInfo.subclassConfig",
  raceConfig: "sheet.raceConfig.title",
  race: "sheet.basicInfo.race",
  background: "sheet.basicInfo.background",
  alignment: "sheet.basicInfo.alignment",
  playerName: "sheet.basicInfo.playerName",
  fightingStyle: "sheet.basicInfo.fightingStyle",
  classSkills: "sheet.skillPicker.classSkills",
  classToolProficiencies: "sheet.toolPicker.title",
  raceToolProficiency: "sheet.raceToolPicker.title",
  equipmentChoices: "sheet.creation.equipmentChoices",
  languageChoices: "sheet.languages.choiceTitle",
  cantrips: "sheet.spells.cantrip",
  leveledSpells: "sheet.spells.knownTitle",
  expertise: "sheet.expertisePicker.title",
};

export const TOTAL_REQUIRED_FIELDS = Object.keys(REQUIRED_FIELD_LABEL_KEY).length;
