import type { AbilityName, SkillName } from "../model/characterSheet.types";
import { describeDefaultClassStartingEquipment } from "./classCreation";

export type DndClass = {
  id: string;
  name: string;
  hitDice: string;
  primaryAbility: AbilityName[];
  savingThrows: AbilityName[];
  armorProficiencies: string[];
  weaponProficiencies: string[];
  skillChoices: SkillName[];
  skillCount: number;
  spellcastingAbility: AbilityName | null;
  // Derived preview only. Character creation uses classCreation.ts as source of truth.
  startingEquipment: string[];
};

const CLASS_DEFINITIONS: Omit<DndClass, "startingEquipment">[] = [
  { id: "barbarian", name: "Bárbaro", hitDice: "d12", primaryAbility: ["strength"], savingThrows: ["strength", "constitution"], armorProficiencies: ["Leve", "Média", "Escudos"], weaponProficiencies: ["Simples", "Marciais"], skillChoices: ["animalHandling", "athletics", "intimidation", "nature", "perception", "survival"], skillCount: 2, spellcastingAbility: null },
  { id: "bard", name: "Bardo", hitDice: "d8", primaryAbility: ["charisma"], savingThrows: ["dexterity", "charisma"], armorProficiencies: ["Leve"], weaponProficiencies: ["Simples", "Bestas de mão", "Espadas longas", "Rapieiras", "Espadas curtas"], skillChoices: ["acrobatics", "animalHandling", "arcana", "athletics", "deception", "history", "insight", "intimidation", "investigation", "medicine", "nature", "perception", "performance", "persuasion", "religion", "sleightOfHand", "stealth", "survival"], skillCount: 3, spellcastingAbility: "charisma" },
  { id: "cleric", name: "Clérigo", hitDice: "d8", primaryAbility: ["wisdom"], savingThrows: ["wisdom", "charisma"], armorProficiencies: ["Leve", "Média", "Escudos"], weaponProficiencies: ["Simples"], skillChoices: ["history", "insight", "medicine", "persuasion", "religion"], skillCount: 2, spellcastingAbility: "wisdom" },
  { id: "druid", name: "Druida", hitDice: "d8", primaryAbility: ["wisdom"], savingThrows: ["intelligence", "wisdom"], armorProficiencies: ["Leve", "Média", "Escudos (não-metálicos)"], weaponProficiencies: ["Clavas", "Adagas", "Dardos de arremesso", "Maças", "Cajados", "Cimitarras", "Foices", "Fundas", "Lanças"], skillChoices: ["arcana", "animalHandling", "insight", "medicine", "nature", "perception", "religion", "survival"], skillCount: 2, spellcastingAbility: "wisdom" },
  { id: "fighter", name: "Guerreiro", hitDice: "d10", primaryAbility: ["strength", "dexterity"], savingThrows: ["strength", "constitution"], armorProficiencies: ["Leve", "Média", "Pesada", "Escudos"], weaponProficiencies: ["Simples", "Marciais"], skillChoices: ["acrobatics", "animalHandling", "athletics", "history", "insight", "intimidation", "perception", "survival"], skillCount: 2, spellcastingAbility: null },
  { id: "monk", name: "Monge", hitDice: "d8", primaryAbility: ["dexterity", "wisdom"], savingThrows: ["strength", "dexterity"], armorProficiencies: [], weaponProficiencies: ["Simples", "Espadas curtas"], skillChoices: ["acrobatics", "athletics", "history", "insight", "religion", "stealth"], skillCount: 2, spellcastingAbility: null },
  { id: "paladin", name: "Paladino", hitDice: "d10", primaryAbility: ["strength", "charisma"], savingThrows: ["wisdom", "charisma"], armorProficiencies: ["Leve", "Média", "Pesada", "Escudos"], weaponProficiencies: ["Simples", "Marciais"], skillChoices: ["athletics", "insight", "intimidation", "medicine", "persuasion", "religion"], skillCount: 2, spellcastingAbility: "charisma" },
  { id: "ranger", name: "Patrulheiro", hitDice: "d10", primaryAbility: ["dexterity", "wisdom"], savingThrows: ["strength", "dexterity"], armorProficiencies: ["Leve", "Média", "Escudos"], weaponProficiencies: ["Simples", "Marciais"], skillChoices: ["animalHandling", "athletics", "insight", "investigation", "nature", "perception", "stealth", "survival"], skillCount: 3, spellcastingAbility: "wisdom" },
  { id: "rogue", name: "Ladino", hitDice: "d8", primaryAbility: ["dexterity"], savingThrows: ["dexterity", "intelligence"], armorProficiencies: ["Leve"], weaponProficiencies: ["Simples", "Bestas de mão", "Espadas longas", "Rapieiras", "Espadas curtas"], skillChoices: ["acrobatics", "athletics", "deception", "insight", "intimidation", "investigation", "perception", "performance", "persuasion", "sleightOfHand", "stealth"], skillCount: 4, spellcastingAbility: null },
  { id: "sorcerer", name: "Feiticeiro", hitDice: "d6", primaryAbility: ["charisma"], savingThrows: ["constitution", "charisma"], armorProficiencies: [], weaponProficiencies: ["Adagas", "Dardos", "Fundas", "Cajados", "Bestas leves"], skillChoices: ["arcana", "deception", "insight", "intimidation", "persuasion", "religion"], skillCount: 2, spellcastingAbility: "charisma" },
  { id: "warlock", name: "Bruxo", hitDice: "d8", primaryAbility: ["charisma"], savingThrows: ["wisdom", "charisma"], armorProficiencies: ["Leve"], weaponProficiencies: ["Simples"], skillChoices: ["arcana", "deception", "history", "intimidation", "investigation", "nature", "religion"], skillCount: 2, spellcastingAbility: "charisma" },
  { id: "wizard", name: "Mago", hitDice: "d6", primaryAbility: ["intelligence"], savingThrows: ["intelligence", "wisdom"], armorProficiencies: [], weaponProficiencies: ["Adagas", "Dardos", "Fundas", "Cajados", "Bestas leves"], skillChoices: ["arcana", "history", "insight", "investigation", "medicine", "religion"], skillCount: 2, spellcastingAbility: "intelligence" },
];

export const CLASSES: DndClass[] = CLASS_DEFINITIONS.map((entry) => ({
  ...entry,
  startingEquipment: describeDefaultClassStartingEquipment(entry.id),
}));

export const getClass = (id: string): DndClass | undefined =>
  CLASSES.find((c) => c.id === id);
