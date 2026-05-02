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

export type CreationSpellConfig = {
  minimumLevel?: number;
  cantrips: number;
  leveledSpells?: number;
  leveledMode: SpellcastingMode;
  preparationAbility?: AbilityName;
  /** @legacy Fallback for classes configured before level-aware slot progression.
   *  New classes should omit this; slots are derived from spellProgression tables. */
  levelOneSlots?: number;
  fixedCantripCanonicalKeys?: string[];
  fixedLeveledSpellCanonicalKeys?: string[];
  byLevel?: Partial<Record<number, {
    cantrips?: number;
    leveledSpells?: number;
    /** @legacy See top-level levelOneSlots. */
    levelOneSlots?: number;
    fixedCantripCanonicalKeys?: string[];
    fixedLeveledSpellCanonicalKeys?: string[];
  }>>;
};

/** @deprecated Renamed to CreationSpellConfig */
export type StartingSpellConfig = CreationSpellConfig;

export type ToolProficiencyChoiceConfig = {
  count: number;
  options: string[];
  label: string;
};

export type ClassCreationConfig = {
  fixedEquipment: string[];
  equipmentChoices: ClassEquipmentChoiceGroup[];
  startingSpells?: CreationSpellConfig;
  toolProficiencyChoices?: ToolProficiencyChoiceConfig;
};
