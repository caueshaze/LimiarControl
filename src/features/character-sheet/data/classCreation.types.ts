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
  minimumLevel?: number;
  cantrips: number;
  leveledSpells: number;
  leveledMode: SpellcastingMode;
  preparationAbility?: AbilityName;
  levelOneSlots?: number;
  fixedCantripCanonicalKeys?: string[];
  fixedLeveledSpellCanonicalKeys?: string[];
  byLevel?: Partial<Record<number, {
    cantrips?: number;
    leveledSpells?: number;
    levelOneSlots?: number;
    fixedCantripCanonicalKeys?: string[];
    fixedLeveledSpellCanonicalKeys?: string[];
  }>>;
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
