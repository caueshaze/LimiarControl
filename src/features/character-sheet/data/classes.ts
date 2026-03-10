import type { AbilityName, SkillName } from "../model/characterSheet.types";

export type DndClass = {
  name: string;
  hitDice: string;
  primaryAbility: AbilityName[];
  savingThrows: AbilityName[];
  armorProficiencies: string[];
  weaponProficiencies: string[];
  skillChoices: SkillName[];
  skillCount: number;
  spellcastingAbility: AbilityName | null;
  startingEquipment: string[];
};

export const CLASSES: DndClass[] = [
  { name: "Barbarian", hitDice: "d12", primaryAbility: ["strength"], savingThrows: ["strength", "constitution"], armorProficiencies: ["Light", "Medium", "Shields"], weaponProficiencies: ["Simple", "Martial"], skillChoices: ["animalHandling", "athletics", "intimidation", "nature", "perception", "survival"], skillCount: 2, spellcastingAbility: null, startingEquipment: ["Greataxe", "Handaxe x2", "Explorer's Pack", "Javelin x4"] },
  { name: "Bard", hitDice: "d8", primaryAbility: ["charisma"], savingThrows: ["dexterity", "charisma"], armorProficiencies: ["Light"], weaponProficiencies: ["Simple", "Hand crossbows", "Longswords", "Rapiers", "Shortswords"], skillChoices: ["acrobatics", "animalHandling", "arcana", "athletics", "deception", "history", "insight", "intimidation", "investigation", "medicine", "nature", "perception", "performance", "persuasion", "religion", "sleightOfHand", "stealth", "survival"], skillCount: 3, spellcastingAbility: "charisma", startingEquipment: ["Rapier", "Diplomat's Pack", "Lute", "Leather Armor", "Dagger"] },
  { name: "Cleric", hitDice: "d8", primaryAbility: ["wisdom"], savingThrows: ["wisdom", "charisma"], armorProficiencies: ["Light", "Medium", "Shields"], weaponProficiencies: ["Simple"], skillChoices: ["history", "insight", "medicine", "persuasion", "religion"], skillCount: 2, spellcastingAbility: "wisdom", startingEquipment: ["Mace", "Scale Mail", "Shield", "Holy Symbol", "Priest's Pack"] },
  { name: "Druid", hitDice: "d8", primaryAbility: ["wisdom"], savingThrows: ["intelligence", "wisdom"], armorProficiencies: ["Light", "Medium", "Shields (non-metal)"], weaponProficiencies: ["Clubs", "Daggers", "Javelins", "Maces", "Quarterstaffs", "Scimitars", "Sickles", "Slings", "Spears"], skillChoices: ["arcana", "animalHandling", "insight", "medicine", "nature", "perception", "religion", "survival"], skillCount: 2, spellcastingAbility: "wisdom", startingEquipment: ["Wooden Shield", "Scimitar", "Leather Armor", "Explorer's Pack", "Druidic Focus"] },
  { name: "Fighter", hitDice: "d10", primaryAbility: ["strength", "dexterity"], savingThrows: ["strength", "constitution"], armorProficiencies: ["Light", "Medium", "Heavy", "Shields"], weaponProficiencies: ["Simple", "Martial"], skillChoices: ["acrobatics", "animalHandling", "athletics", "history", "insight", "intimidation", "perception", "survival"], skillCount: 2, spellcastingAbility: null, startingEquipment: ["Chain Mail", "Shield", "Longsword", "Light Crossbow", "Explorer's Pack"] },
  { name: "Monk", hitDice: "d8", primaryAbility: ["dexterity", "wisdom"], savingThrows: ["strength", "dexterity"], armorProficiencies: [], weaponProficiencies: ["Simple", "Shortswords"], skillChoices: ["acrobatics", "athletics", "history", "insight", "religion", "stealth"], skillCount: 2, spellcastingAbility: null, startingEquipment: ["Shortsword", "Dungeoneer's Pack", "Dart x10"] },
  { name: "Paladin", hitDice: "d10", primaryAbility: ["strength", "charisma"], savingThrows: ["wisdom", "charisma"], armorProficiencies: ["Light", "Medium", "Heavy", "Shields"], weaponProficiencies: ["Simple", "Martial"], skillChoices: ["athletics", "insight", "intimidation", "medicine", "persuasion", "religion"], skillCount: 2, spellcastingAbility: "charisma", startingEquipment: ["Chain Mail", "Shield", "Longsword", "Javelin x5", "Priest's Pack"] },
  { name: "Ranger", hitDice: "d10", primaryAbility: ["dexterity", "wisdom"], savingThrows: ["strength", "dexterity"], armorProficiencies: ["Light", "Medium", "Shields"], weaponProficiencies: ["Simple", "Martial"], skillChoices: ["animalHandling", "athletics", "insight", "investigation", "nature", "perception", "stealth", "survival"], skillCount: 3, spellcastingAbility: "wisdom", startingEquipment: ["Scale Mail", "Longbow", "Arrow x20", "Shortsword x2", "Explorer's Pack"] },
  { name: "Rogue", hitDice: "d8", primaryAbility: ["dexterity"], savingThrows: ["dexterity", "intelligence"], armorProficiencies: ["Light"], weaponProficiencies: ["Simple", "Hand crossbows", "Longswords", "Rapiers", "Shortswords"], skillChoices: ["acrobatics", "athletics", "deception", "insight", "intimidation", "investigation", "perception", "performance", "persuasion", "sleightOfHand", "stealth"], skillCount: 4, spellcastingAbility: null, startingEquipment: ["Rapier", "Shortbow", "Arrow x20", "Leather Armor", "Thieves' Tools", "Burglar's Pack"] },
  { name: "Sorcerer", hitDice: "d6", primaryAbility: ["charisma"], savingThrows: ["constitution", "charisma"], armorProficiencies: [], weaponProficiencies: ["Daggers", "Darts", "Slings", "Quarterstaffs", "Light crossbows"], skillChoices: ["arcana", "deception", "insight", "intimidation", "persuasion", "religion"], skillCount: 2, spellcastingAbility: "charisma", startingEquipment: ["Light Crossbow", "Dagger x2", "Arcane Focus", "Dungeoneer's Pack"] },
  { name: "Warlock", hitDice: "d8", primaryAbility: ["charisma"], savingThrows: ["wisdom", "charisma"], armorProficiencies: ["Light"], weaponProficiencies: ["Simple"], skillChoices: ["arcana", "deception", "history", "intimidation", "investigation", "nature", "religion"], skillCount: 2, spellcastingAbility: "charisma", startingEquipment: ["Leather Armor", "Simple Weapon", "Light Crossbow", "Arcane Focus", "Scholar's Pack"] },
  { name: "Wizard", hitDice: "d6", primaryAbility: ["intelligence"], savingThrows: ["intelligence", "wisdom"], armorProficiencies: [], weaponProficiencies: ["Daggers", "Darts", "Slings", "Quarterstaffs", "Light crossbows"], skillChoices: ["arcana", "history", "insight", "investigation", "medicine", "religion"], skillCount: 2, spellcastingAbility: "intelligence", startingEquipment: ["Quarterstaff", "Arcane Focus", "Spellbook", "Scholar's Pack"] },
];

export const getClass = (name: string): DndClass | undefined =>
  CLASSES.find((c) => c.name === name);
