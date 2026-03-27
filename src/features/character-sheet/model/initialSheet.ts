import { nanoid } from "nanoid";
import type { CharacterSheet, ConditionName } from "./characterSheet.types";

const CONDITION_NAMES: ConditionName[] = [
  "blinded", "charmed", "deafened", "frightened", "grappled",
  "incapacitated", "invisible", "paralyzed", "petrified",
  "poisoned", "prone", "restrained", "stunned", "unconscious",
];

const emptyConditions = Object.fromEntries(
  CONDITION_NAMES.map((c) => [c, false]),
) as Record<ConditionName, boolean>;

export const INITIAL_SHEET: CharacterSheet = {
  schemaVersion: 1,

  name: "",
  class: "",
  subclass: null,
  currentWeaponId: null,
  equippedArmorItemId: null,
  level: 1,
  background: "",
  playerName: "",
  race: "",
  alignment: "",
  experiencePoints: 0,
  restState: "exploration",
  pendingLevelUp: false,
  inspiration: false,

  abilities: {
    strength: 15,
    dexterity: 14,
    constitution: 13,
    intelligence: 12,
    wisdom: 10,
    charisma: 8,
  },

  savingThrowProficiencies: {
    strength: false,
    dexterity: false,
    constitution: false,
    intelligence: false,
    wisdom: false,
    charisma: false,
  },

  skillProficiencies: {
    acrobatics: 0,
    animalHandling: 0,
    arcana: 0,
    athletics: 0,
    deception: 0,
    history: 0,
    insight: 0,
    intimidation: 0,
    investigation: 0,
    medicine: 0,
    nature: 0,
    perception: 0,
    performance: 0,
    persuasion: 0,
    religion: 0,
    sleightOfHand: 0,
    stealth: 0,
    survival: 0,
  },

  equippedArmor: { name: "None", baseAC: 0, dexCap: null, armorType: "none" },
  equippedShield: null,
  miscACBonus: 0,
  speedMeters: 0,

  maxHP: 0,
  currentHP: 0,
  tempHP: 0,

  hitDiceType: "",
  hitDiceTotal: 0,
  hitDiceRemaining: 0,

  deathSaves: { successes: 0, failures: 0 },

  weapons: [],
  inventory: [],
  currency: { copperValue: 0 },

  spellcasting: null,

  languages: [],
  toolProficiencies: [],
  weaponProficiencies: [],
  armorProficiencies: [],

  conditions: emptyConditions,

  classSkillChoices: [],
  classToolProficiencyChoices: [],
  raceToolProficiencyChoices: [],
  classEquipmentSelections: {},
  languageChoices: [],
  raceConfig: null,
  subclassConfig: null,
  fightingStyle: null,
  expertiseChoices: [],
  featuresAndTraits: "",
  notes: "",
};
