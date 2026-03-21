import type { AbilityName, SpellcastingMode } from "../model/characterSheet.types";

export type ClassEquipmentOption = {
  id: string;
  label: string;
  items: string[];
};

export type ClassEquipmentChoiceGroup = {
  id: string;
  label: string;
  options: ClassEquipmentOption[];
};

/** @deprecated Use `SpellcastingMode` from characterSheet.types.ts */
export type StartingSpellMode = SpellcastingMode;

export type StartingSpellConfig = {
  cantrips: number;
  leveledSpells: number;
  leveledMode: SpellcastingMode;
  preparationAbility?: AbilityName;
  levelOneSlots?: number;
};

export type ToolProficiencyChoiceConfig = {
  count: number;
  options: string[];
  label: string;
};

export type ClassCreationConfig = {
  fixedEquipment: string[];
  equipmentChoices: ClassEquipmentChoiceGroup[];
  startingSpells?: StartingSpellConfig;
  toolProficiencyChoices?: ToolProficiencyChoiceConfig;
};
