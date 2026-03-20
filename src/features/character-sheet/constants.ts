import type {
  AbilityName,
  Armor,
  ConditionName,
  SkillName,
} from "./model/characterSheet.types";

export const ABILITY_SCORE_POOL = 72;
export const ABILITY_SCORE_MIN = 0;
export const ABILITY_SCORE_MAX = 30;
export const STANDARD_ARRAY = [15, 14, 13, 12, 10, 8] as const;

// ── Abilities ───────────────────────────────────────────────────────────────

export const ABILITIES: { key: AbilityName; label: string; short: string }[] = [
  { key: "strength", label: "Força", short: "FOR" },
  { key: "dexterity", label: "Destreza", short: "DES" },
  { key: "constitution", label: "Constituição", short: "CON" },
  { key: "intelligence", label: "Inteligência", short: "INT" },
  { key: "wisdom", label: "Sabedoria", short: "SAB" },
  { key: "charisma", label: "Carisma", short: "CAR" },
];

export const ABILITY_SHORT: Record<AbilityName, string> = {
  strength: "FOR",
  dexterity: "DES",
  constitution: "CON",
  intelligence: "INT",
  wisdom: "SAB",
  charisma: "CAR",
};

// ── Skills ──────────────────────────────────────────────────────────────────

export const SKILL_ABILITY_MAP: Record<SkillName, AbilityName> = {
  acrobatics: "dexterity",
  animalHandling: "wisdom",
  arcana: "intelligence",
  athletics: "strength",
  deception: "charisma",
  history: "intelligence",
  insight: "wisdom",
  intimidation: "charisma",
  investigation: "intelligence",
  medicine: "wisdom",
  nature: "intelligence",
  perception: "wisdom",
  performance: "charisma",
  persuasion: "charisma",
  religion: "intelligence",
  sleightOfHand: "dexterity",
  stealth: "dexterity",
  survival: "wisdom",
};

export const SKILL_LABELS: Record<SkillName, string> = {
  acrobatics: "Acrobacia",
  animalHandling: "Adestramento",
  arcana: "Arcanismo",
  athletics: "Atletismo",
  deception: "Enganação",
  history: "História",
  insight: "Intuição",
  intimidation: "Intimidação",
  investigation: "Investigação",
  medicine: "Medicina",
  nature: "Natureza",
  perception: "Percepção",
  performance: "Atuação",
  persuasion: "Persuasão",
  religion: "Religião",
  sleightOfHand: "Prestidigitação",
  stealth: "Furtividade",
  survival: "Sobrevivência",
};

export const SKILL_NAMES = Object.keys(SKILL_ABILITY_MAP) as SkillName[];

// ── Proficiency Labels ──────────────────────────────────────────────────────

export const PROFICIENCY_LABELS: Record<number, string> = {
  0: "—",
  0.5: "Half",
  1: "Prof",
  2: "Expert",
};

// ── Conditions ──────────────────────────────────────────────────────────────

export const CONDITION_NAMES: ConditionName[] = [
  "blinded", "charmed", "deafened", "frightened", "grappled",
  "incapacitated", "invisible", "paralyzed", "petrified",
  "poisoned", "prone", "restrained", "stunned", "unconscious",
];

export const CONDITION_LABELS: Record<ConditionName, string> = {
  blinded: "Cegado",
  charmed: "Encantado",
  deafened: "Ensurdecido",
  frightened: "Amedrontado",
  grappled: "Agarrado",
  incapacitated: "Incapacitado",
  invisible: "Invisível",
  paralyzed: "Paralisado",
  petrified: "Petrificado",
  poisoned: "Envenenado",
  prone: "Caído",
  restrained: "Contido",
  stunned: "Atordoado",
  unconscious: "Inconsciente",
};

// ── Preset Armors ───────────────────────────────────────────────────────────

export const ARMOR_PRESETS: Armor[] = [
  { name: "None", baseAC: 0, dexCap: null, armorType: "none" },
  { name: "Padded", baseAC: 11, dexCap: null, armorType: "light" },
  { name: "Leather", baseAC: 11, dexCap: null, armorType: "light" },
  { name: "Studded Leather", baseAC: 12, dexCap: null, armorType: "light" },
  { name: "Hide", baseAC: 12, dexCap: 2, armorType: "medium" },
  { name: "Chain Shirt", baseAC: 13, dexCap: 2, armorType: "medium" },
  { name: "Scale Mail", baseAC: 14, dexCap: 2, armorType: "medium" },
  { name: "Breastplate", baseAC: 14, dexCap: 2, armorType: "medium" },
  { name: "Half Plate", baseAC: 15, dexCap: 2, armorType: "medium" },
  { name: "Ring Mail", baseAC: 14, dexCap: 0, armorType: "heavy" },
  { name: "Chain Mail", baseAC: 16, dexCap: 0, armorType: "heavy" },
  { name: "Splint", baseAC: 17, dexCap: 0, armorType: "heavy" },
  { name: "Plate", baseAC: 18, dexCap: 0, armorType: "heavy" },
];

// ── Spell Schools ───────────────────────────────────────────────────────────

export const SPELL_SCHOOLS = [
  "Abjuração", "Conjuração", "Adivinhação", "Encantamento",
  "Evocação", "Ilusão", "Necromancia", "Transmutação",
] as const;

// ── Damage Types ────────────────────────────────────────────────────────────

export const DAMAGE_TYPES = [
  "cortante", "perfurante", "contundente", "fogo", "frio", "elétrico",
  "trovão", "ácido", "veneno", "necrótico", "radiante", "força", "psíquico",
] as const;
