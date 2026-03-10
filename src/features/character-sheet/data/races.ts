import type { AbilityName } from "../model/characterSheet.types";

export type Race = {
  name: string;
  size: "Small" | "Medium";
  darkvision: number | null;
  languages: string[];
  abilityBonuses: Partial<Record<AbilityName, number>>;
  speed: number;
  traits: string[];
};

export const RACES: Race[] = [
  { name: "Hill Dwarf", size: "Medium", darkvision: 60, languages: ["Common", "Dwarvish"], abilityBonuses: { constitution: 2, wisdom: 1 }, speed: 25, traits: ["Dwarven Resilience", "Stonecunning", "Dwarven Toughness", "Heavy Armor Speed Unchanged"] },
  { name: "Mountain Dwarf", size: "Medium", darkvision: 60, languages: ["Common", "Dwarvish"], abilityBonuses: { constitution: 2, strength: 2 }, speed: 25, traits: ["Dwarven Resilience", "Stonecunning", "Armor Proficiency", "Heavy Armor Speed Unchanged"] },
  { name: "High Elf", size: "Medium", darkvision: 60, languages: ["Common", "Elvish", "Choice: Extra Language"], abilityBonuses: { dexterity: 2, intelligence: 1 }, speed: 30, traits: ["Fey Ancestry", "Trance", "Cantrip"] },
  { name: "Wood Elf", size: "Medium", darkvision: 60, languages: ["Common", "Elvish"], abilityBonuses: { dexterity: 2, wisdom: 1 }, speed: 35, traits: ["Fey Ancestry", "Trance", "Fleet of Foot", "Mask of the Wild"] },
  { name: "Dark Elf (Drow)", size: "Medium", darkvision: 120, languages: ["Common", "Elvish"], abilityBonuses: { dexterity: 2, charisma: 1 }, speed: 30, traits: ["Fey Ancestry", "Trance", "Sunlight Sensitivity", "Drow Magic"] },
  { name: "Lightfoot Halfling", size: "Small", darkvision: null, languages: ["Common", "Halfling"], abilityBonuses: { dexterity: 2, charisma: 1 }, speed: 25, traits: ["Lucky", "Brave", "Halfling Nimbleness", "Naturally Stealthy"] },
  { name: "Stout Halfling", size: "Small", darkvision: null, languages: ["Common", "Halfling"], abilityBonuses: { dexterity: 2, constitution: 1 }, speed: 25, traits: ["Lucky", "Brave", "Halfling Nimbleness", "Stout Resilience"] },
  { name: "Human", size: "Medium", darkvision: null, languages: ["Common", "Choice: Extra Language"], abilityBonuses: { strength: 1, dexterity: 1, constitution: 1, intelligence: 1, wisdom: 1, charisma: 1 }, speed: 30, traits: ["Extra Skill"] },
  { name: "Dragonborn", size: "Medium", darkvision: null, languages: ["Common", "Draconic"], abilityBonuses: { strength: 2, charisma: 1 }, speed: 30, traits: ["Draconic Ancestry", "Breath Weapon", "Damage Resistance"] },
  { name: "Forest Gnome", size: "Small", darkvision: 60, languages: ["Common", "Gnomish"], abilityBonuses: { intelligence: 2, dexterity: 1 }, speed: 25, traits: ["Gnome Cunning", "Natural Illusionist", "Speak with Animals"] },
  { name: "Rock Gnome", size: "Small", darkvision: 60, languages: ["Common", "Gnomish"], abilityBonuses: { intelligence: 2, constitution: 1 }, speed: 25, traits: ["Gnome Cunning", "Artificer's Lore", "Tinker"] },
  { name: "Half-Elf", size: "Medium", darkvision: 60, languages: ["Common", "Elvish", "Choice: Extra Language"], abilityBonuses: { charisma: 2, dexterity: 1, wisdom: 1 }, speed: 30, traits: ["Fey Ancestry", "Skill Versatility"] },
  { name: "Half-Orc", size: "Medium", darkvision: 60, languages: ["Common", "Orc"], abilityBonuses: { strength: 2, constitution: 1 }, speed: 30, traits: ["Menacing", "Relentless Endurance", "Savage Attacks"] },
  { name: "Tiefling", size: "Medium", darkvision: 60, languages: ["Common", "Infernal"], abilityBonuses: { intelligence: 1, charisma: 2 }, speed: 30, traits: ["Hellish Resistance", "Infernal Legacy"] },
];

export const getRace = (name: string): Race | undefined =>
  RACES.find((r) => r.name === name);
