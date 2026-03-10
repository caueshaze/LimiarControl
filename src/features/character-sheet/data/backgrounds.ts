import type { SkillName } from "../model/characterSheet.types";

export type Background = {
  name: string;
  skillProficiencies: SkillName[];
  toolProficiencies: string[];
  languages: string[];
  feature: string;
  startingEquipment: string[];
};

export const BACKGROUNDS: Background[] = [
  { name: "Acolyte", skillProficiencies: ["insight", "religion"], toolProficiencies: [], languages: ["Choice: Extra Language", "Choice: Extra Language"], feature: "Shelter of the Faithful", startingEquipment: ["Holy symbol", "Prayer book", "5 sticks of incense", "Vestments", "Common clothes", "15 GP"] },
  { name: "Charlatan", skillProficiencies: ["deception", "sleightOfHand"], toolProficiencies: ["Disguise kit", "Forgery kit"], languages: [], feature: "False Identity", startingEquipment: ["Fine clothes", "Disguise kit", "Con tools", "15 GP"] },
  { name: "Criminal", skillProficiencies: ["deception", "stealth"], toolProficiencies: ["Thieves' tools"], languages: [], feature: "Criminal Contact", startingEquipment: ["Crowbar", "Dark common clothes with hood", "15 GP"] },
  { name: "Entertainer", skillProficiencies: ["acrobatics", "performance"], toolProficiencies: ["Disguise kit", "Musical instrument"], languages: [], feature: "By Popular Demand", startingEquipment: ["Musical instrument", "Favor of an admirer", "Costume", "15 GP"] },
  { name: "Folk Hero", skillProficiencies: ["animalHandling", "survival"], toolProficiencies: ["Artisan's tools", "Vehicles (land)"], languages: [], feature: "Rustic Hospitality", startingEquipment: ["Artisan's tools", "Shovel", "Iron pot", "Common clothes", "10 GP"] },
  { name: "Guild Artisan", skillProficiencies: ["insight", "persuasion"], toolProficiencies: ["Artisan's tools"], languages: ["Choice: Extra Language"], feature: "Guild Membership", startingEquipment: ["Artisan's tools", "Letter of introduction", "Traveler's clothes", "15 GP"] },
  { name: "Hermit", skillProficiencies: ["medicine", "religion"], toolProficiencies: ["Herbalism kit"], languages: ["Choice: Extra Language"], feature: "Discovery", startingEquipment: ["Scroll case", "Winter blanket", "Common clothes", "Herbalism kit", "5 GP"] },
  { name: "Noble", skillProficiencies: ["history", "persuasion"], toolProficiencies: ["Gaming set"], languages: ["Choice: Extra Language"], feature: "Position of Privilege", startingEquipment: ["Fine clothes", "Signet ring", "Scroll of pedigree", "25 GP"] },
  { name: "Outlander", skillProficiencies: ["athletics", "survival"], toolProficiencies: ["Musical instrument"], languages: ["Choice: Extra Language"], feature: "Wanderer", startingEquipment: ["Staff", "Hunting trap", "Animal trophy", "Traveler's clothes", "10 GP"] },
  { name: "Sage", skillProficiencies: ["arcana", "history"], toolProficiencies: [], languages: ["Choice: Extra Language", "Choice: Extra Language"], feature: "Researcher", startingEquipment: ["Bottle of black ink", "Quill", "Small knife", "Letter with unanswered question", "Common clothes", "10 GP"] },
  { name: "Sailor", skillProficiencies: ["athletics", "perception"], toolProficiencies: ["Navigator's tools", "Vehicles (water)"], languages: [], feature: "Ship's Passage", startingEquipment: ["Belaying pin", "50 feet of silk rope", "Lucky charm", "Common clothes", "10 GP"] },
  { name: "Soldier", skillProficiencies: ["athletics", "intimidation"], toolProficiencies: ["Gaming set", "Vehicles (land)"], languages: [], feature: "Military Rank", startingEquipment: ["Insignia of rank", "Trophy from fallen enemy", "Gaming set", "Common clothes", "10 GP"] },
  { name: "Urchin", skillProficiencies: ["sleightOfHand", "stealth"], toolProficiencies: ["Disguise kit", "Thieves' tools"], languages: [], feature: "City Secrets", startingEquipment: ["Small knife", "Map of home city", "Pet mouse", "Token from parent", "Common clothes", "10 GP"] },
];

export const getBackground = (name: string): Background | undefined =>
  BACKGROUNDS.find((b) => b.name === name);
