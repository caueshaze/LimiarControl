// ── Ability & Skill Types ───────────────────────────────────────────────────

export type AbilityName =
  | "strength"
  | "dexterity"
  | "constitution"
  | "intelligence"
  | "wisdom"
  | "charisma";

export type SkillName =
  | "acrobatics"
  | "animalHandling"
  | "arcana"
  | "athletics"
  | "deception"
  | "history"
  | "insight"
  | "intimidation"
  | "investigation"
  | "medicine"
  | "nature"
  | "perception"
  | "performance"
  | "persuasion"
  | "religion"
  | "sleightOfHand"
  | "stealth"
  | "survival";

export type ProficiencyLevel = 0 | 0.5 | 1 | 2;

// ── Armor & Shield ──────────────────────────────────────────────────────────

export type ArmorType = "none" | "light" | "medium" | "heavy";

export type Armor = {
  name: string;
  baseAC: number;
  dexCap: number | null; // null = unlimited
  armorType: ArmorType;
};

export type Shield = {
  name: string;
  bonus: number;
};

// ── Weapon ──────────────────────────────────────────────────────────────────

export type Weapon = {
  id: string;
  name: string;
  ability: AbilityName;
  damageDice: string;
  damageType: string;
  proficient: boolean;
  magicBonus: number;
  properties: string;
  range: string;
};

// ── Inventory ───────────────────────────────────────────────────────────────

export type InventoryItem = {
  id: string;
  name: string;
  quantity: number;
  weight: number;
  notes: string;
};

export type Currency = {
  cp: number;
  sp: number;
  ep: number;
  gp: number;
  pp: number;
};

// ── Spellcasting ────────────────────────────────────────────────────────────

export type Spell = {
  id: string;
  name: string;
  level: number; // 0 = cantrip
  school: string;
  prepared: boolean;
  notes: string;
};

export type SpellSlots = {
  max: number;
  used: number;
};

export type SpellcastingData = {
  ability: AbilityName;
  slots: Record<number, SpellSlots>; // keys 1-9
  spells: Spell[];
};

// ── Conditions ──────────────────────────────────────────────────────────────

export type ConditionName =
  | "blinded"
  | "charmed"
  | "deafened"
  | "frightened"
  | "grappled"
  | "incapacitated"
  | "invisible"
  | "paralyzed"
  | "petrified"
  | "poisoned"
  | "prone"
  | "restrained"
  | "stunned"
  | "unconscious";

// ── Death Saves ─────────────────────────────────────────────────────────────

export type DeathSaves = {
  successes: number; // 0-3
  failures: number; // 0-3
};

export type CharacterSheetMode = "creation" | "play";

// ── Character Sheet ─────────────────────────────────────────────────────────

export type CharacterSheet = {
  schemaVersion: number; // incrementar em migrações futuras

  // Basic info
  name: string;
  class: string;
  level: number;
  background: string;
  playerName: string;
  race: string;
  alignment: string;
  experiencePoints: number;
  inspiration: boolean;

  // Abilities
  abilities: Record<AbilityName, number>;
  savingThrowProficiencies: Record<AbilityName, boolean>;
  skillProficiencies: Record<SkillName, ProficiencyLevel>;

  // Combat
  equippedArmor: Armor;
  equippedShield: Shield | null;
  miscACBonus: number;
  speed: number;

  // HP
  maxHP: number;
  currentHP: number;
  tempHP: number;

  // Hit Dice
  hitDiceType: string;
  hitDiceTotal: number;
  hitDiceRemaining: number;

  // Death Saves
  deathSaves: DeathSaves;

  // Weapons
  weapons: Weapon[];

  // Inventory
  inventory: InventoryItem[];
  currency: Currency;

  // Spellcasting
  spellcasting: SpellcastingData | null;

  // Proficiencies & Languages
  languages: string[];
  toolProficiencies: string[];
  weaponProficiencies: string[];
  armorProficiencies: string[];

  // Conditions
  conditions: Record<ConditionName, boolean>;

  // Skill choices tracking
  classSkillChoices: SkillName[];
  classEquipmentSelections: Record<string, string>;

  // Text fields
  featuresAndTraits: string;
  notes: string;
};
